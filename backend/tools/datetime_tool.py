import json
import zoneinfo
from datetime import datetime
from datetime import timezone as stdlib_tz


DATETIME_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": (
            "Get the current date and time. Use this when the user asks about "
            "today's date, the current time, or anything requiring knowledge of "
            "the current moment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "IANA timezone name (e.g. 'America/New_York', "
                        "'Europe/London', 'Asia/Tokyo'). Defaults to UTC."
                    ),
                }
            },
            "required": [],
        },
    },
}


def get_current_datetime(timezone: str = None) -> str:
    """Return current datetime as JSON. Called directly by the backend tool handler."""
    try:
        if timezone:
            tz = zoneinfo.ZoneInfo(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now(stdlib_tz.utc)
        return json.dumps({
            "datetime": now.isoformat(),
            "timezone": timezone or "UTC",
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%I:%M %p %Z"),
        })
    except Exception:
        now = datetime.now(stdlib_tz.utc)
        return json.dumps({
            "datetime": now.isoformat(),
            "timezone": "UTC",
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%I:%M %p UTC"),
        })


# Registry: tool name → callable (used by app.py tool dispatch)
LOCAL_TOOLS: dict[str, callable] = {
    "get_current_datetime": get_current_datetime,
}

# Schemas list passed to model_args["tools"]
LOCAL_TOOLS_SCHEMAS: list[dict] = [DATETIME_TOOL_SCHEMA]
