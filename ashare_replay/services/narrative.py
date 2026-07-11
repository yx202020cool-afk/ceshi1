from __future__ import annotations

from typing import Any

from ashare_replay.constants import DISCLAIMER


def deterministic_summary(report: dict[str, Any]) -> str:
    meta = report["metadata"]
    market = report["market_overview"]
    industry = report["industry"]
    concept = report["concept"]
    top_industry = industry["gainers_top3"][0]["sector_name"] if industry["gainers_top3"] else "无"
    top_concept = concept["gainers_top3"][0]["sector_name"] if concept["gainers_top3"] else "无"
    return (
        f"{meta['trade_date']} {meta['report_version']}：市场状态为{market['state']}。"
        f"行业强势方向以{top_industry}为代表，概念强势方向以{top_concept}为代表。"
        f"当前资金流均为“按当前数据供应商口径计算的主力资金流指标”，"
        f"不代表全部真实资金。{DISCLAIMER}"
    )
