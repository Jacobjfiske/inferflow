from threading import Lock


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.jobs_submitted = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0

    def inc_submitted(self) -> None:
        with self._lock:
            self.jobs_submitted += 1

    def inc_succeeded(self) -> None:
        with self._lock:
            self.jobs_succeeded += 1

    def inc_failed(self) -> None:
        with self._lock:
            self.jobs_failed += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "jobs_submitted": self.jobs_submitted,
                "jobs_succeeded": self.jobs_succeeded,
                "jobs_failed": self.jobs_failed,
            }


metrics = Metrics()
