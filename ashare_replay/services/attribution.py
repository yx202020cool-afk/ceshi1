from __future__ import annotations

from datetime import datetime
from typing import Any


def explain_sector(sector: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    as_of = datetime.fromisoformat(snapshot["meta"]["as_of"])
    evidence: list[dict[str, Any]] = []
    for item in [*snapshot.get("news", []), *snapshot.get("policy_events", [])]:
        published_at = datetime.fromisoformat(item["published_at"])
        if published_at <= as_of and sector["sector_code"] in item.get("related_sector_codes", []):
            evidence.append(
                {
                    "type": "新闻/政策",
                    "title": item["title"],
                    "published_at": item["published_at"],
                    "url": item.get("url"),
                    "summary": item.get("content") or item.get("evidence", ""),
                }
            )
    if not evidence:
        return {
            "summary": "证据不足：当前数据源没有在报告截止时间前提供可引用新闻、公告或政策证据。",
            "evidence": [],
            "confidence": 0.2,
        }
    direction = "上涨" if sector.get("change_pct", 0) >= 0 else "下跌"
    return {
        "summary": f"{sector['sector_name']}今日{direction}可能与已收录证据有关，但仍以结构化指标为准，不作确定性因果判断。",
        "evidence": evidence,
        "confidence": min(0.85, 0.35 + 0.15 * len(evidence)),
    }
