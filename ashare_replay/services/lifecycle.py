from __future__ import annotations

from typing import Any

NEXT_STAGE = {
    "启动": "发酵",
    "发酵": "加速",
    "加速": "高潮",
    "高潮": "分歧",
    "分歧": "退潮或修复",
    "退潮": "修复",
    "修复": "启动或震荡",
    "震荡": "启动或退潮",
    "无法判断": "等待更多数据",
}


def evaluate_lifecycle(sector: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    t = config.get("lifecycle_thresholds", {})
    change = float(sector.get("change_pct") or 0)
    amount_change = float(sector.get("amount_change_pct") or 0)
    net_ratio = float(sector.get("net_inflow_ratio") or 0)
    flow_5d = float(sector.get("flow_5d") or 0)
    up_ratio = sector.get("up_count", 0) / max(sector.get("constituent_count", 1), 1)
    limit_up = int(sector.get("limit_up_count") or 0)
    limit_down = int(sector.get("limit_down_count") or 0)
    tail = float(sector.get("tail_change_pct") or 0)
    triggers: list[str] = []
    missing: list[str] = []

    if change >= t.get("accelerate_return_pct", 3.0) and amount_change >= t.get("accelerate_amount_change_pct", 25):
        stage = "加速"
        triggers.append("当日涨幅和成交额放大同时超过加速阈值")
    elif up_ratio >= t.get("climax_up_ratio", 0.72) and limit_up >= t.get("climax_limit_up_count", 3):
        stage = "高潮"
        triggers.append("板块上涨覆盖率和涨停数量同时达到高潮阈值")
    elif tail <= t.get("divergence_tail_pullback_pct", -1.2) and change > 0:
        stage = "分歧"
        triggers.append("板块收盘仍上涨但尾盘回落达到分歧阈值")
    elif change <= t.get("ebb_return_pct", -2.0) or limit_down >= 2:
        stage = "退潮"
        triggers.append("板块跌幅或跌停数量触发退潮规则")
    elif change >= t.get("repair_return_pct", 1.0) and net_ratio > 0:
        stage = "修复"
        triggers.append("板块反弹且主力资金口径为净流入")
    elif flow_5d > 0 and change >= t.get("launch_return_pct", 1.2) and net_ratio >= t.get("launch_net_ratio", 0.02):
        stage = "启动"
        triggers.append("当日涨幅、5日资金和净流入占比同时触发启动规则")
    elif flow_5d > 0:
        stage = "发酵"
        triggers.append("多日资金保持净流入但当日强度尚未达到加速")
    elif abs(change) <= t.get("shock_abs_return_pct", 0.8):
        stage = "震荡"
        triggers.append("板块涨跌幅处于震荡阈值内")
    else:
        stage = "无法判断"
        missing.append("缺少足够强的价格、资金或情绪条件")

    if not triggers:
        triggers.append("未触发明确规则")
    confidence = min(0.95, 0.45 + 0.1 * len(triggers) + min(abs(change) / 12, 0.2) + min(abs(net_ratio) * 2, 0.2))
    return {
        "sector_code": sector["sector_code"],
        "sector_name": sector["sector_name"],
        "taxonomy": sector["taxonomy"],
        "stage": stage,
        "confidence": round(confidence, 2),
        "triggered_rules": triggers,
        "missing_conditions": missing,
        "previous_stage": "演示回放推算，真实模式需读取上一交易日报告",
        "next_stage": NEXT_STAGE[stage],
        "invalidation": "若板块成交额快速萎缩、资金连续转负或龙头跌破关键强度，则本阶段判断失效。",
    }
