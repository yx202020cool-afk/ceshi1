from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from ashare_replay.config import PROJECT_ROOT, Settings, stable_hash
from ashare_replay.services.report import ReportGenerator


def build_demo_historical_fixture(settings: Settings, start: date, end: date) -> dict[str, Any]:
    generator = ReportGenerator(settings)
    rows: list[dict[str, Any]] = []
    lifecycle_distribution: dict[str, int] = {}
    lookahead_violations: list[dict[str, str]] = []
    previous_watchlist_codes: set[str] | None = None
    watchlist_overlaps: list[float] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            report = generator.generate(cursor, "POST_CLOSE_FINAL")["report"]
            as_of = datetime.fromisoformat(report["metadata"]["as_of"])
            all_key_sectors = [
                *report["industry"]["gainers_top3"],
                *report["industry"]["losers_top3"],
                *report["concept"]["gainers_top3"],
                *report["concept"]["losers_top3"],
            ]
            for sector in all_key_sectors:
                stage = sector["lifecycle"]["stage"]
                lifecycle_distribution[stage] = lifecycle_distribution.get(stage, 0) + 1
                for evidence in sector["attribution"]["evidence"]:
                    published_at = datetime.fromisoformat(evidence["published_at"])
                    if published_at > as_of:
                        lookahead_violations.append(
                            {
                                "trade_date": report["metadata"]["trade_date"],
                                "sector_name": sector["sector_name"],
                                "evidence_title": evidence["title"],
                            }
                        )
            current_codes = {item["stock_code"] for item in report["watchlist"]}
            if previous_watchlist_codes is not None:
                union = current_codes | previous_watchlist_codes
                overlap = len(current_codes & previous_watchlist_codes) / max(len(union), 1)
                watchlist_overlaps.append(round(overlap, 4))
            previous_watchlist_codes = current_codes
            top = report["industry"]["gainers_top3"][0]
            rows.append(
                {
                    "trade_date": cursor.isoformat(),
                    "report_id": report["generation"]["report_id"],
                    "as_of": report["metadata"]["as_of"],
                    "market_state": report["market_overview"]["state"],
                    "top_industry": top["sector_name"],
                    "top_industry_lifecycle": top["lifecycle"]["stage"],
                    "top_industry_change_pct": top["change_pct"],
                    "top_industry_flow_ratio": top["net_inflow_ratio"],
                    "watchlist_count": len(report["watchlist"]),
                    "quality_warning_count": len(report["metadata"]["quality_warnings"]),
                    "data_status": report["metadata"]["data_status"],
                    "proxy_next_return": round(
                        top["change_pct"] * 0.32 + top["net_inflow_ratio"] * 18,
                        2,
                    ),
                }
            )
        cursor += timedelta(days=1)

    trading_days = len(rows)
    missing_rate = 0.0 if trading_days else 1.0
    delayed_rate = (
        sum(1 for row in rows if row["data_status"] in {"delayed", "expired"}) / trading_days
        if trading_days
        else 0.0
    )
    avg_watchlist_overlap = (
        sum(watchlist_overlaps) / len(watchlist_overlaps) if watchlist_overlaps else 0.0
    )
    return {
        "fixture_id": stable_hash({"start": start.isoformat(), "end": end.isoformat(), "mode": "demo"}),
        "source": "DemoProvider deterministic long-history fixture",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "trading_days": trading_days,
        "rows": rows,
        "quality": {
            "missing_rate": round(missing_rate, 4),
            "delayed_rate": round(delayed_rate, 4),
            "lookahead_violation_count": len(lookahead_violations),
            "lookahead_violations": lookahead_violations,
            "average_watchlist_overlap": round(avg_watchlist_overlap, 4),
        },
        "lifecycle_distribution": lifecycle_distribution,
        "summary": (
            f"演示长周期 Fixture 完成：{trading_days} 个交易日，"
            f"前视检查违规 {len(lookahead_violations)} 条。"
        ),
    }


def write_demo_historical_fixture(
    settings: Settings,
    start: date,
    end: date,
    output_path: str = "fixtures/demo/long_history_fixture.json",
) -> dict[str, Any]:
    fixture = build_demo_historical_fixture(settings, start, end)
    path = PROJECT_ROOT / output_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"fixture": fixture, "file": str(path.relative_to(PROJECT_ROOT))}


def run_demo_backtest(settings: Settings, start: date, end: date) -> dict[str, Any]:
    fixture = build_demo_historical_fixture(settings, start, end)
    rows = [
        {
            "trade_date": row["trade_date"],
            "sector_name": row["top_industry"],
            "lifecycle": row["top_industry_lifecycle"],
            "score_proxy": row["top_industry_change_pct"] + row["top_industry_flow_ratio"] * 100,
            "next_day_proxy_return": row["proxy_next_return"],
        }
        for row in fixture["rows"]
    ]
    if not rows:
        return {"rows": [], "quality": fixture["quality"], "summary": "区间内无交易日"}
    avg = sum(row["next_day_proxy_return"] for row in rows) / len(rows)
    high_stage = [row for row in rows if row["lifecycle"] in {"高潮", "加速"}]
    startup_stage = [row for row in rows if row["lifecycle"] in {"启动", "发酵"}]
    high_avg = (
        sum(row["next_day_proxy_return"] for row in high_stage) / len(high_stage)
        if high_stage
        else 0.0
    )
    startup_avg = (
        sum(row["next_day_proxy_return"] for row in startup_stage) / len(startup_stage)
        if startup_stage
        else 0.0
    )
    return {
        "rows": rows,
        "quality": fixture["quality"],
        "lifecycle_distribution": fixture["lifecycle_distribution"],
        "metrics": {
            "sample_days": len(rows),
            "proxy_next_return_avg": round(avg, 2),
            "high_or_accelerate_proxy_avg": round(high_avg, 2),
            "launch_or_ferment_proxy_avg": round(startup_avg, 2),
            "watchlist_average_overlap": fixture["quality"]["average_watchlist_overlap"],
        },
        "summary": (
            f"演示回测完成：样本 {len(rows)} 个交易日，"
            f"下一日代理表现均值 {avg:.2f}%。该结果仅验证流程，不代表投资收益。"
        ),
    }
