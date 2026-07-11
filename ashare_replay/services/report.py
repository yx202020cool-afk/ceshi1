from __future__ import annotations

import csv
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ashare_replay.config import PROJECT_ROOT, Settings, stable_hash
from ashare_replay.constants import DISCLAIMER, REPORT_TYPES, TAXONOMY_LABELS
from ashare_replay.db import Database
from ashare_replay.providers import build_provider
from ashare_replay.schema_validation import validate_required_object
from ashare_replay.services.attribution import explain_sector
from ashare_replay.services.leader import score_leaders_for_sector
from ashare_replay.services.lifecycle import evaluate_lifecycle
from ashare_replay.services.market import evaluate_market_state
from ashare_replay.services.narrative import deterministic_summary
from ashare_replay.services.ranking import enrich_sector_rows, rank_by_taxonomy
from ashare_replay.services.utils import payload_hash, stable_id
from ashare_replay.services.watchlist import build_watchlist
from ashare_replay.services.weekly import weekly_flow_analysis
from ashare_replay.time_utils import as_of_datetime, ensure_not_future, iso_dt, iso_now


class ReportGenerator:
    def __init__(self, settings: Settings, db: Database | None = None) -> None:
        self.settings = settings
        self.db = db or Database(settings.database_url, settings.timezone)
        self.provider = build_provider(settings)

    def generate(self, trade_date: date, report_type: str) -> dict[str, Any]:
        if report_type not in REPORT_TYPES:
            raise ValueError(f"未知报告类型: {report_type}")
        report_time = self.settings.config["report_times"].get(report_type, REPORT_TYPES[report_type]["time"])
        as_of = as_of_datetime(trade_date, report_time, self.settings.timezone)
        if self.settings.app_mode != "demo":
            ensure_not_future(as_of, self.settings.timezone)

        self.db.init_db()
        self.db.upsert_config(self.settings.config_hash, self.settings.config)
        health = self.provider.health_check()
        self.db.upsert_provider_health(health)

        snapshot = self.provider.get_snapshot(trade_date, as_of, report_type)
        snap_hash = payload_hash(self._stable_snapshot_payload(snapshot))
        snapshot_id = stable_id("snap", snapshot["meta"]["provider"], trade_date, report_type, snap_hash)
        self._persist_snapshot(snapshot, snapshot_id, snap_hash, report_type)

        sectors = enrich_sector_rows(snapshot, self.settings.config)
        market = evaluate_market_state(snapshot, self.settings.config)
        lifecycle_by_sector = {
            (row["sector_code"], row["taxonomy"]): evaluate_lifecycle(row, self.settings.config)
            for row in sectors
        }
        leaders_by_sector = {
            (row["sector_code"], row["taxonomy"]): score_leaders_for_sector(
                row, snapshot, self.settings.config, top_n=5
            )
            for row in sectors
        }
        weekly_rows = weekly_flow_analysis(sectors)
        watchlist = build_watchlist(leaders_by_sector, lifecycle_by_sector, self.settings.config)
        for item in watchlist:
            item["data_as_of"] = iso_dt(as_of)

        industry = self._taxonomy_section(
            "industry", sectors, snapshot, lifecycle_by_sector, leaders_by_sector
        )
        concept = self._taxonomy_section(
            "concept", sectors, snapshot, lifecycle_by_sector, leaders_by_sector
        )
        warnings = list(dict.fromkeys(snapshot["meta"].get("quality_warnings", [])))
        report_id = stable_id(
            "report",
            trade_date.isoformat(),
            report_type,
            self.settings.config_hash,
            snap_hash,
            self._code_version(),
        )
        generation = {
            "report_id": report_id,
            "snapshot_id": snapshot_id,
            "config_version": self.settings.config_hash,
            "weights_version": stable_hash(self.settings.config.get("leader_score_weights", {})),
            "code_version": self._code_version(),
            "generated_at": iso_now(self.settings.timezone),
            "data_cutoff": iso_dt(as_of),
            "providers": [snapshot["meta"]["provider"]],
            "reproducible_key": stable_hash(
                {
                    "snapshot": snap_hash,
                    "config": self.settings.config_hash,
                    "code": self._code_version(),
                    "report_type": report_type,
                }
            ),
        }
        report: dict[str, Any] = {
            "metadata": {
                "trade_date": trade_date.isoformat(),
                "report_type": report_type,
                "report_version": REPORT_TYPES[report_type]["label"],
                "report_note": REPORT_TYPES[report_type]["note"],
                "as_of": iso_dt(as_of),
                "is_final": bool(REPORT_TYPES[report_type]["is_final"]),
                "source": snapshot["meta"]["source"],
                "provider": snapshot["meta"]["provider"],
                "data_status": snapshot["meta"]["data_status"],
                "quality_warnings": warnings,
                "timezone": self.settings.timezone,
                "disclaimer": DISCLAIMER,
            },
            "summary": "",
            "market_overview": market,
            "industry": industry,
            "concept": concept,
            "weekly_flow": weekly_rows[:20],
            "watchlist": watchlist,
            "risks": self._risk_summary(snapshot, market, warnings),
            "generation": generation,
            "settings_view": {
                "report_times": self.settings.config["report_times"],
                "sector_filters": self.settings.config["sector_filters"],
                "leader_score_weights": self.settings.config["leader_score_weights"],
                "lifecycle_thresholds": self.settings.config["lifecycle_thresholds"],
                "llm_enabled": self.settings.llm_enabled,
            },
        }
        report["summary"] = deterministic_summary(report)
        validate_required_object(report)
        file_map = self.write_outputs(report)
        self.db.save_report(report, file_map)
        self._persist_analysis(snapshot_id, report, lifecycle_by_sector, leaders_by_sector)
        return {"report": report, "files": file_map}

    def _taxonomy_section(
        self,
        taxonomy: str,
        sectors: list[dict[str, Any]],
        snapshot: dict[str, Any],
        lifecycle_by_sector: dict[tuple[str, str], dict[str, Any]],
        leaders_by_sector: dict[tuple[str, str], list[dict[str, Any]]],
    ) -> dict[str, Any]:
        ranked = rank_by_taxonomy(sectors, taxonomy)

        def decorate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            output = []
            for row in rows:
                key = (row["sector_code"], row["taxonomy"])
                output.append(
                    {
                        **row,
                        "lifecycle": lifecycle_by_sector[key],
                        "leaders_top5": leaders_by_sector[key],
                        "attribution": explain_sector(row, snapshot),
                        "money_flow_label": "按当前数据供应商口径计算的主力资金流指标",
                    }
                )
            return output

        return {
            "taxonomy": taxonomy,
            "taxonomy_label": TAXONOMY_LABELS[taxonomy],
            "gainers_top3": decorate(ranked["gainers_top3"]),
            "losers_top3": decorate(ranked["losers_top3"]),
            "fund_flow_top": decorate(ranked["fund_flow_top"][:5]),
            "fund_flow_bottom": decorate(ranked["fund_flow_bottom"][:5]),
            "all_ranked": decorate(ranked["all"]),
        }

    def _stable_snapshot_payload(self, payload: Any) -> Any:
        volatile = {"fetched_at", "created_at", "updated_at"}
        if isinstance(payload, dict):
            return {
                key: self._stable_snapshot_payload(value)
                for key, value in payload.items()
                if key not in volatile
            }
        if isinstance(payload, list):
            return [self._stable_snapshot_payload(item) for item in payload]
        return payload

    def _persist_snapshot(
        self,
        snapshot: dict[str, Any],
        snapshot_id: str,
        snap_hash: str,
        report_type: str,
    ) -> None:
        self.db.save_snapshot(
            {
                "snapshot_id": snapshot_id,
                "provider": snapshot["meta"]["provider"],
                "trade_date": snapshot["meta"]["trade_date"],
                "as_of": snapshot["meta"]["as_of"],
                "report_type": report_type,
                "payload_json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                "payload_hash": snap_hash,
                "created_at": iso_now(self.settings.timezone),
            }
        )
        self._persist_reference_data(snapshot)

    def _persist_reference_data(self, snapshot: dict[str, Any]) -> None:
        now = iso_now(self.settings.timezone)
        for row in snapshot.get("stocks", []):
            payload = {**row, "created_at": now, "updated_at": now}
            self.db.execute(
                """
                INSERT INTO stocks(stock_code, stock_name, exchange, board, listed_date,
                                   is_st, is_delisting, created_at, updated_at)
                VALUES(:stock_code, :stock_name, :exchange, :board, :listed_date,
                       :is_st, :is_delisting, :created_at, :updated_at)
                ON CONFLICT(stock_code) DO UPDATE SET
                    stock_name=excluded.stock_name,
                    board=excluded.board,
                    is_st=excluded.is_st,
                    is_delisting=excluded.is_delisting,
                    updated_at=excluded.updated_at
                """,
                payload,
            )
        for row in snapshot.get("calendar", []):
            self.db.execute(
                """
                INSERT INTO trading_calendar(trade_date, is_trading_day, reason, created_at)
                VALUES(:trade_date, :is_trading_day, :reason, :created_at)
                ON CONFLICT(trade_date) DO UPDATE SET
                    is_trading_day=excluded.is_trading_day,
                    reason=excluded.reason
                """,
                {**row, "is_trading_day": int(bool(row["is_trading_day"]))},
            )
        for row in snapshot.get("sectors", []):
            self.db.execute(
                """
                INSERT INTO sectors(sector_code, sector_name, taxonomy, provider,
                                    classification_system, created_at, updated_at)
                VALUES(:sector_code, :sector_name, :taxonomy, :provider,
                       :classification_system, :created_at, :updated_at)
                ON CONFLICT(sector_code, taxonomy, provider) DO UPDATE SET
                    sector_name=excluded.sector_name,
                    updated_at=excluded.updated_at
                """,
                row,
            )
        for row in snapshot.get("constituents", []):
            self.db.execute(
                """
                INSERT INTO sector_constituents(sector_code, taxonomy, provider, stock_code,
                                                valid_from, valid_to, created_at)
                VALUES(:sector_code, :taxonomy, :provider, :stock_code,
                       :valid_from, :valid_to, :created_at)
                ON CONFLICT(sector_code, taxonomy, provider, stock_code, valid_from)
                DO UPDATE SET valid_to=excluded.valid_to
                """,
                row,
            )
        for row in snapshot.get("sector_quotes", []):
            self.db.execute(
                """
                INSERT INTO sector_quotes(sector_code, taxonomy, trade_date, as_of, provider,
                    change_pct, amount, amount_change_pct, up_count, down_count, flat_count,
                    limit_up_count, limit_down_count, break_limit_count, median_change_pct,
                    data_status, quality_warnings, created_at)
                VALUES(:sector_code, :taxonomy, :trade_date, :as_of, :provider,
                    :change_pct, :amount, :amount_change_pct, :up_count, :down_count, :flat_count,
                    :limit_up_count, :limit_down_count, :break_limit_count, :median_change_pct,
                    :data_status, :quality_warnings_json, :created_at)
                ON CONFLICT(sector_code, taxonomy, trade_date, as_of, provider)
                DO UPDATE SET change_pct=excluded.change_pct, amount=excluded.amount
                """,
                {**row, "quality_warnings_json": json.dumps(row["quality_warnings"], ensure_ascii=False)},
            )
        for row in snapshot.get("stock_quotes", []):
            self.db.execute(
                """
                INSERT INTO raw_quotes(stock_code, trade_date, as_of, provider, close_price,
                    change_pct, amount, turnover_rate, is_suspended, data_status,
                    quality_warnings, created_at)
                VALUES(:stock_code, :trade_date, :as_of, :provider, :close_price,
                    :change_pct, :amount, :turnover_rate, :is_suspended, :data_status,
                    :quality_warnings_json, :created_at)
                ON CONFLICT(stock_code, trade_date, as_of, provider)
                DO UPDATE SET close_price=excluded.close_price, change_pct=excluded.change_pct
                """,
                {
                    **row,
                    "is_suspended": int(bool(row.get("is_suspended"))),
                    "quality_warnings_json": json.dumps(row["quality_warnings"], ensure_ascii=False),
                },
            )
        for row in snapshot.get("sector_money_flow", []):
            self.db.execute(
                """
                INSERT INTO sector_money_flow(sector_code, taxonomy, trade_date, as_of, provider,
                    main_net_inflow, super_large_net_inflow, large_net_inflow, medium_net_inflow,
                    small_net_inflow, net_inflow_ratio, flow_3d, flow_5d, flow_10d, flow_20d,
                    is_final, comparable_across_dates, comparable_across_sectors,
                    data_status, quality_warnings, created_at)
                VALUES(:sector_code, :taxonomy, :trade_date, :as_of, :provider,
                    :main_net_inflow, :super_large_net_inflow, :large_net_inflow, :medium_net_inflow,
                    :small_net_inflow, :net_inflow_ratio, :flow_3d, :flow_5d, :flow_10d, :flow_20d,
                    :is_final_int, :comparable_across_dates_int, :comparable_across_sectors_int,
                    :data_status, :quality_warnings_json, :created_at)
                ON CONFLICT(sector_code, taxonomy, trade_date, as_of, provider)
                DO UPDATE SET main_net_inflow=excluded.main_net_inflow
                """,
                {
                    **row,
                    "is_final_int": int(bool(row.get("is_final"))),
                    "comparable_across_dates_int": int(bool(row.get("comparable_across_dates"))),
                    "comparable_across_sectors_int": int(bool(row.get("comparable_across_sectors"))),
                    "quality_warnings_json": json.dumps(row["quality_warnings"], ensure_ascii=False),
                },
            )
        for row in snapshot.get("stock_money_flow", []):
            self.db.execute(
                """
                INSERT INTO stock_money_flow(stock_code, trade_date, as_of, provider,
                    main_net_inflow, super_large_net_inflow, large_net_inflow, medium_net_inflow,
                    small_net_inflow, net_inflow_ratio, data_status, quality_warnings, created_at)
                VALUES(:stock_code, :trade_date, :as_of, :provider,
                    :main_net_inflow, :super_large_net_inflow, :large_net_inflow, :medium_net_inflow,
                    :small_net_inflow, :net_inflow_ratio, :data_status, :quality_warnings_json, :created_at)
                ON CONFLICT(stock_code, trade_date, as_of, provider)
                DO UPDATE SET main_net_inflow=excluded.main_net_inflow
                """,
                {**row, "quality_warnings_json": json.dumps(row["quality_warnings"], ensure_ascii=False)},
            )
        for row in snapshot.get("news", []):
            self.db.execute(
                """
                INSERT INTO news(id, provider, title, content, url, published_at,
                                 related_sector_codes, related_stock_codes, created_at)
                VALUES(:id, :provider, :title, :content, :url, :published_at,
                       :related_sector_codes_json, :related_stock_codes_json, :created_at)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title
                """,
                {
                    **row,
                    "related_sector_codes_json": json.dumps(row["related_sector_codes"], ensure_ascii=False),
                    "related_stock_codes_json": json.dumps(row["related_stock_codes"], ensure_ascii=False),
                    "created_at": now,
                },
            )
        for row in snapshot.get("announcements", []):
            self.db.execute(
                """
                INSERT INTO announcements(id, provider, title, url, published_at,
                                          related_stock_codes, created_at)
                VALUES(:id, :provider, :title, :url, :published_at,
                       :related_stock_codes_json, :created_at)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title
                """,
                {
                    **row,
                    "related_stock_codes_json": json.dumps(row["related_stock_codes"], ensure_ascii=False),
                    "created_at": now,
                },
            )

    def _persist_analysis(
        self,
        snapshot_id: str,
        report: dict[str, Any],
        lifecycle_by_sector: dict[tuple[str, str], dict[str, Any]],
        leaders_by_sector: dict[tuple[str, str], list[dict[str, Any]]],
    ) -> None:
        now = iso_now(self.settings.timezone)
        self.db.execute(
            """
            INSERT INTO features(feature_id, snapshot_id, feature_json, created_at)
            VALUES(:feature_id, :snapshot_id, :feature_json, :created_at)
            ON CONFLICT(feature_id) DO UPDATE SET feature_json=excluded.feature_json
            """,
            {
                "feature_id": stable_id("feature", snapshot_id),
                "snapshot_id": snapshot_id,
                "feature_json": json.dumps(
                    {
                        "market_overview": report["market_overview"],
                        "weekly_flow": report["weekly_flow"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "created_at": now,
            },
        )
        for lifecycle in lifecycle_by_sector.values():
            self.db.execute(
                """
                INSERT INTO lifecycle_results(result_id, snapshot_id, sector_code, taxonomy,
                    stage, confidence, triggered_rules, missing_conditions,
                    next_stage, invalidation, created_at)
                VALUES(:result_id, :snapshot_id, :sector_code, :taxonomy,
                    :stage, :confidence, :triggered_rules, :missing_conditions,
                    :next_stage, :invalidation, :created_at)
                ON CONFLICT(result_id) DO UPDATE SET stage=excluded.stage, confidence=excluded.confidence
                """,
                {
                    "result_id": stable_id(
                        "life", snapshot_id, lifecycle["sector_code"], lifecycle["taxonomy"]
                    ),
                    "snapshot_id": snapshot_id,
                    "sector_code": lifecycle["sector_code"],
                    "taxonomy": lifecycle["taxonomy"],
                    "stage": lifecycle["stage"],
                    "confidence": lifecycle["confidence"],
                    "triggered_rules": json.dumps(lifecycle["triggered_rules"], ensure_ascii=False),
                    "missing_conditions": json.dumps(lifecycle["missing_conditions"], ensure_ascii=False),
                    "next_stage": lifecycle["next_stage"],
                    "invalidation": lifecycle["invalidation"],
                    "created_at": now,
                },
            )
        for leaders in leaders_by_sector.values():
            for leader in leaders:
                self.db.execute(
                    """
                    INSERT INTO leader_scores(score_id, snapshot_id, sector_code, taxonomy,
                        stock_code, total_score, sub_scores_json, reason, risk_tips,
                        invalidation, created_at)
                    VALUES(:score_id, :snapshot_id, :sector_code, :taxonomy,
                        :stock_code, :total_score, :sub_scores_json, :reason, :risk_tips,
                        :invalidation, :created_at)
                    ON CONFLICT(score_id) DO UPDATE SET total_score=excluded.total_score
                    """,
                    {
                        "score_id": stable_id(
                            "leader",
                            snapshot_id,
                            leader["sector_code"],
                            leader["taxonomy"],
                            leader["stock_code"],
                        ),
                        "snapshot_id": snapshot_id,
                        "sector_code": leader["sector_code"],
                        "taxonomy": leader["taxonomy"],
                        "stock_code": leader["stock_code"],
                        "total_score": leader["total_score"],
                        "sub_scores_json": json.dumps(leader["sub_scores"], ensure_ascii=False),
                        "reason": leader["reason"],
                        "risk_tips": json.dumps(leader["risk_tips"], ensure_ascii=False),
                        "invalidation": leader["invalidation"],
                        "created_at": now,
                    },
                )
        for item in report["watchlist"]:
            self.db.execute(
                """
                INSERT INTO watchlist(item_id, snapshot_id, stock_code, stock_name, sector_code,
                    taxonomy, candidate_type, total_score, reasons, risks, invalidation, created_at)
                VALUES(:item_id, :snapshot_id, :stock_code, :stock_name, :sector_code,
                    :taxonomy, :candidate_type, :total_score, :reasons, :risks, :invalidation, :created_at)
                ON CONFLICT(item_id) DO UPDATE SET total_score=excluded.total_score
                """,
                {
                    "item_id": stable_id("watch", snapshot_id, item["stock_code"], item["main_sector"]),
                    "snapshot_id": snapshot_id,
                    "stock_code": item["stock_code"],
                    "stock_name": item["stock_name"],
                    "sector_code": item["main_sector_code"],
                    "taxonomy": item["taxonomy"],
                    "candidate_type": item["candidate_type"],
                    "total_score": item["total_score"],
                    "reasons": item["reason"],
                    "risks": json.dumps(item["main_risks"], ensure_ascii=False),
                    "invalidation": item["invalidation"],
                    "created_at": now,
                },
            )

    def _risk_summary(
        self,
        snapshot: dict[str, Any],
        market: dict[str, Any],
        warnings: list[str],
    ) -> list[str]:
        risks = list(warnings)
        if market["break_limit_rate"] > 0.3:
            risks.append("炸板率偏高，短线分歧风险上升")
        if market["down_count"] > market["up_count"]:
            risks.append("下跌家数多于上涨家数，赚钱效应不足")
        if snapshot["meta"]["data_status"] == "demo":
            risks.append("当前为演示数据，不能作为真实交易判断依据")
        return list(dict.fromkeys(risks))

    def write_outputs(self, report: dict[str, Any]) -> dict[str, str]:
        meta = report["metadata"]
        out_dir = self.settings.report_output_dir / meta["trade_date"] / meta["report_type"]
        out_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "json": out_dir / "report.json",
            "markdown": out_dir / "report.md",
            "html": out_dir / "report.html",
            "pdf": out_dir / "report.pdf",
            "sector_csv": out_dir / "sector_rankings.csv",
            "leaders_csv": out_dir / "leaders.csv",
            "watchlist_csv": out_dir / "watchlist.csv",
        }
        files["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        files["markdown"].write_text(self._render_markdown(report), encoding="utf-8")
        files["html"].write_text(self._render_html(report), encoding="utf-8")
        self._write_sector_csv(report, files["sector_csv"])
        self._write_leaders_csv(report, files["leaders_csv"])
        self._write_watchlist_csv(report, files["watchlist_csv"])
        self._write_pdf(report, files["pdf"])
        return {key: str(path.relative_to(PROJECT_ROOT)) for key, path in files.items()}

    def _render_markdown(self, report: dict[str, Any]) -> str:
        meta = report["metadata"]
        lines = [
            f"# A 股每日全局复盘 - {meta['report_version']}",
            "",
            f"- 报告日期：{meta['trade_date']}",
            f"- 数据截止：{meta['as_of']}",
            f"- 是否最终：{'是' if meta['is_final'] else '否'}",
            f"- 数据来源：{meta['source']} / {meta['provider']}",
            f"- 数据状态：{meta['data_status']}",
            "",
            f"> {meta['disclaimer']}",
            "",
            "## 总结",
            report["summary"],
            "",
            "## 市场概况",
            f"- 市场状态：{report['market_overview']['state']}",
            f"- 触发条件：{'；'.join(report['market_overview']['triggered_conditions'])}",
            f"- 上涨/下跌/平盘：{report['market_overview']['up_count']} / {report['market_overview']['down_count']} / {report['market_overview']['flat_count']}",
            f"- 涨停/跌停/炸板：{report['market_overview']['limit_up_count']} / {report['market_overview']['limit_down_count']} / {report['market_overview']['break_limit_count']}",
            "",
        ]
        for section_key, title in [("industry", "行业板块"), ("concept", "概念板块")]:
            section = report[section_key]
            lines.extend([f"## {title}", "### 涨幅前三"])
            for row in section["gainers_top3"]:
                lines.append(
                    f"- {row['sector_name']}：{row['change_pct']}%，资金 {row['main_net_inflow']} 亿元，阶段 {row['lifecycle']['stage']}"
                )
            lines.append("### 跌幅前三")
            for row in section["losers_top3"]:
                lines.append(
                    f"- {row['sector_name']}：{row['change_pct']}%，资金 {row['main_net_inflow']} 亿元，阶段 {row['lifecycle']['stage']}"
                )
            lines.append("")
        lines.extend(["## 候选观察池"])
        for item in report["watchlist"][:10]:
            lines.append(
                f"- {item['stock_code']} {item['stock_name']}：{item['candidate_type']}，评分 {item['total_score']}，风险：{'；'.join(item['main_risks'])}"
            )
        lines.extend(["", "## 风险提示"])
        lines.extend([f"- {risk}" for risk in report["risks"]])
        return "\n".join(lines) + "\n"

    def _render_html(self, report: dict[str, Any]) -> str:
        meta = report["metadata"]

        def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
            head = "".join(f"<th>{label}</th>" for key, label in columns)
            body = ""
            for row in rows:
                body += "<tr>" + "".join(f"<td>{row.get(key, '')}</td>" for key, label in columns) + "</tr>"
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

        columns = [
            ("sector_name", "板块"),
            ("change_pct", "涨跌幅%"),
            ("amount", "成交额"),
            ("main_net_inflow", "资金流"),
            ("net_inflow_ratio", "资金/成交额"),
        ]
        html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>A 股每日全局复盘 - {meta['report_version']}</title>
<style>
:root {{
  color-scheme: light;
  --bg:#f5f5f7;
  --panel:#ffffff;
  --text:#1d1d1f;
  --muted:#6e6e73;
  --line:#d2d2d7;
  --accent:#0071e3;
  --good:#0a7f42;
  --bad:#b42318;
}}
body {{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif;
}}
header {{
  padding:56px 7vw 30px;
  background:linear-gradient(180deg,#fff 0%,#f5f5f7 100%);
}}
h1 {{font-size:44px; line-height:1.08; margin:0 0 14px; font-weight:700; letter-spacing:0;}}
h2 {{font-size:24px; margin:34px 0 16px; letter-spacing:0;}}
.summary {{font-size:18px; color:var(--muted); max-width:980px; line-height:1.6;}}
.grid {{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:24px;}}
.metric {{background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px;}}
.metric b {{display:block; font-size:24px; margin-top:8px;}}
main {{padding:0 7vw 60px;}}
section {{margin-top:18px;}}
table {{width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden;}}
th,td {{padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; font-size:14px;}}
th {{background:#fbfbfd; color:var(--muted); font-weight:600;}}
.note {{color:var(--muted); font-size:13px; line-height:1.5;}}
.warn {{color:var(--bad);}}
.pill {{display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 10px; color:var(--muted); margin-right:6px;}}
</style>
</head>
<body>
<header>
  <div class="pill">{meta['report_version']}</div><div class="pill">数据截止 {meta['as_of']}</div><div class="pill">{meta['data_status']}</div>
  <h1>A 股每日全局复盘与板块资金分析</h1>
  <p class="summary">{report['summary']}</p>
  <p class="note">{meta['disclaimer']}</p>
  <div class="grid">
    <div class="metric">市场状态<b>{report['market_overview']['state']}</b></div>
    <div class="metric">上涨/下跌<b>{report['market_overview']['up_count']} / {report['market_overview']['down_count']}</b></div>
    <div class="metric">涨停/跌停<b>{report['market_overview']['limit_up_count']} / {report['market_overview']['limit_down_count']}</b></div>
    <div class="metric">成交额<b>{report['market_overview']['market_amount']} 亿</b></div>
  </div>
</header>
<main>
<section><h2>行业涨幅前三</h2>{table(report['industry']['gainers_top3'], columns)}</section>
<section><h2>行业跌幅前三</h2>{table(report['industry']['losers_top3'], columns)}</section>
<section><h2>概念涨幅前三</h2>{table(report['concept']['gainers_top3'], columns)}</section>
<section><h2>概念跌幅前三</h2>{table(report['concept']['losers_top3'], columns)}</section>
<section><h2>周线持续流入</h2>{table(report['weekly_flow'][:10], [('sector_name','板块'),('taxonomy','类型'),('category','类型'),('flow_5d','5日资金'),('score','综合分')])}</section>
<section><h2>候选观察池</h2>{table(report['watchlist'][:15], [('stock_code','代码'),('stock_name','名称'),('main_sector','重点板块'),('candidate_type','类型'),('total_score','评分')])}</section>
<section><h2>风险提示</h2><ul>{"".join(f"<li class='warn'>{risk}</li>" for risk in report['risks'])}</ul></section>
</main>
</body>
</html>"""
        return html

    def _write_sector_csv(self, report: dict[str, Any], path: Path) -> None:
        rows = []
        for section_key in ["industry", "concept"]:
            for row in report[section_key]["all_ranked"]:
                rows.append(
                    {
                        "taxonomy": row["taxonomy"],
                        "sector_code": row["sector_code"],
                        "sector_name": row["sector_name"],
                        "change_pct": row["change_pct"],
                        "amount": row["amount"],
                        "main_net_inflow": row["main_net_inflow"],
                        "lifecycle": row["lifecycle"]["stage"],
                        "data_as_of": report["metadata"]["as_of"],
                    }
                )
        self._write_csv(path, rows)

    def _write_leaders_csv(self, report: dict[str, Any], path: Path) -> None:
        rows = []
        for section_key in ["industry", "concept"]:
            for sector in report[section_key]["all_ranked"]:
                for leader in sector["leaders_top5"]:
                    rows.append(
                        {
                            "taxonomy": leader["taxonomy"],
                            "sector_name": leader["sector_name"],
                            "stock_code": leader["stock_code"],
                            "stock_name": leader["stock_name"],
                            "rank_in_sector": leader["rank_in_sector"],
                            "total_score": leader["total_score"],
                            "leader_type": leader["leader_type"],
                            "sub_scores": json.dumps(leader["sub_scores"], ensure_ascii=False),
                            "risk_tips": "；".join(leader["risk_tips"]),
                        }
                    )
        self._write_csv(path, rows)

    def _write_watchlist_csv(self, report: dict[str, Any], path: Path) -> None:
        self._write_csv(path, report["watchlist"])

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_pdf(self, report: dict[str, Any], path: Path) -> None:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ChineseTitle",
            parent=styles["Title"],
            fontName="STSong-Light",
            fontSize=18,
            leading=24,
        )
        body_style = ParagraphStyle(
            "ChineseBody",
            parent=styles["BodyText"],
            fontName="STSong-Light",
            fontSize=10,
            leading=15,
        )
        doc = SimpleDocTemplate(str(path), pagesize=A4)
        story: list[Any] = [
            Paragraph(f"A 股每日全局复盘 - {report['metadata']['report_version']}", title_style),
            Spacer(1, 10),
            Paragraph(report["summary"], body_style),
            Spacer(1, 10),
            Paragraph(f"数据截止：{report['metadata']['as_of']}；是否最终：{report['metadata']['is_final']}", body_style),
            Spacer(1, 10),
        ]
        data = [["类型", "板块", "涨跌幅%", "资金流", "阶段"]]
        for label, rows in [
            ("行业涨幅", report["industry"]["gainers_top3"]),
            ("行业跌幅", report["industry"]["losers_top3"]),
            ("概念涨幅", report["concept"]["gainers_top3"]),
            ("概念跌幅", report["concept"]["losers_top3"]),
        ]:
            for row in rows:
                data.append(
                    [
                        label,
                        row["sector_name"],
                        row["change_pct"],
                        row["main_net_inflow"],
                        row["lifecycle"]["stage"],
                    ]
                )
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f7")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d2d2d7")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 10))
        story.append(Paragraph(DISCLAIMER, body_style))
        doc.build(story)

    def _code_version(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout.strip()
        except Exception:
            return "local-uncommitted"
