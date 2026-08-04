"""Sequential job queue: one ffmpeg/yt-dlp process at a time (batches are
processed one after another, never in parallel, per the product spec).

Built on QProcess so everything stays on the Qt event loop - no extra
threads needed to keep the UI responsive while a job runs.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QObject, QProcess, Signal

from dcc.paths import NO_WINDOW_FLAGS


class JobStatus(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    DONE = "Done"
    FAILED = "Failed"
    CANCELED = "Canceled"


@dataclass
class Job:
    label: str
    args: list
    duration_sec: float = 0.0     # for ffmpeg progress %; 0 = indeterminate
    kind: str = "ffmpeg"          # "ffmpeg" | "ytdlp"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: str = ""


_TIME_RE = re.compile(r"out_time_ms=(\d+)")
_PCT_RE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")


_FINISHED_STATUSES = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELED)


class JobQueue(QObject):
    job_added = Signal(str)
    job_started = Signal(str)
    job_progress = Signal(str, int)
    job_finished = Signal(str, bool, str)
    job_removed = Signal(str)
    queue_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: dict = {}
        self._order: list = []
        self._process: QProcess | None = None
        self._current_id: str | None = None
        self._buffer = ""

    def add(self, job: Job) -> str:
        self._jobs[job.id] = job
        self._order.append(job.id)
        self.job_added.emit(job.id)
        self.queue_changed.emit()
        self._maybe_start_next()
        return job.id

    def jobs(self) -> list:
        return [self._jobs[i] for i in self._order]

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        if job.status == JobStatus.RUNNING and self._process:
            self._process.kill()
        elif job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELED
            self.queue_changed.emit()

    def remove(self, job_id: str) -> None:
        """Removes a finished/failed/canceled job from the list. Running or
        still-queued jobs must be canceled first - this never kills a process."""
        job = self._jobs.get(job_id)
        if not job or job.status not in _FINISHED_STATUSES:
            return
        del self._jobs[job_id]
        self._order.remove(job_id)
        self.job_removed.emit(job_id)
        self.queue_changed.emit()

    def clear_finished(self) -> None:
        for job_id in [i for i in self._order if self._jobs[i].status in _FINISHED_STATUSES]:
            del self._jobs[job_id]
            self._order.remove(job_id)
            self.job_removed.emit(job_id)
        self.queue_changed.emit()

    def _maybe_start_next(self) -> None:
        if self._process is not None:
            return
        next_id = next((i for i in self._order if self._jobs[i].status == JobStatus.QUEUED), None)
        if not next_id:
            return
        self._start(next_id)

    def _start(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        self._current_id = job_id
        self._buffer = ""
        self.job_started.emit(job_id)
        self.queue_changed.emit()

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.finished.connect(self._on_finished)
        proc.setProgram(job.args[0])
        proc.setArguments(job.args[1:])
        proc.start()
        self._process = proc

    def _on_output(self) -> None:
        if not self._process or not self._current_id:
            return
        job = self._jobs[self._current_id]
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        self._buffer += chunk

        if job.kind == "ffmpeg" and job.duration_sec > 0:
            for m in _TIME_RE.finditer(chunk):
                out_ms = int(m.group(1))
                pct = min(100, int(out_ms / 1000 / job.duration_sec * 100))
                job.progress = pct
                self.job_progress.emit(job.id, pct)
        elif job.kind == "ytdlp":
            for m in _PCT_RE.finditer(chunk):
                pct = min(100, int(float(m.group(1))))
                job.progress = pct
                self.job_progress.emit(job.id, pct)

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        job_id = self._current_id
        job = self._jobs[job_id]
        self._process = None
        self._current_id = None

        if job.status == JobStatus.RUNNING:
            if exit_code == 0:
                job.status = JobStatus.DONE
                job.progress = 100
                self.job_finished.emit(job_id, True, "")
            else:
                job.status = JobStatus.FAILED
                tail = "\n".join(self._buffer.splitlines()[-15:])
                job.message = tail
                self.job_finished.emit(job_id, False, tail)
        else:
            job.status = JobStatus.CANCELED
            self.job_finished.emit(job_id, False, "Canceled")

        self.queue_changed.emit()
        self._maybe_start_next()


_process_creation_flags = NO_WINDOW_FLAGS  # kept for reference / future use
