from __future__ import annotations

from typing import Any


def weekly_flow_analysis(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sector in sectors:
        flow_3d = sector.get("flow_3d", 0)
        flow_5d = sector.get("flow_5d", 0)
        flow_10d = sector.get("flow_10d", 0)
        flow_20d = sector.get("flow_20d", 0)
        acceleration = sector.get("flow_acceleration", 0)
        decay = sector.get("flow_decay", 0)
        if flow_5d > 0 and flow_10d > 0:
            label = "中周期持续流入"
        elif flow_3d > 0:
            label = "短周期持续流入"
        elif acceleration > 0.25:
            label = "资金加速"
        elif decay > 0.45:
            label = "资金衰减"
        else:
            label = "观察"
        score = (
            min(max(flow_3d, -30), 80) * 0.18
            + min(max(flow_5d, -50), 120) * 0.24
            + min(max(flow_10d, -80), 180) * 0.22
            + min(max(flow_20d, -120), 260) * 0.16
            + sector.get("flow_continuity", 0) * 50
            + acceleration * 18
            - decay * 16
        )
        rows.append(
            {
                "sector_code": sector["sector_code"],
                "sector_name": sector["sector_name"],
                "taxonomy": sector["taxonomy"],
                "category": label,
                "flow_3d": flow_3d,
                "flow_5d": flow_5d,
                "flow_10d": flow_10d,
                "flow_20d": flow_20d,
                "flow_acceleration": acceleration,
                "flow_decay": decay,
                "weekly_trend": "上行" if flow_5d > 0 and sector.get("change_pct", 0) > 0 else "震荡或下行",
                "score": round(score, 2),
            }
        )
    return sorted(rows, key=lambda row: row["score"], reverse=True)
