import json
import pytest
from unittest.mock import patch
from datetime import datetime, timezone as stdlib_tz
from backend.tools.datetime_tool import get_current_datetime, LOCAL_TOOLS, LOCAL_TOOLS_SCHEMAS


def test_get_current_datetime_utc_returns_valid_json():
    result = get_current_datetime()
    data = json.loads(result)
    assert "datetime" in data
    assert "timezone" in data
    assert "date" in data
    assert "time" in data
    assert data["timezone"] == "UTC"


def test_get_current_datetime_with_valid_timezone():
    result = get_current_datetime(timezone="America/New_York")
    data = json.loads(result)
    assert data["timezone"] == "America/New_York"
    assert "datetime" in data


def test_get_current_datetime_invalid_timezone_falls_back_to_utc():
    result = get_current_datetime(timezone="Not/AReal/Zone")
    data = json.loads(result)
    assert data["timezone"] == "UTC"
    assert "datetime" in data


def test_local_tools_registry_contains_datetime():
    assert "get_current_datetime" in LOCAL_TOOLS
    assert callable(LOCAL_TOOLS["get_current_datetime"])


def test_local_tools_schemas_is_valid_openai_format():
    assert len(LOCAL_TOOLS_SCHEMAS) >= 1
    schema = LOCAL_TOOLS_SCHEMAS[0]
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "get_current_datetime"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]
