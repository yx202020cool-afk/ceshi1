from __future__ import annotations

import pytest

from ashare_replay.schema_validation import SchemaValidationError, validate_required_object
from ashare_replay.security import mask_secret, safe_download_name


def test_safe_download_name():
    assert safe_download_name("report.json", [".json"]) == "report.json"
    with pytest.raises(ValueError):
        safe_download_name("../secret.env", [".env"])
    with pytest.raises(ValueError):
        safe_download_name("report.exe", [".json"])


def test_secret_masking_and_schema_error():
    assert mask_secret("abcdef123456") == "abc***456"
    with pytest.raises(SchemaValidationError):
        validate_required_object({"metadata": {}})
