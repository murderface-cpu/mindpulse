"""
scheduler.py – Periodic AI data population using APScheduler
"""
import os
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as db
import ai_engine as ai

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def populate_database():
    """
    Main job: ask Groq to generate insights and persist them to PostgreSQL.
    Called on every scheduled tick.
    """
    start = time.time()
    n = int(os.getenv("ENTRIES_PER_RUN", "3"))
    logger.info(f"Scheduler tick – generating {n} insight(s)…")
    db.log_event("INFO", "scheduler_tick", f"Starting population run – {n} entries requested")

    created = 0
    try:
        insights = ai.generate_batch(n)
        for ins in insights:
            db.insert_insight(
                topic=ins["topic"],
                category=ins["category"],
                summary=ins["summary"],
                full_content=ins["full_content"],
                model=ins["model"],
                tokens_used=ins["tokens_used"],
            )
            created += 1

        status = "success" if created == n else "partial"
        db.log_event("INFO", "scheduler_done",
                     f"Population run complete – {created}/{n} entries saved")

    except Exception as e:
        status = "failed"
        logger.error(f"Population run failed: {e}")
        db.log_event("ERROR", "scheduler_error", str(e))

    duration_ms = int((time.time() - start) * 1000)
    db.record_run(entries_created=created, status=status, duration_ms=duration_ms)
    logger.info(f"Run finished – status={status}, created={created}, duration={duration_ms}ms")


def start_scheduler():
    global _scheduler

    interval = int(os.getenv("POPULATE_INTERVAL_SECONDS", "300"))
    logger.info(f"Starting scheduler – interval={interval}s")

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=populate_database,
        trigger=IntervalTrigger(seconds=interval),
        id="populate_db",
        name="AI Database Population",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()

    # Run once immediately on startup so the DB isn't empty
    try:
        populate_database()
    except Exception as e:
        logger.error(f"Initial population failed: {e}")

    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def get_next_run() -> str:
    """Return ISO string of the next scheduled run, or 'N/A'."""
    global _scheduler
    if _scheduler:
        job = _scheduler.get_job("populate_db")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
    return "N/A"


def update_interval(seconds: int):
    """Dynamically change the population interval without restarting."""
    global _scheduler
    if _scheduler:
        _scheduler.reschedule_job(
            job_id="populate_db",
            trigger=IntervalTrigger(seconds=seconds),
        )
        os.environ["POPULATE_INTERVAL_SECONDS"] = str(seconds)
        logger.info(f"Scheduler interval updated to {seconds}s")
