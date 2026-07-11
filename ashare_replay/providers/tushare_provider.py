from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ashare_replay.config import Settings
from ashare_replay.providers.base import DataProvider
from ashare_replay.providers.readiness import ProviderCapability, summarize_capability_results
from ashare_replay.security import mask_secret
from ashare_replay.time_utils import iso_now


def required_tushare_capabilities(settings: Settings) -> list[ProviderCapability]:
    probe = settings.config.get("real_provider_probe", {})
    start_date = probe.get("probe_start_date", "20240102").replace("-", "")
    end_date = probe.get("probe_end_date", "20240105").replace("-", "")
    trade_date = probe.get("probe_trade_date", "20240103").replace("-", "")
    news_start = probe.get("probe_news_start", "2024-01-03 09:00:00")
    news_end = probe.get("probe_news_end", "2024-01-03 15:30:00")
    return [
        ProviderCapability(
            name="交易日历",
            endpoint="trade_cal",
            required=True,
            params={"exchange": "SSE", "start_date": start_date, "end_date": end_date},
        ),
        ProviderCapability(
            name="股票基础信息",
            endpoint="stock_basic",
            required=True,
            params={"exchange": "", "list_status": "L"},
        ),
        ProviderCapability(
            name="日线行情",
            endpoint="daily",
            required=True,
            params={"trade_date": trade_date},
        ),
        ProviderCapability(
            name="指数日线行情",
            endpoint="index_daily",
            required=True,
            params={"ts_code": "000001.SH", "start_date": start_date, "end_date": end_date},
        ),
        ProviderCapability(
            name="个股资金流",
            endpoint="moneyflow",
            required=True,
            params={"trade_date": trade_date},
        ),
        ProviderCapability(
            name="同花顺板块基础",
            endpoint="ths_index",
            required=True,
            params={"exchange": "A", "type": "N"},
        ),
        ProviderCapability(
            name="同花顺板块成分",
            endpoint="ths_member",
            required=True,
            params={"ts_code": "885001.TI"},
            empty_is_ok=True,
        ),
        ProviderCapability(
            name="同花顺板块行情",
            endpoint="ths_daily",
            required=True,
            params={"ts_code": "885001.TI", "start_date": start_date, "end_date": end_date},
            empty_is_ok=True,
        ),
        ProviderCapability(
            name="板块资金流",
            endpoint="moneyflow_ind_ths",
            required=True,
            params={"trade_date": trade_date},
            empty_is_ok=True,
        ),
        ProviderCapability(
            name="新闻",
            endpoint="news",
            required=False,
            params={"src": "sina", "start_date": news_start, "end_date": news_end},
            empty_is_ok=True,
        ),
        ProviderCapability(
            name="上市公司公告",
            endpoint="anns",
            required=False,
            params={"ann_date": trade_date},
            empty_is_ok=True,
        ),
    ]


class TushareProvider(DataProvider):
    """Tushare Pro 真实数据 Provider 入口。

    该实现不会在没有密钥或权限时伪造数据。完整板块资金、个股资金、
    新闻公告权限取决于用户的 Tushare 账号能力。
    """

    provider_name = "tushare"
    source = "Tushare Pro"
    mode = "real"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def health_check(self) -> dict[str, Any]:
        if not self.settings.tushare_token:
            return {
                "provider_name": self.provider_name,
                "status": "missing_token",
                "mode": "real",
                "last_success_at": None,
                "last_error_at": iso_now(self.settings.timezone),
                "last_error": "未配置 TUSHARE_TOKEN",
                "uses_demo_data": 0,
                "is_final": 0,
                "readiness": self.audit_capabilities(run_probes=False),
            }
        try:
            import tushare as ts

            pro = ts.pro_api(self.settings.tushare_token)
            _ = pro.trade_cal(exchange="SSE", start_date="20240101", end_date="20240105")
            return {
                "provider_name": self.provider_name,
                "status": "ok",
                "mode": "real",
                "last_success_at": iso_now(self.settings.timezone),
                "last_error_at": None,
                "last_error": None,
                "uses_demo_data": 0,
                "is_final": 0,
                "readiness": self.audit_capabilities(run_probes=False),
            }
        except Exception as exc:  # pragma: no cover - depends on external service
            return {
                "provider_name": self.provider_name,
                "status": "error",
                "mode": "real",
                "last_success_at": None,
                "last_error_at": iso_now(self.settings.timezone),
                "last_error": f"{type(exc).__name__}: {str(exc)[:180]} token={mask_secret(self.settings.tushare_token)}",
                "uses_demo_data": 0,
                "is_final": 0,
                "readiness": self.audit_capabilities(run_probes=False),
            }

    def audit_capabilities(self, run_probes: bool = True) -> dict[str, Any]:
        capabilities = required_tushare_capabilities(self.settings)
        if not self.settings.tushare_token:
            results = [
                {
                    "name": item.name,
                    "endpoint": item.endpoint,
                    "required": item.required,
                    "status": "missing_token",
                    "rows": None,
                    "message": "未配置 TUSHARE_TOKEN，无法检查真实接口权限。",
                }
                for item in capabilities
            ]
            return {
                "provider": self.provider_name,
                "mode": "real",
                "run_probes": False,
                "token": "",
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
                    "message": "已配置密钥；运行 provider-audit 可检查接口权限。",
                }
                for item in capabilities
            ]
            return {
                "provider": self.provider_name,
                "mode": "real",
                "run_probes": False,
                "token": mask_secret(self.settings.tushare_token),
                "capabilities": results,
                **summarize_capability_results(results),
            }

        try:
            import tushare as ts
        except ImportError:
            results = [
                {
                    "name": item.name,
                    "endpoint": item.endpoint,
                    "required": item.required,
                    "status": "missing_dependency",
                    "rows": None,
                    "message": "未安装 tushare Python 包。",
                }
                for item in capabilities
            ]
            return {
                "provider": self.provider_name,
                "mode": "real",
                "run_probes": False,
                "token": mask_secret(self.settings.tushare_token),
                "capabilities": results,
                **summarize_capability_results(results),
            }

        pro = ts.pro_api(self.settings.tushare_token)
        results = [self._probe_capability(pro, item) for item in capabilities]
        return {
            "provider": self.provider_name,
            "mode": "real",
            "run_probes": True,
            "token": mask_secret(self.settings.tushare_token),
            "capabilities": results,
            **summarize_capability_results(results),
        }

    def _probe_capability(self, pro: Any, item: ProviderCapability) -> dict[str, Any]:
        method = getattr(pro, item.endpoint, None)
        if method is None:
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": "missing_endpoint",
                "rows": None,
                "message": "当前 tushare 客户端没有该接口，请检查版本。",
            }
        try:
            frame = method(**item.params)
            rows = len(frame) if hasattr(frame, "__len__") else None
            if rows == 0 and not item.empty_is_ok and item.min_rows > 0:
                status = "empty_or_no_permission"
                message = "接口可调用但返回空数据，可能是日期无数据或账号权限不足。"
            else:
                status = "ok"
                message = "接口探针调用成功。"
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": status,
                "rows": rows,
                "message": message,
            }
        except Exception as exc:  # pragma: no cover - depends on external service
            return {
                "name": item.name,
                "endpoint": item.endpoint,
                "required": item.required,
                "status": "error",
                "rows": None,
                "message": f"{type(exc).__name__}: {str(exc)[:180]}",
            }

    def get_snapshot(self, trade_date: date, as_of: datetime, report_type: str) -> dict[str, Any]:
        if not self.settings.tushare_token:
            raise RuntimeError(
                "真实数据模式需要先在 .env 中填写 TUSHARE_TOKEN。"
                "系统不会把演示数据标记为真实行情。"
            )
        try:
            import tushare as ts
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError("真实数据模式需要安装 tushare；请在 requirements 中加入后重建容器。") from exc

        pro = ts.pro_api(self.settings.tushare_token)
        trade_date_text = trade_date.strftime("%Y%m%d")
        stock_basic = pro.stock_basic(exchange="", list_status="L")
        daily = pro.daily(trade_date=trade_date_text)
        trade_cal = pro.trade_cal(exchange="SSE", start_date=trade_date_text, end_date=trade_date_text)
        raise RuntimeError(
            "Tushare 基础连接已建立，但完整真实报告还需要开通并映射板块、资金流、新闻和公告权限。"
            f"已验证字段: stock_basic={len(stock_basic)}, daily={len(daily)}, trade_cal={len(trade_cal)}。"
        )
