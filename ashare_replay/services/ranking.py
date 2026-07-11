from __future__ import annotations

from typing import Any

from ashare_replay.services.utils import top_n


def enrich_sector_rows(snapshot: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    filters = config.get("sector_filters", {})
    min_constituents = int(filters.get("min_constituents", 5))
    min_coverage = float(filters.get("min_coverage_ratio", 0.75))
    flows = {
        (row["sector_code"], row["taxonomy"]): row for row in snapshot.get("sector_money_flow", [])
    }
    rows: list[dict[str, Any]] = []
    for quote in snapshot.get("sector_quotes", []):
        flow = flows.get((quote["sector_code"], quote["taxonomy"]), {})
        eligible = (
            quote.get("constituent_count", 0) >= min_constituents
            and quote.get("coverage_ratio", 0) >= min_coverage
        )
        amount = float(quote.get("amount") or 0)
        net = float(flow.get("main_net_inflow") or 0)
        rows.append(
            {
                **quote,
                "main_net_inflow": net,
                "main_net_outflow": min(0.0, net),
                "net_inflow_ratio": float(flow.get("net_inflow_ratio") or 0),
                "flow_3d": float(flow.get("flow_3d") or 0),
                "flow_5d": float(flow.get("flow_5d") or 0),
                "flow_10d": float(flow.get("flow_10d") or 0),
                "flow_20d": float(flow.get("flow_20d") or 0),
                "flow_continuity": float(flow.get("flow_continuity") or 0),
                "flow_acceleration": float(flow.get("flow_acceleration") or 0),
                "flow_decay": float(flow.get("flow_decay") or 0),
                "flow_concentration": float(flow.get("flow_concentration") or 0),
                "relative_strength": float(quote.get("relative_strength") or 0),
                "eligible_for_main_rank": eligible,
                "data_complete": eligible and amount > 0,
            }
        )
    return rows


def rank_by_taxonomy(rows: list[dict[str, Any]], taxonomy: str) -> dict[str, Any]:
    scoped = [row for row in rows if row["taxonomy"] == taxonomy and row["eligible_for_main_rank"]]
    all_scoped = [row for row in rows if row["taxonomy"] == taxonomy]
    return {
        "all": sorted(all_scoped, key=lambda row: row["change_pct"], reverse=True),
        "gainers_top3": top_n(scoped, "change_pct", 3, True),
        "losers_top3": top_n(scoped, "change_pct", 3, False),
        "fund_flow_top": top_n(scoped, "main_net_inflow", 10, True),
        "fund_flow_bottom": top_n(scoped, "main_net_inflow", 10, False),
    }
