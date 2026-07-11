from __future__ import annotations

import hashlib
import json
from typing import Any


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def score_range(value: float, low: float, high: float) -> float:
    if high == low:
        return 50.0
    return clamp((value - low) / (high - low) * 100.0)


def payload_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 16) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:length]}"


def top_n(rows: list[dict[str, Any]], key: str, n: int = 3, reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: float(row.get(key) or -9999), reverse=reverse)[:n]


def compact_reason(parts: list[str]) -> str:
    clean = [part for part in parts if part]
    return "；".join(clean) if clean else "证据不足，当前仅能给出结构化指标。"
