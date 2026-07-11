from __future__ import annotations

from ashare_replay.config import Settings
from ashare_replay.providers.akshare_provider import AkshareProvider
from ashare_replay.providers.base import DataProvider
from ashare_replay.providers.demo import DemoProvider
from ashare_replay.providers.tushare_provider import TushareProvider


def build_provider(settings: Settings) -> DataProvider:
    if settings.app_mode == "real":
        if settings.real_provider == "akshare":
            return AkshareProvider(settings)
        if settings.real_provider == "tushare":
            return TushareProvider(settings)
        raise ValueError(f"暂不支持真实数据 Provider: {settings.real_provider}")
    return DemoProvider(settings)
