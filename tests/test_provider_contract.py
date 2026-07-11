from __future__ import annotations

from datetime import date

from ashare_replay.constants import REPORT_TYPES
from ashare_replay.providers.demo import DemoProvider
from ashare_replay.time_utils import as_of_datetime


def test_demo_provider_contract(isolated_env):
    provider = DemoProvider(isolated_env)
    as_of = as_of_datetime(date(2026, 7, 10), "17:30", isolated_env.timezone)
    snapshot = provider.get_snapshot(date(2026, 7, 10), as_of, "POST_CLOSE_FINAL")
    assert provider.health_check()["status"] == "ok"
    assert snapshot["meta"]["provider"] == "demo"
    assert snapshot["meta"]["data_status"] == "demo"
    assert len(snapshot["sectors"]) >= 16
    assert len(snapshot["stocks"]) >= 60
    assert {row["taxonomy"] for row in snapshot["sectors"]} == {"industry", "concept"}
    assert all(key in snapshot["meta"] for key in ["source", "provider", "trade_date", "as_of", "fetched_at"])
    assert set(REPORT_TYPES) == {"PRE_CLOSE_PREVIEW", "CLOSE_CONFIRMATION", "POST_CLOSE_FINAL"}
