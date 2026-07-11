from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Protocol


class TradingCalendarProvider(Protocol):
    def get_trading_calendar(self, start: date, end: date) -> list[dict[str, Any]]: ...


class StockBasicProvider(Protocol):
    def get_stock_basic(self) -> list[dict[str, Any]]: ...


class RealtimeQuoteProvider(Protocol):
    def get_realtime_quotes(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class DailyQuoteProvider(Protocol):
    def get_daily_quotes(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class IndexQuoteProvider(Protocol):
    def get_index_quotes(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class IndustrySectorProvider(Protocol):
    def get_industry_sectors(self) -> list[dict[str, Any]]: ...


class ConceptSectorProvider(Protocol):
    def get_concept_sectors(self) -> list[dict[str, Any]]: ...


class SectorConstituentProvider(Protocol):
    def get_sector_constituents(self, trade_date: date) -> list[dict[str, Any]]: ...


class SectorMoneyFlowProvider(Protocol):
    def get_sector_money_flow(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class StockMoneyFlowProvider(Protocol):
    def get_stock_money_flow(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class SentimentProvider(Protocol):
    def get_market_sentiment(self, trade_date: date, as_of: datetime) -> dict[str, Any]: ...


class NewsProvider(Protocol):
    def get_news(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class AnnouncementProvider(Protocol):
    def get_announcements(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class PolicyProvider(Protocol):
    def get_policy_events(self, trade_date: date, as_of: datetime) -> list[dict[str, Any]]: ...


class DataProvider(ABC):
    provider_name: str
    source: str
    mode: str

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """返回 Provider 健康状态，不得隐藏错误。"""

    @abstractmethod
    def get_snapshot(self, trade_date: date, as_of: datetime, report_type: str) -> dict[str, Any]:
        """返回统一字段结构的原始数据快照。"""
