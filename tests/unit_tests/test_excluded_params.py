import pytest
from unittest.mock import MagicMock, patch


def _make_app_settings(excluded_params=None, llm_source="azure"):
    azure_openai = MagicMock()
    azure_openai.temperature = 0.2
    azure_openai.max_tokens = 1000
    azure_openai.top_p = 1.0
    azure_openai.stop_sequence = None
    azure_openai.stream = True
    azure_openai.model = "gpt-4.1-mini"
    azure_openai.system_message = "You are a helpful assistant."
    azure_openai.excluded_params = excluded_params
    azure_openai.function_call_azure_functions_enabled = False

    base_settings = MagicMock()
    base_settings.llm_source = llm_source
    base_settings.use_promptflow = False

    settings = MagicMock()
    settings.azure_openai = azure_openai
    settings.base_settings = base_settings
    settings.datasource = None
    settings.search = MagicMock()

    return settings


@pytest.mark.asyncio
async def test_no_excluded_params_includes_all():
    """When excluded_params is None, all standard params are present."""
    settings = _make_app_settings(excluded_params=None)

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "temperature" in model_args
    assert "top_p" in model_args
    assert "max_tokens" in model_args
    assert "stream" in model_args
    assert "model" in model_args


@pytest.mark.asyncio
async def test_excluded_params_removes_top_p():
    """Setting excluded_params to 'top_p' removes it from model_args."""
    settings = _make_app_settings(excluded_params="top_p")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "top_p" not in model_args
    assert "temperature" in model_args


@pytest.mark.asyncio
async def test_excluded_params_removes_multiple():
    """Comma-separated list removes all listed params."""
    settings = _make_app_settings(excluded_params="top_p,temperature")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "top_p" not in model_args
    assert "temperature" not in model_args
    assert "max_tokens" in model_args


@pytest.mark.asyncio
async def test_excluded_params_strips_whitespace():
    """Spaces around comma-separated entries are handled."""
    settings = _make_app_settings(excluded_params=" top_p , stop ")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "top_p" not in model_args
    assert "stop" not in model_args
    assert "temperature" in model_args


@pytest.mark.asyncio
async def test_excluded_params_empty_string_includes_all():
    """Empty string for excluded_params behaves the same as None."""
    settings = _make_app_settings(excluded_params="")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "top_p" in model_args
    assert "temperature" in model_args


@pytest.mark.asyncio
async def test_excluded_params_unknown_key_is_ignored():
    """An excluded param that was never in model_args doesn't raise."""
    settings = _make_app_settings(excluded_params="nonexistent_param")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "temperature" in model_args
    assert "top_p" in model_args
