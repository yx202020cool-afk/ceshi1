from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_replay.config import PROJECT_ROOT


class SchemaValidationError(ValueError):
    pass


def load_report_schema() -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / "schemas" / "report.schema.json").read_text(encoding="utf-8"))


def validate_required_object(payload: dict[str, Any], schema_path: Path | None = None) -> None:
    schema = (
        json.loads(schema_path.read_text(encoding="utf-8"))
        if schema_path
        else load_report_schema()
    )
    required = schema.get("required", [])
    missing = [key for key in required if key not in payload]
    if missing:
        raise SchemaValidationError(f"报告缺少必要字段: {', '.join(missing)}")
    for key, rule in schema.get("properties", {}).items():
        if key not in payload:
            continue
        expected = rule.get("type")
        if expected == "object" and not isinstance(payload[key], dict):
            raise SchemaValidationError(f"{key} 应为对象")
        if expected == "array" and not isinstance(payload[key], list):
            raise SchemaValidationError(f"{key} 应为数组")
