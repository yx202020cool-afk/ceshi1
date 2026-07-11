from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ashare_replay.db import Database
from ashare_replay.schema_validation import validate_required_object
from ashare_replay.services.report import ReportGenerator


def test_report_outputs_and_schema_are_consistent(isolated_env):
    result = ReportGenerator(isolated_env).generate(date(2026, 7, 10), "POST_CLOSE_FINAL")
    report = result["report"]
    validate_required_object(report)
    files = result["files"]
    for key in ["json", "markdown", "html", "pdf", "sector_csv", "leaders_csv", "watchlist_csv"]:
        path = Path(files[key])
        if not path.is_absolute():
            path = Path.cwd() / path
        assert path.exists(), key
        assert path.stat().st_size > 0, key
    from_json = json.loads((isolated_env.report_output_dir / "2026-07-10" / "POST_CLOSE_FINAL" / "report.json").read_text(encoding="utf-8"))
    assert from_json["metadata"]["as_of"] == report["metadata"]["as_of"]
    assert from_json["industry"]["gainers_top3"][0]["sector_code"] == report["industry"]["gainers_top3"][0]["sector_code"]
    assert any("演示数据" in warning for warning in from_json["metadata"]["quality_warnings"])


def test_report_database_idempotency(isolated_env):
    generator = ReportGenerator(isolated_env)
    generator.generate(date(2026, 7, 10), "PRE_CLOSE_PREVIEW")
    generator.generate(date(2026, 7, 10), "PRE_CLOSE_PREVIEW")
    db = Database(isolated_env.database_url, isolated_env.timezone)
    rows = db.query("SELECT COUNT(*) AS count FROM reports")
    assert rows[0]["count"] == 1
