"""Single background worker thread for LLM analysis.

- Activity ingestion never waits for inference.
- Manual "Analyze Now" requests are queued and handled by the same thread, so
  only one inference runs at a time (CPU-only laptop).
- Automatic analysis runs when an employee has >= ANALYSIS_BATCH_SIZE new live
  events, or new events that have been idle for ANALYSIS_IDLE_SECONDS.
- Failures are recorded and retried later; the cursor is never advanced on failure."""
from __future__ import annotations

import logging
import queue
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..database import SessionLocal
from . import analyzer, ollama_client

log = logging.getLogger("hackviz.worker")


@dataclass
class Job:
    employee_id: str
    mode: str  # manual | auto
    force: bool = False
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    state: str = "queued"  # queued | running | done | failed
    result: dict | None = None
    error: str | None = None
    error_code: str | None = None
    done: threading.Event = field(default_factory=threading.Event)

    def public(self) -> dict:
        return {"employee_id": self.employee_id, "mode": self.mode, "state": self.state,
                "queued_at": self.queued_at, "started_at": self.started_at, "finished_at": self.finished_at,
                "result": self.result, "error": self.error, "error_code": self.error_code}


class AnalysisWorker:
    def __init__(self) -> None:
        self._q: "queue.Queue[Job]" = queue.Queue()
        self._lock = threading.Lock()
        self._active: dict[str, Job] = {}     # employee_id -> queued/running job
        self._last: dict[str, Job] = {}       # employee_id -> last finished job
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.current: Job | None = None
        self.last_scan_at: datetime | None = None
        self.started_at: datetime | None = None

    # ------------------------------------------------------------ control
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.started_at = datetime.now(timezone.utc)
        self._thread = threading.Thread(target=self._loop, name="hackviz-analysis", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def request(self, employee_id: str, mode: str = "manual", force: bool = False) -> tuple[Job, bool]:
        """Queue a job. Returns (job, created). If one is already queued/running for the employee,
        that job is returned instead (duplicate-analysis prevention)."""
        with self._lock:
            existing = self._active.get(employee_id)
            if existing is not None:
                return existing, False
            job = Job(employee_id, mode, force)
            self._active[employee_id] = job
        self._q.put(job)
        return job, True

    def status(self) -> dict:
        with self._lock:
            active = [j.public() for j in self._active.values()]
            last = {k: v.public() for k, v in self._last.items()}
        return {"worker_alive": self.alive, "auto_enabled": settings.auto_analysis,
                "batch_size": settings.batch_size, "idle_seconds": settings.idle_seconds,
                "retry_seconds": settings.retry_seconds, "model": settings.ollama_model,
                "current": self.current.public() if self.current else None, "active": active,
                "last_finished": last, "last_scan_at": self.last_scan_at}

    def job_for(self, employee_id: str) -> dict | None:
        with self._lock:
            j = self._active.get(employee_id) or self._last.get(employee_id)
            return j.public() if j else None

    # ------------------------------------------------------------ loop
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._q.get(timeout=3)
            except queue.Empty:
                job = None
            try:
                if job is not None:
                    self._run(job)
                elif settings.auto_analysis:
                    self._scan()
            except Exception:  # noqa: BLE001 - keep worker alive
                log.error("worker loop error:\n%s", traceback.format_exc())

    def _scan(self) -> None:
        self.last_scan_at = datetime.now(timezone.utc)
        now = self.last_scan_at
        with SessionLocal() as db:
            pending = analyzer.pending_live_counts(db)
        for p in pending:
            if p["next_retry_at"] and p["next_retry_at"] > now:
                continue
            idle = (now - p["last_received_at"]).total_seconds() if p["last_received_at"] else 0
            if p["unanalyzed_live_events"] >= settings.batch_size or idle >= settings.idle_seconds:
                job, created = self.request(p["employee_id"], "auto")
                if created:
                    log.info("auto analysis queued for %s (%s new live events, idle %.0fs)",
                             p["employee_id"], p["unanalyzed_live_events"], idle)

    def _run(self, job: Job) -> None:
        job.state, job.started_at = "running", datetime.now(timezone.utc)
        self.current = job
        try:
            with SessionLocal() as db:
                try:
                    job.result = analyzer.analyze_employee(db, job.employee_id, job.mode, job.force)
                    job.state = "done"
                except (analyzer.AnalysisError, ollama_client.OllamaError) as exc:
                    db.rollback()
                    job.state, job.error = "failed", str(exc)
                    job.error_code = getattr(exc, "code", "error")
                    if not isinstance(exc, analyzer.NothingToAnalyze):
                        self._record_failure(db, job)
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    job.state, job.error, job.error_code = "failed", f"{type(exc).__name__}: {exc}", "internal_error"
                    log.error("analysis crashed:\n%s", traceback.format_exc())
                    self._record_failure(db, job)
        finally:
            job.finished_at = datetime.now(timezone.utc)
            self.current = None
            with self._lock:
                self._active.pop(job.employee_id, None)
                self._last[job.employee_id] = job
            job.done.set()
            log.info("analysis %s for %s -> %s %s", job.mode, job.employee_id, job.state, job.error or job.result)

    def _record_failure(self, db, job: Job) -> None:
        try:
            st = analyzer.get_state(db, job.employee_id)
            st.last_attempt_at = job.started_at
            st.last_error = (job.error or "")[:1000]
            st.consecutive_failures = (st.consecutive_failures or 0) + 1
            backoff = min(600, settings.retry_seconds * st.consecutive_failures)
            st.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            log.error("could not record failure:\n%s", traceback.format_exc())


worker = AnalysisWorker()
