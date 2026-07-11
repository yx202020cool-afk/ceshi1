from __future__ import annotations

from datetime import date

from ashare_replay.providers.demo import DemoProvider
from ashare_replay.services.leader import score_leaders_for_sector
from ashare_replay.services.lifecycle import evaluate_lifecycle
from ashare_replay.services.ranking import enrich_sector_rows, rank_by_taxonomy
from ashare_replay.time_utils import as_of_datetime


def _snapshot(settings):
    provider = DemoProvider(settings)
    as_of = as_of_datetime(date(2026, 7, 10), "17:30", settings.timezone)
    return provider.get_snapshot(date(2026, 7, 10), as_of, "POST_CLOSE_FINAL")


def test_industry_and_concept_are_ranked_separately(isolated_env):
    snapshot = _snapshot(isolated_env)
    sectors = enrich_sector_rows(snapshot, isolated_env.config)
    industry = rank_by_taxonomy(sectors, "industry")
    concept = rank_by_taxonomy(sectors, "concept")
    assert len(industry["gainers_top3"]) == 3
    assert len(industry["losers_top3"]) == 3
    assert len(concept["gainers_top3"]) == 3
    assert len(concept["losers_top3"]) == 3
    assert all(row["taxonomy"] == "industry" for row in industry["gainers_top3"])
    assert all(row["taxonomy"] == "concept" for row in concept["gainers_top3"])


def test_lifecycle_and_leader_scores_are_traceable(isolated_env):
    snapshot = _snapshot(isolated_env)
    sector = enrich_sector_rows(snapshot, isolated_env.config)[0]
    lifecycle = evaluate_lifecycle(sector, isolated_env.config)
    leaders = score_leaders_for_sector(sector, snapshot, isolated_env.config)
    assert lifecycle["stage"] in {"启动", "发酵", "加速", "高潮", "分歧", "退潮", "修复", "震荡", "无法判断"}
    assert lifecycle["triggered_rules"]
    assert len(leaders) == 5
    assert leaders[0]["sub_scores"]
    assert "risk_penalty" in leaders[0]["sub_scores"]
    assert leaders[0]["reason"]
