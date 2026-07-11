from __future__ import annotations

import hashlib
import math
import random
from datetime import date, datetime, timedelta
from typing import Any

from ashare_replay.config import Settings
from ashare_replay.constants import REPORT_TYPES
from ashare_replay.providers.base import DataProvider
from ashare_replay.time_utils import iso_dt, iso_now

INDUSTRIES = [
    ("IND001", "半导体", 0.7),
    ("IND002", "机器人", 0.55),
    ("IND003", "新能源车", 0.25),
    ("IND004", "医药生物", -0.2),
    ("IND005", "银行", -0.55),
    ("IND006", "煤炭", -0.35),
    ("IND007", "传媒", 0.35),
    ("IND008", "军工", -0.05),
]

CONCEPTS = [
    ("CON001", "人工智能", 0.8),
    ("CON002", "低空经济", 0.45),
    ("CON003", "算力租赁", 0.65),
    ("CON004", "创新药", -0.15),
    ("CON005", "中特估", -0.5),
    ("CON006", "固态电池", 0.2),
    ("CON007", "卫星互联网", -0.25),
    ("CON008", "消费电子", 0.05),
]

BOARD_CYCLE = ["主板", "创业板", "科创板", "北交所"]


def _seed_for(trade_date: date, report_type: str, salt: str = "") -> int:
    raw = f"{trade_date.isoformat()}-{report_type}-{salt}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _common(
    provider: str,
    trade_date: date,
    as_of: datetime,
    report_type: str,
    is_final: bool,
    data_status: str = "demo",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "source": "内置演示数据",
        "provider": provider,
        "trade_date": trade_date.isoformat(),
        "as_of": iso_dt(as_of),
        "effective_at": iso_dt(as_of),
        "fetched_at": iso_now(),
        "created_at": iso_now(),
        "updated_at": iso_now(),
        "report_type": report_type,
        "report_version": REPORT_TYPES[report_type]["label"],
        "is_final": is_final,
        "data_status": data_status,
        "quality_warnings": warnings or ["演示数据，不代表真实行情"],
    }


class DemoProvider(DataProvider):
    provider_name = "demo"
    source = "内置演示数据"
    mode = "demo"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def health_check(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "status": "ok",
            "mode": "demo",
            "last_success_at": iso_now(self.settings.timezone),
            "last_error_at": None,
            "last_error": None,
            "uses_demo_data": 1,
            "is_final": 0,
        }

    def get_snapshot(self, trade_date: date, as_of: datetime, report_type: str) -> dict[str, Any]:
        is_final = bool(REPORT_TYPES[report_type]["is_final"])
        warnings = ["演示数据，不代表真实行情"]
        if report_type == "PRE_CLOSE_PREVIEW":
            warnings.append("盘中预览，非最终收盘数据")
        if report_type == "CLOSE_CONFIRMATION":
            warnings.append("部分资金流字段为收盘后暂定口径")
        if trade_date.weekday() >= 5:
            warnings.append("所选日期不是 A 股常规交易日，演示模式仍可生成用于功能验证")

        stocks = self._stocks()
        sectors = self._sectors()
        constituents = self._constituents(stocks, sectors, trade_date)
        sector_quotes = self._sector_quotes(trade_date, as_of, report_type, sectors, constituents, warnings)
        stock_quotes = self._stock_quotes(trade_date, as_of, report_type, stocks, constituents, sector_quotes, warnings)
        sector_flows, stock_flows = self._money_flows(
            trade_date, as_of, report_type, sector_quotes, stock_quotes, warnings
        )
        snapshot = {
            "meta": _common(self.provider_name, trade_date, as_of, report_type, is_final, "demo", warnings),
            "calendar": self._calendar(trade_date - timedelta(days=30), trade_date + timedelta(days=1)),
            "stocks": stocks,
            "sectors": sectors,
            "constituents": constituents,
            "index_quotes": self._index_quotes(trade_date, as_of, report_type, warnings),
            "stock_quotes": stock_quotes,
            "sector_quotes": sector_quotes,
            "stock_money_flow": stock_flows,
            "sector_money_flow": sector_flows,
            "market_sentiment": self._market_sentiment(trade_date, as_of, stock_quotes, sector_quotes, warnings),
            "news": self._news(trade_date, as_of),
            "announcements": self._announcements(trade_date, as_of, stocks),
            "policy_events": self._policy_events(trade_date, as_of),
        }
        return snapshot

    def _calendar(self, start: date, end: date) -> list[dict[str, Any]]:
        rows = []
        cursor = start
        while cursor <= end:
            rows.append(
                {
                    "trade_date": cursor.isoformat(),
                    "is_trading_day": cursor.weekday() < 5,
                    "reason": "周末休市" if cursor.weekday() >= 5 else "正常交易日",
                    "created_at": iso_now(self.settings.timezone),
                }
            )
            cursor += timedelta(days=1)
        return rows

    def _stocks(self) -> list[dict[str, Any]]:
        prefixes = ["华辰", "中科", "海联", "启明", "瑞达", "长信", "云启", "东方", "北方"]
        suffixes = ["科技", "电子", "智能", "新材", "股份", "能源", "生物", "资本", "制造"]
        stocks: list[dict[str, Any]] = []
        for idx in range(72):
            exchange = "SH" if idx % 2 == 0 else "SZ"
            code_base = 600000 if exchange == "SH" else 300000
            code = f"{code_base + idx:06d}.{exchange}"
            board = BOARD_CYCLE[idx % len(BOARD_CYCLE)]
            stocks.append(
                {
                    "stock_code": code,
                    "stock_name": f"{prefixes[idx % len(prefixes)]}{suffixes[(idx // 3) % len(suffixes)]}",
                    "exchange": exchange,
                    "board": board,
                    "listed_date": "2018-01-01" if idx > 10 else "2026-06-01",
                    "is_st": idx in {14, 38},
                    "is_delisting": idx == 61,
                    "is_new_stock": idx <= 10,
                }
            )
        return stocks

    def _sectors(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now = iso_now(self.settings.timezone)
        for code, name, _bias in INDUSTRIES:
            rows.append(
                {
                    "sector_code": code,
                    "sector_name": name,
                    "taxonomy": "industry",
                    "classification_system": "Demo-CSRC-like",
                    "provider": self.provider_name,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for code, name, _bias in CONCEPTS:
            rows.append(
                {
                    "sector_code": code,
                    "sector_name": name,
                    "taxonomy": "concept",
                    "classification_system": "Demo-Concept",
                    "provider": self.provider_name,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        return rows

    def _constituents(
        self,
        stocks: list[dict[str, Any]],
        sectors: list[dict[str, Any]],
        trade_date: date,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now = iso_now(self.settings.timezone)
        industry_sectors = [s for s in sectors if s["taxonomy"] == "industry"]
        concept_sectors = [s for s in sectors if s["taxonomy"] == "concept"]
        for s_idx, sector in enumerate(industry_sectors):
            members = stocks[s_idx * 9 : (s_idx + 1) * 9]
            for stock in members:
                rows.append(
                    {
                        "sector_code": sector["sector_code"],
                        "sector_name": sector["sector_name"],
                        "taxonomy": "industry",
                        "provider": self.provider_name,
                        "stock_code": stock["stock_code"],
                        "valid_from": "2025-01-01",
                        "valid_to": None,
                        "created_at": now,
                    }
                )
        for s_idx, sector in enumerate(concept_sectors):
            start = (s_idx * 6) % len(stocks)
            member_indexes = [(start + offset * 3) % len(stocks) for offset in range(9)]
            for stock_idx in member_indexes:
                stock = stocks[stock_idx]
                rows.append(
                    {
                        "sector_code": sector["sector_code"],
                        "sector_name": sector["sector_name"],
                        "taxonomy": "concept",
                        "provider": self.provider_name,
                        "stock_code": stock["stock_code"],
                        "valid_from": "2025-01-01",
                        "valid_to": None,
                        "created_at": now,
                    }
                )
        return rows

    def _sector_quotes(
        self,
        trade_date: date,
        as_of: datetime,
        report_type: str,
        sectors: list[dict[str, Any]],
        constituents: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        rng = random.Random(_seed_for(trade_date, report_type, "sector"))
        stage_factor = {"PRE_CLOSE_PREVIEW": 0.82, "CLOSE_CONFIRMATION": 0.95, "POST_CLOSE_FINAL": 1.0}[report_type]
        bias_map = {code: bias for code, _name, bias in [*INDUSTRIES, *CONCEPTS]}
        rows: list[dict[str, Any]] = []
        for sector in sectors:
            bias = bias_map[sector["sector_code"]]
            seasonal = math.sin((_seed_for(trade_date, report_type, sector["sector_code"]) % 360) / 57.3)
            change_pct = round((bias * 3.2 + seasonal * 1.4 + rng.uniform(-0.9, 0.9)) * stage_factor, 2)
            amount = round(80 + abs(change_pct) * 28 + rng.uniform(8, 95), 2)
            amount_change_pct = round(change_pct * 7 + rng.uniform(-18, 28), 2)
            member_count = sum(
                1
                for item in constituents
                if item["sector_code"] == sector["sector_code"] and item["taxonomy"] == sector["taxonomy"]
            )
            up_ratio = max(0.08, min(0.92, 0.5 + change_pct / 12 + rng.uniform(-0.08, 0.08)))
            up_count = max(0, min(member_count, int(round(member_count * up_ratio))))
            down_count = max(0, member_count - up_count - (1 if member_count > 6 else 0))
            flat_count = member_count - up_count - down_count
            limit_up = max(0, int(change_pct // 2.1)) if change_pct > 0 else 0
            limit_down = max(0, int(abs(change_pct) // 2.4)) if change_pct < 0 else 0
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "demo",
                        warnings,
                    ),
                    "sector_code": sector["sector_code"],
                    "sector_name": sector["sector_name"],
                    "taxonomy": sector["taxonomy"],
                    "classification_system": sector["classification_system"],
                    "change_pct": change_pct,
                    "amount": amount,
                    "amount_change_pct": amount_change_pct,
                    "up_count": up_count,
                    "down_count": down_count,
                    "flat_count": flat_count,
                    "limit_up_count": limit_up,
                    "limit_down_count": limit_down,
                    "break_limit_count": max(0, int(rng.random() * max(1, limit_up + 2))),
                    "median_change_pct": round(change_pct * 0.72 + rng.uniform(-0.35, 0.35), 2),
                    "tail_change_pct": round(rng.uniform(-1.8, 1.8), 2),
                    "coverage_ratio": round(rng.uniform(0.82, 1.0), 2),
                    "constituent_count": member_count,
                    "relative_strength": round(change_pct - rng.uniform(-0.4, 0.8), 2),
                }
            )
        return rows

    def _stock_quotes(
        self,
        trade_date: date,
        as_of: datetime,
        report_type: str,
        stocks: list[dict[str, Any]],
        constituents: list[dict[str, Any]],
        sector_quotes: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        rng = random.Random(_seed_for(trade_date, report_type, "stock"))
        quote_by_sector = {(row["sector_code"], row["taxonomy"]): row for row in sector_quotes}
        memberships: dict[str, list[dict[str, Any]]] = {}
        for item in constituents:
            memberships.setdefault(item["stock_code"], []).append(item)
        rows: list[dict[str, Any]] = []
        for idx, stock in enumerate(stocks):
            member_rows = memberships.get(stock["stock_code"], [])
            sector_return = 0.0
            if member_rows:
                returns = [
                    quote_by_sector[(m["sector_code"], m["taxonomy"])]["change_pct"]
                    for m in member_rows
                    if (m["sector_code"], m["taxonomy"]) in quote_by_sector
                ]
                sector_return = sum(returns) / max(1, len(returns))
            stock_noise = rng.uniform(-2.2, 2.4)
            change_pct = round(sector_return * 0.75 + stock_noise, 2)
            is_suspended = idx in {4, 41} and report_type != "PRE_CLOSE_PREVIEW"
            if is_suspended:
                change_pct = 0.0
            price = round(8 + idx * 0.37 + rng.uniform(0, 12), 2)
            amount = round(1.5 + abs(change_pct) * 1.8 + rng.uniform(0.5, 18), 2)
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "demo",
                        warnings,
                    ),
                    **stock,
                    "close_price": price,
                    "change_pct": change_pct,
                    "amount": amount,
                    "turnover_rate": round(rng.uniform(0.6, 18.0), 2),
                    "is_suspended": is_suspended,
                    "limit_up": change_pct >= self._limit_threshold(stock) - 0.3,
                    "limit_down": change_pct <= -self._limit_threshold(stock) + 0.3,
                    "streak_limit_up": max(0, int((change_pct - 3.5) // 1.8)),
                    "tail_change_pct": round(rng.uniform(-2.5, 2.5), 2),
                    "daily_trend": "上行" if change_pct > 1 else ("下行" if change_pct < -1 else "震荡"),
                    "weekly_trend": "上行" if sector_return > 0.8 else ("下行" if sector_return < -0.8 else "震荡"),
                    "memberships": member_rows,
                }
            )
        return rows

    def _limit_threshold(self, stock: dict[str, Any]) -> float:
        if stock["is_st"]:
            return 5.0
        if stock["is_new_stock"]:
            return 44.0 if stock["board"] == "主板" else 20.0
        if stock["board"] in {"创业板", "科创板"}:
            return 20.0
        if stock["board"] == "北交所":
            return 30.0
        return 10.0

    def _money_flows(
        self,
        trade_date: date,
        as_of: datetime,
        report_type: str,
        sector_quotes: list[dict[str, Any]],
        stock_quotes: list[dict[str, Any]],
        warnings: list[str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rng = random.Random(_seed_for(trade_date, report_type, "flow"))
        sector_flows: list[dict[str, Any]] = []
        for quote in sector_quotes:
            net = round(quote["amount"] * quote["change_pct"] * 0.085 + rng.uniform(-5, 7), 2)
            sector_flows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "demo",
                        warnings,
                    ),
                    "sector_code": quote["sector_code"],
                    "sector_name": quote["sector_name"],
                    "taxonomy": quote["taxonomy"],
                    "provider_path": "DemoProvider.synthetic_sector_money_flow",
                    "main_net_inflow": net,
                    "super_large_net_inflow": round(net * 0.34 + rng.uniform(-1.5, 1.5), 2),
                    "large_net_inflow": round(net * 0.42 + rng.uniform(-1.5, 1.5), 2),
                    "medium_net_inflow": round(net * 0.18 + rng.uniform(-1.2, 1.2), 2),
                    "small_net_inflow": round(net * 0.06 + rng.uniform(-1.0, 1.0), 2),
                    "net_inflow_ratio": round(net / max(quote["amount"], 1), 4),
                    "flow_3d": round(net * rng.uniform(1.8, 3.2), 2),
                    "flow_5d": round(net * rng.uniform(2.8, 5.3), 2),
                    "flow_10d": round(net * rng.uniform(3.0, 8.5), 2),
                    "flow_20d": round(net * rng.uniform(3.0, 12.0), 2),
                    "flow_continuity": round(rng.uniform(0.1, 0.95) if net > 0 else rng.uniform(0.0, 0.5), 2),
                    "flow_acceleration": round(rng.uniform(-0.4, 0.8) + quote["change_pct"] / 10, 2),
                    "flow_decay": round(rng.uniform(0.0, 0.8) if net < 0 else rng.uniform(0.0, 0.35), 2),
                    "flow_concentration": round(rng.uniform(0.2, 0.82), 2),
                    "is_final": REPORT_TYPES[report_type]["is_final"],
                    "comparable_across_dates": True,
                    "comparable_across_sectors": True,
                }
            )
        stock_flows: list[dict[str, Any]] = []
        for quote in stock_quotes:
            net = round(quote["amount"] * quote["change_pct"] * 0.075 + rng.uniform(-0.8, 1.1), 2)
            stock_flows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "demo",
                        warnings,
                    ),
                    "stock_code": quote["stock_code"],
                    "stock_name": quote["stock_name"],
                    "provider_path": "DemoProvider.synthetic_stock_money_flow",
                    "main_net_inflow": net,
                    "super_large_net_inflow": round(net * 0.35, 2),
                    "large_net_inflow": round(net * 0.4, 2),
                    "medium_net_inflow": round(net * 0.18, 2),
                    "small_net_inflow": round(net * 0.07, 2),
                    "net_inflow_ratio": round(net / max(quote["amount"], 1), 4),
                    "is_final": REPORT_TYPES[report_type]["is_final"],
                }
            )
        return sector_flows, stock_flows

    def _index_quotes(
        self,
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        rng = random.Random(_seed_for(trade_date, report_type, "index"))
        base = [
            ("000001.SH", "上证指数", 0.15),
            ("399001.SZ", "深证成指", 0.25),
            ("399006.SZ", "创业板指", 0.35),
            ("000300.SH", "沪深300", 0.1),
            ("000852.SH", "中证1000", 0.28),
        ]
        return [
            {
                **_common(
                    self.provider_name,
                    trade_date,
                    as_of,
                    report_type,
                    bool(REPORT_TYPES[report_type]["is_final"]),
                    "demo",
                    warnings,
                ),
                "index_code": code,
                "index_name": name,
                "change_pct": round(bias + rng.uniform(-0.8, 0.9), 2),
                "amount": round(2600 + rng.uniform(-250, 400), 2),
            }
            for code, name, bias in base
        ]

    def _market_sentiment(
        self,
        trade_date: date,
        as_of: datetime,
        stock_quotes: list[dict[str, Any]],
        sector_quotes: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        up = sum(1 for row in stock_quotes if row["change_pct"] > 0.05)
        down = sum(1 for row in stock_quotes if row["change_pct"] < -0.05)
        flat = len(stock_quotes) - up - down
        limit_up = sum(1 for row in stock_quotes if row["limit_up"])
        limit_down = sum(1 for row in stock_quotes if row["limit_down"])
        break_count = sum(row["break_limit_count"] for row in sector_quotes)
        amount = round(sum(row["amount"] for row in stock_quotes), 2)
        return {
            **_common(self.provider_name, trade_date, as_of, "POST_CLOSE_FINAL", True, "demo", warnings),
            "market_amount": amount,
            "amount_change_pct": round(sum(row["amount_change_pct"] for row in sector_quotes) / len(sector_quotes), 2),
            "up_count": up,
            "down_count": down,
            "flat_count": flat,
            "limit_up_count": limit_up,
            "limit_down_count": limit_down,
            "break_limit_count": break_count,
            "break_limit_rate": round(break_count / max(limit_up + break_count, 1), 4),
            "consecutive_limit_up_count": max(0, limit_up // 4),
            "highest_limit_height": max(1, min(7, limit_up // 2 + 1)),
            "up_median_pct": round(sum(row["change_pct"] for row in stock_quotes if row["change_pct"] > 0) / max(up, 1), 2),
            "down_median_pct": round(sum(row["change_pct"] for row in stock_quotes if row["change_pct"] < 0) / max(down, 1), 2),
            "breadth": round(up / max(up + down + flat, 1), 4),
            "profit_effect": round(up / max(up + down, 1), 4),
            "loss_effect": round(down / max(up + down, 1), 4),
            "large_vs_small": "小盘相对占优" if up > down else "大盘相对防守",
            "style_preference": ["成长", "科技", "主题"] if up >= down else ["防御", "价值", "高股息"],
            "data_complete": True,
        }

    def _news(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]:
        common_time = datetime.combine(trade_date, datetime.min.time(), tzinfo=as_of.tzinfo).replace(hour=9, minute=15)
        items = [
            ("N001", "半导体设备国产替代政策支持持续推进", "IND001", "行业政策与订单预期改善。"),
            ("N002", "机器人产业链多家公司披露订单增长", "IND002", "订单和产能扩张成为资金关注点。"),
            ("N003", "算力租赁价格出现区域性上行", "CON003", "算力供需紧张提升主题关注度。"),
            ("N004", "AI 应用公司发布新产品", "CON001", "应用落地带来题材催化。"),
            ("N005", "高股息资产成交降温", "CON005", "资金短线偏好从防御切向成长。"),
        ]
        rows = []
        for news_id, title, sector_code, content in items:
            rows.append(
                {
                    "id": f"{trade_date.isoformat()}-{news_id}",
                    "provider": self.provider_name,
                    "title": title,
                    "content": content,
                    "url": "https://example.invalid/demo-news",
                    "published_at": iso_dt(common_time),
                    "related_sector_codes": [sector_code],
                    "related_stock_codes": [],
                }
            )
        return rows

    def _announcements(self, trade_date: date, as_of: datetime, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        published_at = datetime.combine(trade_date, datetime.min.time(), tzinfo=as_of.tzinfo).replace(hour=12)
        return [
            {
                "id": f"{trade_date.isoformat()}-A{idx}",
                "provider": self.provider_name,
                "title": f"{stock['stock_name']}披露业务进展公告",
                "url": "https://example.invalid/demo-announcement",
                "published_at": iso_dt(published_at),
                "related_stock_codes": [stock["stock_code"]],
            }
            for idx, stock in enumerate(stocks[:6])
        ]

    def _policy_events(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]:
        published_at = datetime.combine(trade_date, datetime.min.time(), tzinfo=as_of.tzinfo).replace(hour=8)
        return [
            {
                "id": f"{trade_date.isoformat()}-P001",
                "provider": self.provider_name,
                "title": "演示政策事件：支持先进制造和数字经济",
                "published_at": iso_dt(published_at),
                "related_sector_codes": ["IND001", "IND002", "CON001", "CON003"],
                "evidence": "演示事件仅用于验证原因归因链路。",
            }
        ]
