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
async def test_local_tools_injected_for_portkey():
    """get_current_datetime tool is injected for portkey regardless of Azure Functions setting."""
    settings = _make_app_settings(function_call_enabled=False, llm_source="portkey")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False), patch("app.azure_openai_tools", []):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "What time is it?"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "tools" in model_args
    tool_names = [t["function"]["name"] for t in model_args["tools"]]
    assert "get_current_datetime" in tool_names


@pytest.mark.asyncio
async def test_local_tools_not_injected_for_azure_without_flag():
    """Local tools are not injected for Azure when function calling is not enabled."""
    settings = _make_app_settings(function_call_enabled=False, llm_source="azure")

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False), patch("app.azure_openai_tools", []):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    assert "tools" not in model_args


@pytest.mark.asyncio
async def test_azure_functions_tools_injected_for_azure_with_flag():
    """Azure Functions tools are injected for Azure when the flag is enabled."""
    settings = _make_app_settings(function_call_enabled=True, llm_source="azure")

    fake_azure_tool = {
        "type": "function",
        "function": {"name": "azure_custom_tool", "description": "test", "parameters": {}}
    }

    with patch("app.app_settings", settings), patch("app.MS_DEFENDER_ENABLED", False), patch("app.azure_openai_tools", [fake_azure_tool]):
        from app import prepare_model_args

        body = {"messages": [{"role": "user", "content": "hello"}]}
        model_args, _ = await prepare_model_args(body, {})

    tool_names = [t["function"]["name"] for t in model_args["tools"]]
    assert "azure_custom_tool" in tool_names
    assert "get_current_datetime" not in tool_names


@pytest.mark.asyncio
async def test_process_function_call_portkey_uses_tools_format():
    """Portkey path: process_function_call uses role:tool and tool_calls array."""
    import json

    settings = _make_app_settings(llm_source="portkey")
    tool_call = MagicMock()
    tool_call.function.name = "get_current_datetime"
    tool_call.function.arguments = json.dumps({"timezone": "UTC"})

    response = MagicMock()
    response.choices[0].message.tool_calls = [tool_call]
    response.choices[0].message.role = "assistant"

    with patch("app.app_settings", settings), patch("app.azure_openai_available_tools", []):
        from app import process_function_call
        messages = await process_function_call(response)

    assert messages is not None
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant"
    assert "tool_calls" in messages[0]
    assert messages[1]["role"] == "tool"
    assert "tool_call_id" in messages[1]
    result = json.loads(messages[1]["content"])
    assert "datetime" in result


@pytest.mark.asyncio
async def test_process_function_call_azure_uses_function_format():
    """Azure path: process_function_call uses role:function and function_call (original format)."""
    import json

    settings = _make_app_settings(llm_source="azure", function_call_enabled=True)
    tool_call = MagicMock()
    tool_call.function.name = "get_current_datetime"
    tool_call.function.arguments = json.dumps({"timezone": "UTC"})

    response = MagicMock()
    response.choices[0].message.tool_calls = [tool_call]
    response.choices[0].message.role = "assistant"

    with patch("app.app_settings", settings), patch("app.azure_openai_available_tools", []):
        from app import process_function_call
        messages = await process_function_call(response)

    assert messages is not None
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant"
    assert "function_call" in messages[0]
    assert "tool_calls" not in messages[0]
    assert messages[1]["role"] == "function"
    assert "name" in messages[1]
    result = json.loads(messages[1]["content"])
    assert "datetime" in result
