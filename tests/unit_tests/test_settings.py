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


def test_dotenv_portkey_source(monkeypatch, app_settings):
    # Clear any real PORTKEY_* env vars that would override dotenv values
    for key in list(os.environ):
        if key.startswith("PORTKEY_"):
            monkeypatch.delenv(key, raising=False)

    # Re-import to pick up dotenv values without env var interference
    from importlib import reload
    import backend.settings as settings_module
    settings_module = reload(settings_module)
    reloaded = settings_module.app_settings

    assert reloaded.base_settings.llm_source == "portkey"
    assert reloaded.portkey is not None
    assert reloaded.portkey.api_key == "pk-test-key-123"
    assert reloaded.portkey.base_uri == "https://api.portkey.ai/v1"
    assert reloaded.portkey.model == "claude-sonnet-4-20250514"


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

    
    

