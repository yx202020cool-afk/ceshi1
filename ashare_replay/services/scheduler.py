from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any

from ashare_replay.config import Settings
from ashare_replay.constants import REPORT_TYPES
from ashare_replay.db import Database
from ashare_replay.services.report import ReportGenerator
from ashare_replay.services.utils import stable_id
from ashare_replay.time_utils import as_of_datetime, iso_now, now_tz


def is_trading_day(value: date) -> bool:
    return value.weekday() < 5


def run_manual_backfill(settings: Settings, trade_date: date, report_type: str) -> dict[str, Any]:
    db = Database(settings.database_url, settings.timezone)
    db.init_db()
    run_id = stable_id("job", "manual_backfill", trade_date, report_type, iso_now(settings.timezone))
    db.record_job(run_id, "manual_backfill", trade_date.isoformat(), report_type, "running")
    try:
        result = ReportGenerator(settings, db).generate(trade_date, report_type)
        db.record_job(run_id, "manual_backfill", trade_date.isoformat(), report_type, "success", "完成", iso_now(settings.timezone))
        return result
    except Exception as exc:
        db.record_job(
            run_id,
            "manual_backfill",
            trade_date.isoformat(),
            report_type,
            "failed",
            f"{type(exc).__name__}: {exc}",
            iso_now(settings.timezone),
        )
        raise


def due_report_types(settings: Settings, current: datetime | None = None) -> list[str]:
    now = now_tz(settings.timezone) if current is None else current
    due = []
    for report_type, meta in REPORT_TYPES.items():
        configured_time = settings.config["report_times"].get(report_type, meta["time"])
        if now >= as_of_datetime(now.date(), configured_time, settings.timezone):
            due.append(report_type)
    return due


def run_scheduler_forever(settings: Settings, poll_seconds: int = 60) -> None:
    db = Database(settings.database_url, settings.timezone)
    db.init_db()
    while True:
        today = now_tz(settings.timezone).date()
        if is_trading_day(today):
            for report_type in due_report_types(settings):
                run_id = stable_id("job", "scheduled", today, report_type)
                existing = db.query("SELECT status FROM job_runs WHERE run_id=:run_id", {"run_id": run_id})
                if existing and existing[0]["status"] == "success":
                    continue
                try:
                    db.record_job(run_id, "scheduled_report", today.isoformat(), report_type, "running")
                    ReportGenerator(settings, db).generate(today, report_type)
                    db.record_job(run_id, "scheduled_report", today.isoformat(), report_type, "success", "完成", iso_now(settings.timezone))
                except Exception as exc:
                    db.record_job(
                        run_id,
                        "scheduled_report",
                        today.isoformat(),
                        report_type,
                        "failed",
                        f"{type(exc).__name__}: {exc}",
                        iso_now(settings.timezone),
                    )
        time.sleep(poll_seconds)
