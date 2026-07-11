from __future__ import annotations

from typing import Any


def build_watchlist(
    leaders_by_sector: dict[tuple[str, str], list[dict[str, Any]]],
    lifecycle_by_sector: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    options = config.get("watchlist", {})
    min_score = float(options.get("min_score", 68))
    max_items = int(options.get("max_items", 30))
    allowed = set(options.get("allowed_lifecycle", ["启动", "发酵", "加速", "修复"]))
    best_by_stock: dict[str, dict[str, Any]] = {}
    for key, leaders in leaders_by_sector.items():
        lifecycle = lifecycle_by_sector.get(key, {})
        if lifecycle.get("stage") not in allowed:
            continue
        for leader in leaders:
            if leader["total_score"] < min_score:
                continue
            item = {
                "stock_code": leader["stock_code"],
                "stock_name": leader["stock_name"],
                "main_sector_code": leader["sector_code"],
                "main_sector": leader["sector_name"],
                "taxonomy": leader["taxonomy"],
                "candidate_type": f"{lifecycle.get('stage', '观察')}板块候选",
                "reason": f"{leader['reason']}；所属板块生命周期为{lifecycle.get('stage')}",
                "total_score": leader["total_score"],
                "money_flow_status": "净流入" if leader.get("money_flow", 0) and leader["money_flow"] > 0 else "净流出或不支持",
                "daily_trend": "强于板块" if leader["sub_scores"]["relative_return"] >= 50 else "弱于板块",
                "weekly_trend": "跟随重点板块观察",
                "liquidity": f"成交额 {leader['amount']} 亿元，换手率 {leader['turnover_rate']}%",
                "main_risks": leader["risk_tips"],
                "invalidation": leader["invalidation"],
                "data_as_of": "",
            }
            current = best_by_stock.get(leader["stock_code"])
            if current is None or item["total_score"] > current["total_score"]:
                best_by_stock[leader["stock_code"]] = item
    return sorted(best_by_stock.values(), key=lambda row: row["total_score"], reverse=True)[:max_items]
