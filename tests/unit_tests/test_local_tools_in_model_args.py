import pytest
from unittest.mock import MagicMock, patch


def _make_app_settings(function_call_enabled=False, llm_source="azure"):
    azure_openai = MagicMock()
    azure_openai.temperature = 0.2
    azure_openai.max_tokens = 1000
    azure_openai.top_p = 1.0
    azure_openai.stop_sequence = None
    azure_openai.stream = True
    azure_openai.model = "gpt-4.1-mini"
    azure_openai.system_message = "You are a helpful assistant."
    azure_openai.excluded_params = None
    azure_openai.admin_system_message = None
    azure_openai.function_call_azure_functions_enabled = function_call_enabled

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
async def test_local_tools_always_included_in_model_args():
    """get_current_datetime tool is always injected regardless of Azure Functions setting."""
    settings = _make_app_settings(function_call_enabled=False)

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False), patch("app.azure_openai_tools", []):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "What time is it?"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "tools" in model_args
    tool_names = [t["function"]["name"] for t in model_args["tools"]]
    assert "get_current_datetime" in tool_names


@pytest.mark.asyncio
async def test_local_tools_merged_with_azure_tools():
    """Local tools are merged with Azure Function tools when both are present."""
    settings = _make_app_settings(function_call_enabled=True)

    fake_azure_tool = {
        "type": "function",
        "function": {"name": "azure_custom_tool", "description": "test", "parameters": {}}
    }

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False), patch("app.azure_openai_tools", [fake_azure_tool]):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    tool_names = [t["function"]["name"] for t in model_args["tools"]]
    assert "get_current_datetime" in tool_names
    assert "azure_custom_tool" in tool_names


@pytest.mark.asyncio
async def test_process_function_call_handles_datetime_tool():
    """process_function_call invokes get_current_datetime locally."""
    import json

    tool_call = MagicMock()
    tool_call.function.name = "get_current_datetime"
    tool_call.function.arguments = json.dumps({"timezone": "UTC"})

    response = MagicMock()
    response.choices[0].message.tool_calls = [tool_call]
    response.choices[0].message.role = "assistant"

    with patch("app.azure_openai_available_tools", []):
        from app import process_function_call

        messages = await process_function_call(response)

    assert messages is not None
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "function"
    result = json.loads(messages[1]["content"])
    assert "datetime" in result
