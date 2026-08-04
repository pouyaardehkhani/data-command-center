"""Shared, app-wide singletons handed to every page: detected GPU/encoder
capabilities and the one sequential job queue everything submits work to."""
from dataclasses import dataclass

from dcc.core.gpu import Capabilities, detect_capabilities
from dcc.core.job_queue import JobQueue


@dataclass
class AppContext:
    capabilities: Capabilities
    job_queue: JobQueue


def build_context() -> AppContext:
    return AppContext(
        capabilities=detect_capabilities(),
        job_queue=JobQueue(),
    )
