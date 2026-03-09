import os
import pytest
from importlib import import_module, reload


@pytest.fixture(scope="function")
def dotenv_path(request):
    test_case_name = request.node.originalname.partition("test_")[2]
    return os.path.join(
        os.path.dirname(__file__),
        "dotenv_data",
        test_case_name
    )


@pytest.fixture(scope="function")
def app_settings(dotenv_path):
    # Reload module object to pick up new environment
    os.environ["DOTENV_PATH"] = dotenv_path
    settings_module = import_module("backend.settings")
    settings_module = reload(settings_module)
    
    yield getattr(settings_module, "app_settings")


def test_dotenv_no_datasource_1(app_settings):    
    # Validate model object
    assert app_settings.base_settings.datasource_type is None
    assert app_settings.datasource is None
    assert app_settings.azure_openai is not None
    
    
def test_dotenv_no_datasource_2(app_settings):    
    # Validate model object
    assert app_settings.datasource is None
    assert app_settings.azure_openai is not None

    
def test_dotenv_with_azure_search_success(app_settings):
    # Validate model object
    assert app_settings.search is not None
    assert app_settings.base_settings.datasource_type == "AzureCognitiveSearch"
    assert app_settings.datasource is not None
    assert app_settings.datasource.service == "search_service"
    assert app_settings.azure_openai is not None
    
    # Validate API payload structure
    payload = app_settings.datasource.construct_payload_configuration()
    assert payload["type"] == "azure_search"
    assert payload["parameters"] is not None
    assert payload["parameters"]["endpoint"] == "https://search_service.search.windows.net"
    print(payload)


def test_dotenv_portkey_source(monkeypatch):
    # Clear real PORTKEY_* env vars so dotenv values take precedence
    for key in list(os.environ):
        if key.startswith("PORTKEY_"):
            monkeypatch.delenv(key, raising=False)

    dotenv_path = os.path.join(
        os.path.dirname(__file__), "dotenv_data", "dotenv_portkey_source"
    )
    os.environ["DOTENV_PATH"] = dotenv_path
    settings_module = import_module("backend.settings")
    settings_module = reload(settings_module)
    app_settings = settings_module.app_settings

    assert app_settings.base_settings.llm_source == "portkey"
    assert app_settings.portkey is not None
    assert app_settings.portkey.api_key == "pk-test-key-123"
    assert app_settings.portkey.base_uri == "https://api.portkey.ai/v1"
    assert app_settings.portkey.model == "claude-sonnet-4-20250514"


def test_dotenv_azure_default_llm_source(app_settings):
    """Existing Azure config without LLM_SOURCE defaults to azure."""
    assert app_settings.base_settings.llm_source == "azure"
    assert app_settings.portkey is None
    assert app_settings.azure_openai is not None


def test_dotenv_portkey_model_name(monkeypatch):
    """When LLM_SOURCE=portkey, model_name returns portkey model."""
    for key in list(os.environ):
        if key.startswith("PORTKEY_"):
            monkeypatch.delenv(key, raising=False)

    dotenv_path = os.path.join(
        os.path.dirname(__file__), "dotenv_data", "dotenv_portkey_source"
    )
    os.environ["DOTENV_PATH"] = dotenv_path
    settings_module = import_module("backend.settings")
    settings_module = reload(settings_module)
    app_settings = settings_module.app_settings

    assert app_settings.model_name == "claude-sonnet-4-20250514"


def test_dotenv_azure_default_model_name(app_settings):
    """When LLM_SOURCE=azure, model_name returns azure openai model."""
    assert app_settings.model_name == "my_model"


def test_dotenv_portkey_no_azure_openai(monkeypatch):
    """Portkey mode works even without Azure OpenAI settings."""
    for key in list(os.environ):
        if key.startswith("PORTKEY_"):
            monkeypatch.delenv(key, raising=False)

    dotenv_path = os.path.join(
        os.path.dirname(__file__), "dotenv_data", "dotenv_portkey_no_azure_openai"
    )
    os.environ["DOTENV_PATH"] = dotenv_path
    settings_module = import_module("backend.settings")
    settings_module = reload(settings_module)
    app_settings = settings_module.app_settings

    assert app_settings.base_settings.llm_source == "portkey"
    assert app_settings.portkey is not None
    assert app_settings.portkey.api_key == "pk-test-key-456"
    assert app_settings.model_name == "gpt-4o"
    assert app_settings.azure_openai is None


def test_dotenv_with_elasticsearch_success(app_settings):
    # Validate model object
    assert app_settings.search is not None
    assert app_settings.base_settings.datasource_type == "Elasticsearch"
    assert app_settings.datasource is not None
    assert app_settings.datasource.endpoint == "dummy"
    assert app_settings.azure_openai is not None
    
    # Validate API payload structure
    payload = app_settings.datasource.construct_payload_configuration()
    assert payload["type"] == "elasticsearch"
    assert payload["parameters"] is not None
    assert payload["parameters"]["endpoint"] == "dummy"
    print(payload)

    
    

