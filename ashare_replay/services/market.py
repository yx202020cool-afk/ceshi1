from __future__ import annotations

from typing import Any


def evaluate_market_state(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    sentiment = snapshot["market_sentiment"]
    thresholds = config.get("market_thresholds", {})
    up = sentiment["up_count"]
    down = sentiment["down_count"]
    total = max(up + down + sentiment["flat_count"], 1)
    up_ratio = up / total
    down_ratio = down / total
    limit_up = sentiment["limit_up_count"]
    limit_down = sentiment["limit_down_count"]
    break_rate = sentiment["break_limit_rate"]
    index_quotes = snapshot.get("index_quotes", [])
    index_is_proxy = any(row.get("index_code") == "AK-A-SAMPLE" for row in index_quotes)
    index_label = "样本平均涨跌幅" if index_is_proxy else "主要指数平均涨跌幅"
    avg_index = sum(row["change_pct"] for row in index_quotes) / max(len(index_quotes), 1)

    triggers: list[str] = []
    if up_ratio >= thresholds.get("strong_up_ratio", 0.62) and avg_index > 0:
        state = "强势普涨"
        triggers.append(f"上涨家数占比 {up_ratio:.1%} 高于阈值")
        triggers.append(f"{index_label} {avg_index:.2f}% 为正")
    elif avg_index > 0 and up_ratio < 0.5:
        state = "指数强但个股弱"
        triggers.append(f"{index_label}为正但上涨家数不足半数")
    elif limit_up >= thresholds.get("emotion_high_limit_up", 60):
        state = "情绪高潮"
        triggers.append(f"涨停数量 {limit_up} 高于情绪高潮阈值")
    elif break_rate >= thresholds.get("high_break_rate", 0.35):
        state = "高位分歧"
        triggers.append(f"炸板率 {break_rate:.1%} 高于阈值")
    elif down_ratio >= thresholds.get("weak_down_ratio", 0.58) and limit_down >= thresholds.get("emotion_low_limit_down", 30):
        state = "情绪退潮"
        triggers.append(f"下跌家数占比 {down_ratio:.1%} 高于阈值")
        triggers.append(f"跌停数量 {limit_down} 高于阈值")
    elif sentiment["market_amount"] < 800:
        state = "缩量震荡"
        triggers.append("成交额低于演示阈值")
    else:
        state = "结构性行情"
        triggers.append("涨跌家数和指数表现未形成单边信号")

    return {
        "state": state,
        "triggered_conditions": triggers,
        "index_average_change_pct": round(avg_index, 2),
        "index_average_label": index_label,
        "up_ratio": round(up_ratio, 4),
        "down_ratio": round(down_ratio, 4),
        "market_amount": sentiment["market_amount"],
        "amount_change_pct": sentiment["amount_change_pct"],
        "up_count": up,
        "down_count": down,
        "flat_count": sentiment["flat_count"],
        "limit_up_count": limit_up,
        "limit_down_count": limit_down,
        "break_limit_count": sentiment["break_limit_count"],
        "break_limit_rate": break_rate,
        "consecutive_limit_up_count": sentiment["consecutive_limit_up_count"],
        "highest_limit_height": sentiment["highest_limit_height"],
        "up_median_pct": sentiment["up_median_pct"],
        "down_median_pct": sentiment["down_median_pct"],
        "breadth": sentiment["breadth"],
        "profit_effect": sentiment["profit_effect"],
        "loss_effect": sentiment["loss_effect"],
        "large_vs_small": sentiment["large_vs_small"],
        "style_preference": sentiment["style_preference"],
        "data_complete": sentiment["data_complete"],
    }
