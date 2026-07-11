from __future__ import annotations

import re
from pathlib import Path

SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.\-\u4e00-\u9fa5]+$")


def safe_download_name(filename: str, allowed_extensions: list[str], max_length: int = 120) -> str:
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("文件名不能包含路径")
    name = Path(filename).name
    if len(name) > max_length:
        raise ValueError("文件名过长")
    if not SAFE_FILENAME_RE.match(name):
        raise ValueError("文件名包含不安全字符")
    if Path(name).suffix.lower() not in allowed_extensions:
        raise ValueError("文件类型不允许下载")
    return name


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"
