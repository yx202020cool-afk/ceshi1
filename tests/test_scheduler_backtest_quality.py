from __future__ import annotations

from datetime import date

from ashare_replay.db import Database
from ashare_replay.services.backtest import build_demo_historical_fixture, run_demo_backtest
from ashare_replay.services.scheduler import run_manual_backfill


def test_manual_backfill_records_job(isolated_env):
    run_manual_backfill(isolated_env, date(2026, 7, 10), "CLOSE_CONFIRMATION")
    db = Database(isolated_env.database_url, isolated_env.timezone)
    jobs = db.query("SELECT status FROM job_runs")
    assert jobs
    assert jobs[-1]["status"] == "success"


def test_demo_backtest_runs_without_future_data(isolated_env):
    result = run_demo_backtest(isolated_env, date(2026, 7, 6), date(2026, 7, 10))
    assert result["rows"]
    assert "演示回测完成" in result["summary"]
    assert result["metrics"]["sample_days"] == 5
    assert result["quality"]["lookahead_violation_count"] == 0
    assert all(row["trade_date"] <= "2026-07-10" for row in result["rows"])


def test_long_history_fixture_has_quality_metrics(isolated_env):
    fixture = build_demo_historical_fixture(isolated_env, date(2026, 6, 29), date(2026, 7, 10))
    assert fixture["trading_days"] >= 10
    assert fixture["quality"]["missing_rate"] == 0.0
    assert fixture["quality"]["lookahead_violation_count"] == 0
    assert fixture["lifecycle_distribution"]
    assert fixture["fixture_id"]
