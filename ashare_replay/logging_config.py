from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ashare_replay.config import PROJECT_ROOT

SECRET_WORDS = ("TOKEN", "KEY", "PASSWORD", "SECRET")


class SecretMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for word in SECRET_WORDS:
            if word in message.upper():
                record.msg = "[日志已隐藏可能包含密钥的内容]"
                record.args = ()
                break
        return True


def setup_logging(level: str = "INFO") -> None:
    log_dir = PROJECT_ROOT / "work" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(SecretMaskFilter())
    file_handler = RotatingFileHandler(
        Path(log_dir / "ashare_replay.log"),
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(SecretMaskFilter())
    root.addHandler(console)
    root.addHandler(file_handler)
