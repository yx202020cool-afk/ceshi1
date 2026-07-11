from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Shanghai"


def get_tz(name: str = DEFAULT_TIMEZONE) -> ZoneInfo:
    return ZoneInfo(name)


def now_tz(tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    return datetime.now(tz=get_tz(tz_name))


def parse_trade_date(value: str | date | None, tz_name: str = DEFAULT_TIMEZONE) -> date:
    if value is None or value == "today":
        return now_tz(tz_name).date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def as_of_datetime(trade_date: date, hhmm: str, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    hour, minute = [int(part) for part in hhmm.split(":", 1)]
    return datetime.combine(trade_date, time(hour=hour, minute=minute), tzinfo=get_tz(tz_name))


def iso_dt(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def iso_now(tz_name: str = DEFAULT_TIMEZONE) -> str:
    return iso_dt(now_tz(tz_name))


def ensure_not_future(value: datetime, tz_name: str = DEFAULT_TIMEZONE) -> None:
    current = now_tz(tz_name)
    if value > current:
        raise ValueError(f"数据截止时间不能晚于当前时间: as_of={value.isoformat()}")
