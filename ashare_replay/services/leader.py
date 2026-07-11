from __future__ import annotations

from typing import Any

from ashare_replay.services.utils import clamp, score_range


def score_leaders_for_sector(
    sector: dict[str, Any],
    snapshot: dict[str, Any],
    config: dict[str, Any],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    weights = config.get("leader_score_weights", {})
    stock_flows = {row["stock_code"]: row for row in snapshot.get("stock_money_flow", [])}
    candidates = []
    for quote in snapshot.get("stock_quotes", []):
        if not any(
            m["sector_code"] == sector["sector_code"] and m["taxonomy"] == sector["taxonomy"]
            for m in quote.get("memberships", [])
        ):
            continue
        flow = stock_flows.get(quote["stock_code"], {})
        risk_penalty = _risk_penalty(quote)
        sub = {
            "relative_return": score_range(quote["change_pct"] - sector["change_pct"], -4, 6),
            "money_flow": score_range(float(flow.get("net_inflow_ratio") or 0), -0.2, 0.3),
            "amount_liquidity": score_range(float(quote.get("amount") or 0), 0.5, 24),
            "sector_contribution": score_range(float(quote.get("amount") or 0) * quote["change_pct"], -20, 70),
            "limit_trend": clamp((20 if quote.get("limit_up") else 0) + quote.get("streak_limit_up", 0) * 18 + 35),
            "recent_activity": score_range(float(quote.get("turnover_rate") or 0), 0, 18),
            "market_relative": score_range(float(quote.get("change_pct") or 0), -5, 10),
            "sector_purity": clamp(110 - len(quote.get("memberships", [])) * 12),
            "close_strength": score_range(float(quote.get("tail_change_pct") or 0), -3, 3),
            "risk_penalty": risk_penalty,
        }
        positive = sum(sub[key] * float(weights.get(key, 0)) for key in sub if key != "risk_penalty")
        total = clamp(positive - sub["risk_penalty"] * float(weights.get("risk_penalty", 0.12)))
        candidates.append(
            {
                "stock_code": quote["stock_code"],
                "stock_name": quote["stock_name"],
                "sector_code": sector["sector_code"],
                "sector_name": sector["sector_name"],
                "taxonomy": sector["taxonomy"],
                "change_pct": quote["change_pct"],
                "amount": quote["amount"],
                "turnover_rate": quote["turnover_rate"],
                "money_flow": flow.get("main_net_inflow"),
                "rank_in_sector": 0,
                "sub_scores": {key: round(value, 2) for key, value in sub.items()},
                "total_score": round(total, 2),
                "reason": _leader_reason(quote, flow, sector),
                "leader_type": _leader_type(quote, flow, total),
                "risk_tips": _risk_tips(quote),
                "invalidation": "若个股资金连续转负、相对板块强度跌至后 50% 或所属板块退潮，则观察失效。",
            }
        )
    ranked = sorted(candidates, key=lambda row: row["total_score"], reverse=True)[:top_n]
    for idx, item in enumerate(ranked, start=1):
        item["rank_in_sector"] = idx
    return ranked


def _risk_penalty(quote: dict[str, Any]) -> float:
    penalty = 0.0
    if quote.get("is_st"):
        penalty += 45
    if quote.get("is_delisting"):
        penalty += 80
    if quote.get("is_suspended"):
        penalty += 70
    if quote.get("is_new_stock"):
        penalty += 12
    if quote.get("turnover_rate", 0) > 16:
        penalty += 10
    return clamp(penalty)


def _risk_tips(quote: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if quote.get("is_st"):
        risks.append("ST 或风险警示股票")
    if quote.get("is_delisting"):
        risks.append("退市整理风险")
    if quote.get("is_suspended"):
        risks.append("停牌或零成交")
    if quote.get("is_new_stock"):
        risks.append("上市初期，涨跌幅规则和流动性特征特殊")
    if quote.get("turnover_rate", 0) > 16:
        risks.append("换手率较高，短线波动可能放大")
    return risks or ["未发现演示规则内的特殊风险"]


def _leader_reason(quote: dict[str, Any], flow: dict[str, Any], sector: dict[str, Any]) -> str:
    parts = [
        f"相对所属板块涨跌幅差值 {quote['change_pct'] - sector['change_pct']:.2f} 个百分点",
        f"按当前数据供应商口径计算的主力资金流指标为 {flow.get('main_net_inflow', '不支持')}",
        f"成交额 {quote.get('amount')} 亿元，换手率 {quote.get('turnover_rate')}%",
    ]
    if quote.get("limit_up"):
        parts.append("触发涨停强度加分，但未仅因涨停直接认定为龙头")
    return "；".join(parts)


def _leader_type(quote: dict[str, Any], flow: dict[str, Any], total: float) -> str:
    if total < 45:
        return "无法确认"
    if quote.get("streak_limit_up", 0) >= 2:
        return "高度龙头"
    if flow.get("main_net_inflow", 0) and flow.get("main_net_inflow", 0) > 1.5:
        return "容量龙头"
    if quote.get("change_pct", 0) > 4:
        return "趋势龙头"
    if quote.get("change_pct", 0) > 1.2:
        return "板块中军"
    if quote.get("change_pct", 0) < 0:
        return "跟风股"
    return "补涨龙头"
