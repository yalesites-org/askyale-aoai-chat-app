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


from unittest.mock import MagicMock, patch, AsyncMock


def _make_app_settings(
    admin_system_message=None,
    llm_source="azure",
    datasource=None,
    system_message="You are a helpful assistant.",
    role_information="You are a helpful assistant.",
):
    """Build a mock app_settings for testing prepare_model_args."""
    azure_openai = MagicMock()
    azure_openai.temperature = 0.2
    azure_openai.max_tokens = 1000
    azure_openai.top_p = 1.0
    azure_openai.stop_sequence = None
    azure_openai.stream = True
    azure_openai.model = "gpt-4.1-mini"
    azure_openai.system_message = system_message
    azure_openai.admin_system_message = admin_system_message
    azure_openai.excluded_params = None
    azure_openai.function_call_azure_functions_enabled = False

    base_settings = MagicMock()
    base_settings.llm_source = llm_source
    base_settings.use_promptflow = False

    search = MagicMock()
    search.role_information = role_information

    settings = MagicMock()
    settings.azure_openai = azure_openai
    settings.base_settings = base_settings
    settings.datasource = datasource
    settings.search = search

    return settings


class TestPrepareModelArgsAdminMessage:
    """Integration tests for admin system message in prepare_model_args."""

    @pytest.mark.asyncio
    async def test_no_datasource_no_admin(self):
        """Path 1: No datasource, no admin -- user message only."""
        settings = _make_app_settings(admin_system_message=None)

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_no_datasource_with_admin(self):
        """Path 1: No datasource, with admin -- admin prepended."""
        settings = _make_app_settings(
            admin_system_message="Admin rules here."
        )

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == (
            "Admin rules here.\n\nYou are a helpful assistant."
        )

    @pytest.mark.asyncio
    async def test_portkey_unsupported_datasource_no_admin(self):
        """Path 3: Portkey + unsupported datasource, no admin."""
        mock_datasource = MagicMock()
        mock_datasource.__class__.__name__ = "SomeOtherDatasource"
        settings = _make_app_settings(
            admin_system_message=None,
            llm_source="portkey",
            datasource=mock_datasource,
        )

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_portkey_unsupported_datasource_with_admin(self):
        """Path 3: Portkey + unsupported datasource, with admin."""
        mock_datasource = MagicMock()
        mock_datasource.__class__.__name__ = "SomeOtherDatasource"
        settings = _make_app_settings(
            admin_system_message="Admin rules here.",
            llm_source="portkey",
            datasource=mock_datasource,
        )

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == (
            "Admin rules here.\n\nYou are a helpful assistant."
        )

    @pytest.mark.asyncio
    async def test_portkey_azure_search_no_admin(self):
        """Path 2: Portkey + Azure Search, no admin -- RAG prompt only."""
        from backend.settings import _AzureSearchSettings

        mock_datasource = MagicMock(spec=_AzureSearchSettings)
        settings = _make_app_settings(
            admin_system_message=None,
            llm_source="portkey",
            datasource=mock_datasource,
            role_information="You are a helpful assistant.",
        )

        mock_documents = [
            {"id": "doc1", "title": "Test Doc", "content": "Test content."}
        ]

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False), \
             patch("app.search_documents", new_callable=AsyncMock, return_value=mock_documents), \
             patch("app.build_citations", return_value=[]):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"].startswith("You are a helpful assistant.")
        assert "## Retrieved Sources" in system_msg["content"]
        assert "Test content." in system_msg["content"]

    @pytest.mark.asyncio
    async def test_portkey_azure_search_with_admin(self):
        """Path 2: Portkey + Azure Search, with admin -- admin + RAG prompt."""
        from backend.settings import _AzureSearchSettings

        mock_datasource = MagicMock(spec=_AzureSearchSettings)
        settings = _make_app_settings(
            admin_system_message="Admin rules here.",
            llm_source="portkey",
            datasource=mock_datasource,
            role_information="You are a helpful assistant.",
        )

        mock_documents = [
            {"id": "doc1", "title": "Test Doc", "content": "Test content."}
        ]

        with patch("app.app_settings", settings), \
             patch("app.MS_DEFENDER_ENABLED", False), \
             patch("app.search_documents", new_callable=AsyncMock, return_value=mock_documents), \
             patch("app.build_citations", return_value=[]):
            from app import prepare_model_args

            body = {"messages": [{"role": "user", "content": "hello"}]}
            model_args, _ = await prepare_model_args(body, {})

        system_msg = model_args["messages"][0]
        assert system_msg["role"] == "system"
        assert system_msg["content"].startswith("Admin rules here.\n\n")
        assert "You are a helpful assistant." in system_msg["content"]
        assert "## Retrieved Sources" in system_msg["content"]
        assert "Test content." in system_msg["content"]
