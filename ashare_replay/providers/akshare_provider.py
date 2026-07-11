from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ashare_replay.config import Settings
from ashare_replay.constants import REPORT_TYPES
from ashare_replay.providers.base import DataProvider
from ashare_replay.providers.readiness import ProviderCapability, summarize_capability_results
from ashare_replay.time_utils import iso_dt, iso_now


def required_akshare_capabilities() -> list[ProviderCapability]:
    return [
        ProviderCapability("A股实时行情", "stock_zh_a_spot_em", True, {}),
        ProviderCapability(
            "A股历史行情",
            "stock_zh_a_hist",
            True,
            {
                "symbol": "000001",
                "period": "daily",
                "start_date": "20240102",
                "end_date": "20240105",
                "adjust": "",
            },
        ),
        ProviderCapability("行业板块列表", "stock_board_industry_name_em", True, {}),
        ProviderCapability("行业板块成分", "stock_board_industry_cons_em", True, {"symbol": "半导体"}),
        ProviderCapability("概念板块列表", "stock_board_concept_name_em", True, {}),
        ProviderCapability("概念板块成分", "stock_board_concept_cons_em", True, {"symbol": "人工智能"}),
        ProviderCapability(
            "板块资金流",
            "stock_sector_fund_flow_rank",
            False,
            {"indicator": "今日", "sector_type": "行业资金流"},
            empty_is_ok=True,
        ),
        ProviderCapability(
            "个股资金流",
            "stock_individual_fund_flow_rank",
            False,
            {"indicator": "今日"},
            empty_is_ok=True,
        ),
        ProviderCapability("个股新闻", "stock_news_em", False, {"symbol": "000001"}, empty_is_ok=True),
    ]


def _common(
    provider: str,
    trade_date: date,
    as_of: datetime,
    report_type: str,
    is_final: bool,
    data_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "source": "AKShare 免费公开数据",
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
        "quality_warnings": warnings,
    }


def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    try:
        text = str(value).replace(",", "").replace("%", "").strip()
        if text in {"", "-", "None", "nan"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    number = _safe_float(value, float(default))
    return int(number or default)


def _pick(row: dict[str, Any], names: list[str], default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in {None, ""}:
            return row[name]
    return default


def _records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        return list(frame.to_dict(orient="records"))
    if isinstance(frame, list):
        return [dict(item) for item in frame if isinstance(item, dict)]
    return []


def _plain_code(value: Any) -> str:
    text = str(value).strip()
    if "." in text:
        return text.split(".", 1)[0]
    return text.zfill(6) if text.isdigit() else text


def _exchange(code: str) -> str:
    plain = _plain_code(code)
    if plain.startswith("6"):
        return "SH"
    if plain.startswith(("8", "4")):
        return "BJ"
    return "SZ"


def _full_code(code: str) -> str:
    plain = _plain_code(code)
    return f"{plain}.{_exchange(plain)}"


def _board(code: str) -> str:
    plain = _plain_code(code)
    if plain.startswith("688"):
        return "科创板"
    if plain.startswith(("300", "301")):
        return "创业板"
    if plain.startswith(("8", "4")):
        return "北交所"
    return "主板"


class AkshareProvider(DataProvider):
    provider_name = "akshare"
    source = "AKShare 免费公开数据"
    mode = "real"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def health_check(self) -> dict[str, Any]:
        try:
            import akshare as ak  # noqa: F401
        except ImportError:
            return {
                "provider_name": self.provider_name,
                "status": "missing_dependency",
                "mode": "real",
                "last_success_at": None,
                "last_error_at": iso_now(self.settings.timezone),
                "last_error": "未安装 akshare；Docker 构建会按 requirements.txt 安装。",
                "uses_demo_data": 0,
                "is_final": 0,
                "readiness": self.audit_capabilities(run_probes=False),
            }
        return {
            "provider_name": self.provider_name,
            "status": "available_not_checked",
            "mode": "real",
            "last_success_at": iso_now(self.settings.timezone),
            "last_error_at": None,
            "last_error": None,
            "uses_demo_data": 0,
            "is_final": 0,
            "readiness": self.audit_capabilities(run_probes=False),
        }

    def audit_capabilities(self, run_probes: bool = True) -> dict[str, Any]:
        capabilities = required_akshare_capabilities()
        try:
            import akshare as ak
        except ImportError:
            results = [
                {
                    "name": item.name,
                    "endpoint": item.endpoint,
                    "required": item.required,
                    "status": "missing_dependency",
                    "rows": None,
                    "message": "未安装 akshare Python 包。",
                }
                for item in capabilities
            ]
            return {
                "provider": self.provider_name,
                "mode": "real",
                "run_probes": False,
                "token_required": False,
                "capabilities": results,
                **summarize_capability_results(results),
            }

        if not run_probes:
            results = [
                {
                    "name": item.name,
                    "endpoint": item.endpoint,
                    "required": item.required,
                    "status": "not_checked",
                    "rows": None,
                    "message": "已安装 akshare；运行 provider-audit 可调用公开接口检查可用性。",
                }
                for item in capabilities
            ]
            return {
                "provider": self.provider_name,
                "mode": "real",
                "run_probes": False,
                "token_required": False,
                "capabilities": results,
                **summarize_capability_results(results),
            }

        results = [self._probe_capability(ak, item) for item in capabilities]
        return {
            "provider": self.provider_name,
            "mode": "real",
            "run_probes": True,
            "token_required": False,
            "capabilities": results,
            **summarize_capability_results(results),
        }

    def _probe_capability(self, ak: Any, item: ProviderCapability) -> dict[str, Any]:
        method = getattr(ak, item.endpoint, None)
        if method is None:
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": "missing_endpoint",
                "rows": None,
                "message": "当前 akshare 版本没有该接口。",
            }
        try:
            frame = method(**item.params)
            rows = len(frame) if hasattr(frame, "__len__") else None
            status = "ok"
            message = "公开接口探针调用成功。"
            if rows == 0 and not item.empty_is_ok and item.min_rows > 0:
                status = "empty"
                message = "公开接口可调用但返回空数据。"
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": status,
                "rows": rows,
                "message": message,
            }
        except Exception as exc:  # pragma: no cover - depends on external public sites
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": "error",
                "rows": None,
                "message": f"{type(exc).__name__}: {str(exc)[:180]}",
            }

    def get_snapshot(self, trade_date: date, as_of: datetime, report_type: str) -> dict[str, Any]:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError(
                "真实免费数据模式需要安装 akshare。Docker 启动会自动安装；"
                "本机运行请执行 pip install -r requirements.txt。"
            ) from exc

        is_final = bool(REPORT_TYPES[report_type]["is_final"])
        warnings = [
            "AKShare 免费公开数据仅用于研究参考，不构成投资建议。",
            "公开数据源字段和更新时间可能变化；系统会保留缺失项和质量警告。",
            "AKShare 免费口径暂不保证新闻、公告和全部资金流字段完整。",
            "板块成分的 valid_from 表示本次报告交易日快照，不代表历史成分真实生效日期。",
            "AKShare 免费 Provider 未读取上市日期，相关字段标记为未知。",
        ]
        spot = _records(ak.stock_zh_a_spot_em())
        if not spot:
            raise RuntimeError("AKShare stock_zh_a_spot_em 未返回 A 股行情数据。")
        industries = self._sector_rows(ak, "industry")
        concepts = self._sector_rows(ak, "concept")
        sector_rows = [*industries, *concepts]
        constituents = self._constituents(ak, sector_rows, trade_date)
        stock_rows = self._stock_basics(spot, constituents)
        stock_quotes = self._stock_quotes(spot, stock_rows, constituents, trade_date, as_of, report_type, warnings)
        sector_quotes = self._sector_quotes(sector_rows, constituents, trade_date, as_of, report_type, warnings)
        sector_money_flow = self._sector_money_flow(
            ak, sector_rows, trade_date, as_of, report_type, warnings
        )
        stock_money_flow = self._stock_money_flow(
            ak, stock_rows, stock_quotes, trade_date, as_of, report_type, warnings
        )
        return {
            "meta": _common(
                self.provider_name,
                trade_date,
                as_of,
                report_type,
                is_final,
                "partial",
                warnings,
            ),
            "calendar": [
                {
                    "trade_date": trade_date.isoformat(),
                    "is_trading_day": trade_date.weekday() < 5,
                    "reason": "AKShare 免费 Provider 按用户指定日期生成",
                    "created_at": iso_now(self.settings.timezone),
                }
            ],
            "stocks": stock_rows,
            "sectors": [
                {
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "taxonomy": row["taxonomy"],
                    "classification_system": row["classification_system"],
                    "provider": self.provider_name,
                    "created_at": iso_now(self.settings.timezone),
                    "updated_at": iso_now(self.settings.timezone),
                }
                for row in sector_rows
            ],
            "constituents": constituents,
            "index_quotes": self._index_quotes(stock_quotes, trade_date, as_of, report_type, warnings),
            "stock_quotes": stock_quotes,
            "sector_quotes": sector_quotes,
            "stock_money_flow": stock_money_flow,
            "sector_money_flow": sector_money_flow,
            "market_sentiment": self._market_sentiment(stock_quotes, trade_date, as_of, report_type, warnings),
            "news": [],
            "announcements": [],
            "policy_events": [],
        }

    def _sector_rows(self, ak: Any, taxonomy: str) -> list[dict[str, Any]]:
        if taxonomy == "industry":
            frame = ak.stock_board_industry_name_em()
            classification = "AKShare-Eastmoney-Industry"
            code_prefix = "AKIND"
        else:
            frame = ak.stock_board_concept_name_em()
            classification = "AKShare-Eastmoney-Concept"
            code_prefix = "AKCON"
        rows = []
        for idx, row in enumerate(_records(frame), start=1):
            name = str(_pick(row, ["板块名称", "名称", "行业名称", "概念名称"], f"{taxonomy}-{idx}"))
            code = str(_pick(row, ["板块代码", "代码"], f"{code_prefix}{idx:04d}"))
            rows.append(
                {
                    "sector_code": code or f"{code_prefix}{idx:04d}",
                    "sector_name": name,
                    "taxonomy": taxonomy,
                    "classification_system": classification,
                    "change_pct": _safe_float(_pick(row, ["涨跌幅", "涨幅"]), 0.0) or 0.0,
                    "amount": (_safe_float(_pick(row, ["成交额", "成交金额"]), 0.0) or 0.0) / 100000000,
                    "amount_change_pct": 0.0,
                    "up_count": _safe_int(_pick(row, ["上涨家数", "上涨数"]), 0),
                    "down_count": _safe_int(_pick(row, ["下跌家数", "下跌数"]), 0),
                    "flat_count": 0,
                    "limit_up_count": 0,
                    "limit_down_count": 0,
                    "break_limit_count": 0,
                    "median_change_pct": _safe_float(_pick(row, ["涨跌幅", "涨幅"]), 0.0) or 0.0,
                    "tail_change_pct": 0.0,
                    "relative_strength": _safe_float(_pick(row, ["涨跌幅", "涨幅"]), 0.0) or 0.0,
                }
            )
        return sorted(rows, key=lambda item: item["change_pct"], reverse=True)

    def _constituents(
        self,
        ak: Any,
        sectors: list[dict[str, Any]],
        trade_date: date,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        selected: list[dict[str, Any]] = []
        for taxonomy in ["industry", "concept"]:
            scoped = [row for row in sectors if row["taxonomy"] == taxonomy]
            selected.extend(scoped[:8])
            selected.extend(scoped[-4:])
        seen_sector: set[tuple[str, str]] = set()
        now = iso_now(self.settings.timezone)
        for sector in selected:
            key = (sector["sector_code"], sector["taxonomy"])
            if key in seen_sector:
                continue
            seen_sector.add(key)
            try:
                if sector["taxonomy"] == "industry":
                    frame = ak.stock_board_industry_cons_em(symbol=sector["sector_name"])
                else:
                    frame = ak.stock_board_concept_cons_em(symbol=sector["sector_name"])
            except Exception:
                frame = None
            if frame is None:
                continue
            for item in _records(frame):
                code = _full_code(str(_pick(item, ["代码", "股票代码", "证券代码"], "")))
                if not code.strip("."):
                    continue
                rows.append(
                    {
                        "sector_code": sector["sector_code"],
                        "sector_name": sector["sector_name"],
                        "taxonomy": sector["taxonomy"],
                        "provider": self.provider_name,
                        "stock_code": code,
                        "valid_from": trade_date.isoformat(),
                        "valid_to": None,
                        "created_at": now,
                    }
                )
        return rows

    def _stock_basics(
        self,
        spot: list[dict[str, Any]],
        constituents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        names_by_code = {
            _full_code(str(_pick(row, ["代码"], ""))): str(_pick(row, ["名称"], ""))
            for row in spot
            if _pick(row, ["代码"], "")
        }
        needed = {item["stock_code"] for item in constituents}
        if len(needed) < 50:
            needed.update(list(names_by_code)[:80])
        rows = []
        for code in sorted(needed):
            name = names_by_code.get(code)
            if not name:
                continue
            rows.append(
                {
                    "stock_code": code,
                    "stock_name": name,
                    "exchange": _exchange(code),
                    "board": _board(code),
                    "listed_date": "未知",
                    "is_st": name.upper().startswith("ST") or "*ST" in name.upper(),
                    "is_delisting": "退" in name,
                    "is_new_stock": False,
                }
            )
        return rows

    def _stock_quotes(
        self,
        spot: list[dict[str, Any]],
        stocks: list[dict[str, Any]],
        constituents: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        spot_by_code = {_full_code(str(_pick(row, ["代码"], ""))): row for row in spot}
        memberships: dict[str, list[dict[str, Any]]] = {}
        for item in constituents:
            memberships.setdefault(item["stock_code"], []).append(item)
        rows = []
        for stock in stocks:
            raw = spot_by_code.get(stock["stock_code"], {})
            change_pct = _safe_float(_pick(raw, ["涨跌幅"]), 0.0) or 0.0
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "normal",
                        warnings,
                    ),
                    **stock,
                    "close_price": _safe_float(_pick(raw, ["最新价", "收盘"]), 0.0),
                    "change_pct": change_pct,
                    "amount": (_safe_float(_pick(raw, ["成交额"]), 0.0) or 0.0) / 100000000,
                    "turnover_rate": _safe_float(_pick(raw, ["换手率"]), 0.0) or 0.0,
                    "is_suspended": False,
                    "limit_up": change_pct >= 9.8,
                    "limit_down": change_pct <= -9.8,
                    "streak_limit_up": 0,
                    "tail_change_pct": _safe_float(_pick(raw, ["涨速"]), 0.0) or 0.0,
                    "daily_trend": "上行" if change_pct > 1 else ("下行" if change_pct < -1 else "震荡"),
                    "weekly_trend": "公开数据未计算",
                    "memberships": memberships.get(stock["stock_code"], []),
                }
            )
        return rows

    def _sector_quotes(
        self,
        sectors: list[dict[str, Any]],
        constituents: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        member_counts: dict[tuple[str, str], int] = {}
        for item in constituents:
            key = (item["sector_code"], item["taxonomy"])
            member_counts[key] = member_counts.get(key, 0) + 1
        rows = []
        for sector in sectors:
            key = (sector["sector_code"], sector["taxonomy"])
            count = member_counts.get(key, 0)
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "normal" if count else "missing",
                        warnings if count else [*warnings, "该板块未能从 AKShare 获取成分股。"],
                    ),
                    **sector,
                    "coverage_ratio": 1.0 if count else 0.0,
                    "constituent_count": count,
                }
            )
        return rows

    def _sector_money_flow(
        self,
        ak: Any,
        sectors: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        flow_by_name: dict[str, dict[str, Any]] = {}
        try:
            flow_rows = _records(
                ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
            )
            flow_by_name = {str(_pick(row, ["名称", "行业", "板块名称"], "")): row for row in flow_rows}
        except Exception:
            warnings.append("AKShare 当前环境未能获取板块资金流，相关字段显示为不支持。")
        rows = []
        for sector in sectors:
            raw = flow_by_name.get(sector["sector_name"], {})
            net = _safe_float(_pick(raw, ["今日主力净流入-净额", "主力净流入", "净流入"]), None)
            amount = max(float(sector.get("amount") or 0), 0.01)
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "normal" if net is not None else "missing",
                        warnings,
                    ),
                    "sector_code": sector["sector_code"],
                    "sector_name": sector["sector_name"],
                    "taxonomy": sector["taxonomy"],
                    "provider_path": "akshare.stock_sector_fund_flow_rank",
                    "main_net_inflow": (net / 100000000) if net is not None else None,
                    "super_large_net_inflow": None,
                    "large_net_inflow": None,
                    "medium_net_inflow": None,
                    "small_net_inflow": None,
                    "net_inflow_ratio": (net / 100000000 / amount) if net is not None else None,
                    "flow_3d": None,
                    "flow_5d": None,
                    "flow_10d": None,
                    "flow_20d": None,
                    "flow_continuity": 0.0,
                    "flow_acceleration": 0.0,
                    "flow_decay": 0.0,
                    "flow_concentration": 0.0,
                    "is_final": bool(REPORT_TYPES[report_type]["is_final"]),
                    "comparable_across_dates": False,
                    "comparable_across_sectors": True,
                }
            )
        return rows

    def _stock_money_flow(
        self,
        ak: Any,
        stocks: list[dict[str, Any]],
        stock_quotes: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        flow_by_code: dict[str, dict[str, Any]] = {}
        try:
            flow_rows = _records(ak.stock_individual_fund_flow_rank(indicator="今日"))
            flow_by_code = {_full_code(str(_pick(row, ["代码"], ""))): row for row in flow_rows}
        except Exception:
            warnings.append("AKShare 当前环境未能获取个股资金流，相关字段显示为不支持。")
        quote_by_code = {row["stock_code"]: row for row in stock_quotes}
        rows = []
        for stock in stocks:
            raw = flow_by_code.get(stock["stock_code"], {})
            net = _safe_float(_pick(raw, ["今日主力净流入-净额", "主力净流入", "净流入"]), None)
            amount = max(float(quote_by_code.get(stock["stock_code"], {}).get("amount") or 0), 0.01)
            rows.append(
                {
                    **_common(
                        self.provider_name,
                        trade_date,
                        as_of,
                        report_type,
                        bool(REPORT_TYPES[report_type]["is_final"]),
                        "normal" if net is not None else "missing",
                        warnings,
                    ),
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "provider_path": "akshare.stock_individual_fund_flow_rank",
                    "main_net_inflow": (net / 100000000) if net is not None else None,
                    "super_large_net_inflow": None,
                    "large_net_inflow": None,
                    "medium_net_inflow": None,
                    "small_net_inflow": None,
                    "net_inflow_ratio": (net / 100000000 / amount) if net is not None else None,
                    "is_final": bool(REPORT_TYPES[report_type]["is_final"]),
                }
            )
        return rows

    def _index_quotes(
        self,
        stock_quotes: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        avg = sum(row["change_pct"] for row in stock_quotes) / max(len(stock_quotes), 1)
        return [
            {
                **_common(
                    self.provider_name,
                    trade_date,
                    as_of,
                    report_type,
                    bool(REPORT_TYPES[report_type]["is_final"]),
                    "missing",
                    [
                        *warnings,
                        "未接入正式指数行情；此字段为样本股票涨跌均值，不作为官方指数。",
                    ],
                ),
                "index_code": "AK-A-SAMPLE",
                "index_name": "A股样本涨跌均值（非指数）",
                "change_pct": round(avg, 2),
                "amount": round(sum(row["amount"] for row in stock_quotes), 2),
            }
        ]

    def _market_sentiment(
        self,
        stock_quotes: list[dict[str, Any]],
        trade_date: date,
        as_of: datetime,
        report_type: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        up = sum(1 for row in stock_quotes if row["change_pct"] > 0.05)
        down = sum(1 for row in stock_quotes if row["change_pct"] < -0.05)
        flat = len(stock_quotes) - up - down
        limit_up = sum(1 for row in stock_quotes if row["limit_up"])
        limit_down = sum(1 for row in stock_quotes if row["limit_down"])
        return {
            **_common(
                self.provider_name,
                trade_date,
                as_of,
                report_type,
                bool(REPORT_TYPES[report_type]["is_final"]),
                "normal",
                warnings,
            ),
            "market_amount": round(sum(row["amount"] for row in stock_quotes), 2),
            "amount_change_pct": 0.0,
            "up_count": up,
            "down_count": down,
            "flat_count": flat,
            "limit_up_count": limit_up,
            "limit_down_count": limit_down,
            "break_limit_count": 0,
            "break_limit_rate": 0.0,
            "consecutive_limit_up_count": 0,
            "highest_limit_height": 1,
            "up_median_pct": round(
                sum(row["change_pct"] for row in stock_quotes if row["change_pct"] > 0) / max(up, 1),
                2,
            ),
            "down_median_pct": round(
                sum(row["change_pct"] for row in stock_quotes if row["change_pct"] < 0) / max(down, 1),
                2,
            ),
            "breadth": round(up / max(len(stock_quotes), 1), 4),
            "profit_effect": round(up / max(up + down, 1), 4),
            "loss_effect": round(down / max(up + down, 1), 4),
            "large_vs_small": "AKShare 免费口径暂不支持大小盘分解",
            "style_preference": ["公开口径暂不支持"],
            "data_complete": True,
        }
