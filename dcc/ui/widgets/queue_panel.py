"""Bottom dock: shows every queued/running/finished job with a progress bar
and a cancel/remove button, plus a way to clear finished jobs in bulk. Jobs
run strictly one-at-a-time (see core/job_queue.py)."""
import qtawesome as qta
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from dcc.core.job_queue import JobQueue, JobStatus

_FINISHED_STATUSES = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELED)


class _JobRow(QWidget):
    def __init__(self, job_id: str, label: str, queue: JobQueue, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self._queue = queue
        self.name_label = QLabel(label)
        self.name_label.setMinimumWidth(220)
        self.status_label = QLabel("Queued")
        self.status_label.setFixedWidth(90)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.action_btn = QPushButton(qta.icon("fa5s.times"), "")
        self.action_btn.setFixedWidth(30)
        self.action_btn.setToolTip("Cancel")
        self.action_btn.clicked.connect(lambda: self._queue.cancel(self.job_id))

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        row.addWidget(self.name_label)
        row.addWidget(self.bar, 1)
        row.addWidget(self.status_label)
        row.addWidget(self.action_btn)

    def set_status(self, status: JobStatus):
        self.status_label.setText(status.value)
        colors = {
            JobStatus.DONE: "#3fc57c", JobStatus.FAILED: "#e5555f",
            JobStatus.CANCELED: "#9aa1ae", JobStatus.RUNNING: "#4f8cff",
        }
        color = colors.get(status, "#9aa1ae")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

        if status in _FINISHED_STATUSES:
            # Once a job is finished there's nothing left to cancel - repurpose
            # the same button to remove it from the list instead of disabling it.
            self.action_btn.setIcon(qta.icon("fa5s.trash"))
            self.action_btn.setToolTip("Remove from list")
            self.action_btn.clicked.disconnect()
            self.action_btn.clicked.connect(lambda: self._queue.remove(self.job_id))


class QueuePanel(QWidget):
    def __init__(self, queue: JobQueue, parent=None):
        super().__init__(parent)
        self.setObjectName("Dock")
        self._queue = queue
        self._rows: dict = {}

        title = QLabel("Job Queue (sequential)")
        title.setStyleSheet("font-weight: 700; padding: 4px 8px;")

        clear_btn = QPushButton(qta.icon("fa5s.broom"), " Clear Completed")
        clear_btn.clicked.connect(queue.clear_finished)

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(clear_btn)

        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch(1)

        container = QWidget()
        container.setLayout(self._list_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setMaximumHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(header_row)
        layout.addWidget(scroll)

        queue.job_added.connect(self._on_added)
        queue.job_started.connect(self._on_started)
        queue.job_progress.connect(self._on_progress)
        queue.job_finished.connect(self._on_finished)
        queue.job_removed.connect(self._on_removed)

    def _on_added(self, job_id: str):
        job = next(j for j in self._queue.jobs() if j.id == job_id)
        row = _JobRow(job_id, job.label, self._queue)
        self._rows[job_id] = row
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _on_started(self, job_id: str):
        if job_id in self._rows:
            self._rows[job_id].set_status(JobStatus.RUNNING)

    def _on_progress(self, job_id: str, pct: int):
        if job_id in self._rows:
            self._rows[job_id].bar.setValue(pct)

    def _on_finished(self, job_id: str, success: bool, message: str):
        row = self._rows.get(job_id)
        if not row:
            return
        job = next((j for j in self._queue.jobs() if j.id == job_id), None)
        if job:
            row.set_status(job.status)
        if success:
            row.bar.setValue(100)

    def _on_removed(self, job_id: str):
        row = self._rows.pop(job_id, None)
        if row:
            self._list_layout.removeWidget(row)
            row.deleteLater()
