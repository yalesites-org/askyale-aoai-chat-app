import pytest
from app import _build_system_message


class TestBuildSystemMessage:
    def test_no_admin_message_none(self):
        """When admin is None, returns user message unchanged."""
        result = _build_system_message("Hello")
        assert result == "Hello"

    def test_no_admin_message_empty_string(self):
        """When admin is empty string, returns user message unchanged."""
        result = _build_system_message("Hello", admin_system_message="")
        assert result == "Hello"

    def test_no_admin_message_whitespace_only(self):
        """When admin is whitespace only, returns user message unchanged."""
        result = _build_system_message("Hello", admin_system_message="   ")
        assert result == "Hello"

    def test_admin_message_prepended(self):
        """Admin message is prepended with double newline separator."""
        result = _build_system_message("Hello", admin_system_message="Rules")
        assert result == "Rules\n\nHello"

    def test_multiline_admin_message(self):
        """Multiline admin message is preserved and prepended."""
        result = _build_system_message(
            "Hello", admin_system_message="Rule 1\nRule 2"
        )
        assert result == "Rule 1\nRule 2\n\nHello"
