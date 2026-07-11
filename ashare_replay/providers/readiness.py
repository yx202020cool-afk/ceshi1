from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderCapability:
    name: str
    endpoint: str
    required: bool
    params: dict[str, Any]
    min_rows: int = 1
    empty_is_ok: bool = False


def summarize_capability_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    required = [row for row in results if row["required"]]
    failed = [row for row in required if row["status"] != "ok"]
    optional_failed = [row for row in results if not row["required"] and row["status"] != "ok"]
    return {
        "required_count": len(required),
        "required_ok_count": len(required) - len(failed),
        "optional_failed_count": len(optional_failed),
        "can_generate_real_report": not failed,
        "blocked_by": [f"{row['name']}:{row['status']}" for row in failed],
    }
