# Portkey LLM Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow the app to optionally route LLM chat completions through Portkey instead of Azure OpenAI, controlled by environment variables, with full backwards compatibility.

**Architecture:** Add a `_PortkeySettings` pydantic class and `llm_source` field to settings, then branch `init_openai_client()` to create either `AsyncAzureOpenAI` or `AsyncOpenAI` depending on the source. Use a helper property to resolve the correct model name.

**Tech Stack:** Python 3.11, Quart, openai SDK (AsyncOpenAI), pydantic-settings

---

### Task 1: Add `_PortkeySettings` and `llm_source` to settings

**Files:**
- Modify: `backend/settings.py`

**Step 1: Write the failing test**

Create test dotenv file and test function.

Create file `tests/unit_tests/dotenv_data/dotenv_portkey_source`:

```
LLM_SOURCE=portkey
PORTKEY_API_KEY=pk-test-key-123
PORTKEY_BASE_URI=https://api.portkey.ai/v1
PORTKEY_MODEL=claude-sonnet-4-20250514
```

Add to `tests/unit_tests/test_settings.py`:

```python
def test_dotenv_portkey_source(app_settings):
    assert app_settings.base_settings.llm_source == "portkey"
    assert app_settings.portkey is not None
    assert app_settings.portkey.api_key == "pk-test-key-123"
    assert app_settings.portkey.base_uri == "https://api.portkey.ai/v1"
    assert app_settings.portkey.model == "claude-sonnet-4-20250514"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py::test_dotenv_portkey_source -v`
Expected: FAIL (no `llm_source` or `portkey` attribute)

**Step 3: Write minimal implementation**

In `backend/settings.py`, add `_PortkeySettings` class after `_PromptflowSettings`:

```python
class _PortkeySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PORTKEY_",
        env_file=DOTENV_PATH,
        extra="ignore",
        env_ignore_empty=True
    )

    api_key: str
    base_uri: str
    model: str
```

Add `llm_source` to `_BaseSettings`:

```python
class _BaseSettings(BaseSettings):
    # ... existing fields ...
    llm_source: str = "azure"
```

Add `portkey` field and validator to `_AppSettings`:

```python
class _AppSettings(BaseModel):
    # ... existing fields ...
    portkey: Optional[_PortkeySettings] = None

    @model_validator(mode="after")
    def set_portkey_settings(self) -> Self:
        try:
            self.portkey = _PortkeySettings()
        except ValidationError:
            self.portkey = None
        return self
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py::test_dotenv_portkey_source -v`
Expected: PASS

**Step 5: Run all existing tests to verify no regression**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py -v`
Expected: All tests PASS (existing Azure tests unaffected)

**Step 6: Commit**

```bash
git add backend/settings.py tests/unit_tests/test_settings.py tests/unit_tests/dotenv_data/dotenv_portkey_source
git commit -m "feat: add portkey settings and llm_source to configuration"
```

---

### Task 2: Add test for Azure default when LLM_SOURCE is unset

**Files:**
- Modify: `tests/unit_tests/test_settings.py`

**Step 1: Write the test**

Add to `tests/unit_tests/test_settings.py`:

```python
def test_dotenv_no_datasource_1_default_llm_source(app_settings):
    """Existing Azure config without LLM_SOURCE defaults to azure."""
    assert app_settings.base_settings.llm_source == "azure"
    assert app_settings.portkey is None
    assert app_settings.azure_openai is not None
```

This test reuses the existing `dotenv_no_datasource_1` dotenv file (which has no `LLM_SOURCE` set).

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py::test_dotenv_no_datasource_1_default_llm_source -v`
Expected: PASS (this validates backwards compatibility)

**Step 3: Commit**

```bash
git add tests/unit_tests/test_settings.py
git commit -m "test: verify azure is default llm_source when unset"
```

---

### Task 3: Add helper to resolve current model name

**Files:**
- Modify: `backend/settings.py`

**Step 1: Write the failing test**

Add to `tests/unit_tests/test_settings.py`:

```python
def test_portkey_model_name(app_settings):
    """When LLM_SOURCE=portkey, model_name returns portkey model."""
    assert app_settings.base_settings.llm_source == "portkey"
    assert app_settings.model_name == "claude-sonnet-4-20250514"
```

This reuses `dotenv_portkey_source`. Also add a test using existing Azure dotenv:

```python
def test_dotenv_no_datasource_1_model_name(app_settings):
    """When LLM_SOURCE=azure, model_name returns azure openai model."""
    assert app_settings.model_name == "my_model"
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py::test_portkey_model_name tests/unit_tests/test_settings.py::test_dotenv_no_datasource_1_model_name -v`
Expected: FAIL (no `model_name` attribute)

**Step 3: Write minimal implementation**

Add a `model_name` property to `_AppSettings`:

```python
class _AppSettings(BaseModel):
    # ... existing fields ...

    @property
    def model_name(self) -> str:
        if self.base_settings.llm_source == "portkey" and self.portkey:
            return self.portkey.model
        return self.azure_openai.model
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/settings.py tests/unit_tests/test_settings.py
git commit -m "feat: add model_name property to resolve model by llm_source"
```

---

### Task 4: Modify `init_openai_client()` for Portkey

**Files:**
- Modify: `app.py`

**Step 1: Add AsyncOpenAI import**

Add `AsyncOpenAI` to the existing openai import in `app.py`:

```python
from openai import AsyncAzureOpenAI, AsyncOpenAI
```

**Step 2: Add Portkey branch to `init_openai_client()`**

Replace the body of `init_openai_client()` with a branch. The full function becomes:

```python
async def init_openai_client():
    if app_settings.base_settings.llm_source == "portkey":
        return await _init_portkey_client()
    return await _init_azure_openai_client()


async def _init_portkey_client():
    try:
        if not app_settings.portkey:
            raise ValueError(
                "LLM_SOURCE is set to 'portkey' but Portkey settings "
                "(PORTKEY_API_KEY, PORTKEY_BASE_URI, PORTKEY_MODEL) are not configured"
            )

        return AsyncOpenAI(
            api_key=app_settings.portkey.api_key,
            base_url=app_settings.portkey.base_uri,
        )
    except Exception as e:
        logging.exception("Exception in Portkey client initialization", e)
        raise e


async def _init_azure_openai_client():
    azure_openai_client = None

    try:
        # API version check
        if (
            app_settings.azure_openai.preview_api_version
            < MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
        ):
            raise ValueError(
                f"The minimum supported Azure OpenAI preview API version is '{MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION}'"
            )

        # Endpoint
        if (
            not app_settings.azure_openai.endpoint and
            not app_settings.azure_openai.resource
        ):
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_RESOURCE is required"
            )

        endpoint = (
            app_settings.azure_openai.endpoint
            if app_settings.azure_openai.endpoint
            else f"https://{app_settings.azure_openai.resource}.openai.azure.com/"
        )

        # Authentication
        aoai_api_key = app_settings.azure_openai.key
        ad_token_provider = None
        if not aoai_api_key:
            logging.debug("No AZURE_OPENAI_KEY found, using Azure Entra ID auth")
            async with DefaultAzureCredential() as credential:
                ad_token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default"
                )

        # Deployment
        deployment = app_settings.azure_openai.model
        if not deployment:
            raise ValueError("AZURE_OPENAI_MODEL is required")

        # Default Headers
        default_headers = {"x-ms-useragent": USER_AGENT}

        # Remote function calls
        if app_settings.azure_openai.function_call_azure_functions_enabled:
            azure_functions_tools_url = f"{app_settings.azure_openai.function_call_azure_functions_tools_base_url}?code={app_settings.azure_openai.function_call_azure_functions_tools_key}"
            async with httpx.AsyncClient() as client:
                response = await client.get(azure_functions_tools_url)
            response_status_code = response.status_code
            if response_status_code == httpx.codes.OK:
                azure_openai_tools.extend(json.loads(response.text))
                for tool in azure_openai_tools:
                    azure_openai_available_tools.append(tool["function"]["name"])
            else:
                logging.error(f"An error occurred while getting OpenAI Function Call tools metadata: {response.status_code}")

        azure_openai_client = AsyncAzureOpenAI(
            api_version=app_settings.azure_openai.preview_api_version,
            api_key=aoai_api_key,
            azure_ad_token_provider=ad_token_provider,
            default_headers=default_headers,
            azure_endpoint=endpoint,
        )

        return azure_openai_client
    except Exception as e:
        logging.exception("Exception in Azure OpenAI initialization", e)
        azure_openai_client = None
        raise e
```

**Step 3: Update `prepare_model_args()` to use `model_name`**

Change line in `prepare_model_args()`:

```python
# Before:
"model": app_settings.azure_openai.model

# After:
"model": app_settings.model_name
```

**Step 4: Update `generate_title()` to use `model_name`**

Change line in `generate_title()`:

```python
# Before:
model=app_settings.azure_openai.model,

# After:
model=app_settings.model_name,
```

**Step 5: Run all tests**

Run: `PYTHONPATH=$(pwd) pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add app.py
git commit -m "feat: add portkey client init and model_name routing in app"
```

---

### Task 5: Add Portkey-specific dotenv test for full settings with no Azure OpenAI

**Files:**
- Create: `tests/unit_tests/dotenv_data/dotenv_portkey_no_azure_openai`
- Modify: `tests/unit_tests/test_settings.py`

**Step 1: Create dotenv file**

Create `tests/unit_tests/dotenv_data/dotenv_portkey_no_azure_openai`:

```
LLM_SOURCE=portkey
PORTKEY_API_KEY=pk-test-key-456
PORTKEY_BASE_URI=https://api.portkey.ai/v1
PORTKEY_MODEL=gpt-4o
```

Note: No `AZURE_OPENAI_*` vars at all.

**Step 2: Write test**

```python
def test_dotenv_portkey_no_azure_openai(app_settings):
    """Portkey mode works even without Azure OpenAI settings."""
    assert app_settings.base_settings.llm_source == "portkey"
    assert app_settings.portkey is not None
    assert app_settings.portkey.api_key == "pk-test-key-456"
    assert app_settings.model_name == "gpt-4o"
```

**Step 3: Run test**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py::test_dotenv_portkey_no_azure_openai -v`

If this fails because `_AzureOpenAISettings()` raises a `ValidationError` (missing required `model` and `endpoint`/`resource`), we need to make Azure OpenAI settings optional in `_AppSettings` when `LLM_SOURCE=portkey`.

**Step 4: Make Azure OpenAI settings conditional**

In `_AppSettings`, change the `azure_openai` field and add a validator:

```python
class _AppSettings(BaseModel):
    base_settings: _BaseSettings = _BaseSettings()
    azure_openai: Optional[_AzureOpenAISettings] = None
    # ... rest unchanged ...

    @model_validator(mode="after")
    def set_azure_openai_settings(self) -> Self:
        if self.azure_openai is None:
            try:
                self.azure_openai = _AzureOpenAISettings()
            except ValidationError:
                if self.base_settings.llm_source != "portkey":
                    raise
                self.azure_openai = None
        return self
```

Update `model_name` property to handle `azure_openai` being None:

```python
@property
def model_name(self) -> str:
    if self.base_settings.llm_source == "portkey" and self.portkey:
        return self.portkey.model
    if self.azure_openai:
        return self.azure_openai.model
    raise ValueError("No LLM model configured")
```

**Step 5: Run all tests**

Run: `PYTHONPATH=$(pwd) pytest tests/unit_tests/test_settings.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/settings.py tests/unit_tests/test_settings.py tests/unit_tests/dotenv_data/dotenv_portkey_no_azure_openai
git commit -m "feat: make azure openai settings optional when using portkey"
```

---

### Task 6: Guard Azure-specific code paths in app.py

**Files:**
- Modify: `app.py`

**Step 1: Guard Azure function call features**

In `prepare_model_args()`, the Azure function call tools check should only apply for Azure mode. Wrap the existing condition:

```python
# Before:
if app_settings.azure_openai.function_call_azure_functions_enabled and len(azure_openai_tools) > 0:

# After:
if (
    app_settings.base_settings.llm_source == "azure"
    and app_settings.azure_openai
    and app_settings.azure_openai.function_call_azure_functions_enabled
    and len(azure_openai_tools) > 0
):
```

In `complete_chat_request()`, guard the function call processing:

```python
# Before:
if app_settings.azure_openai.function_call_azure_functions_enabled:

# After:
if (
    app_settings.base_settings.llm_source == "azure"
    and app_settings.azure_openai
    and app_settings.azure_openai.function_call_azure_functions_enabled
):
```

In `stream_chat_request()` `generate()`, same guard:

```python
# Before:
if app_settings.azure_openai.function_call_azure_functions_enabled:

# After:
if (
    app_settings.base_settings.llm_source == "azure"
    and app_settings.azure_openai
    and app_settings.azure_openai.function_call_azure_functions_enabled
):
```

In `conversation_internal()`, guard the streaming check:

```python
# Before:
if app_settings.azure_openai.stream and not app_settings.base_settings.use_promptflow:

# After:
stream = (
    app_settings.azure_openai.stream
    if app_settings.azure_openai
    else True
)
if stream and not app_settings.base_settings.use_promptflow:
```

**Step 2: Run all tests**

Run: `PYTHONPATH=$(pwd) pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: guard azure-specific code paths for portkey compatibility"
```

---

### Task 7: Final validation and cleanup

**Step 1: Run full test suite**

Run: `PYTHONPATH=$(pwd) pytest -v --show-capture=stdout`
Expected: All PASS

**Step 2: Run linting**

Run: `cd frontend && npm run lint`
(Frontend unchanged, but verify no issues)

**Step 3: Manual verification checklist**

Verify by reading the code:
- [ ] `LLM_SOURCE` unset -> Azure path, no behavioral change
- [ ] `LLM_SOURCE=azure` -> Azure path explicitly
- [ ] `LLM_SOURCE=portkey` with Portkey vars -> Portkey `AsyncOpenAI` client
- [ ] `LLM_SOURCE=portkey` without Portkey vars -> clear error
- [ ] `model_name` resolves correctly in both modes
- [ ] `generate_title()` uses `model_name`
- [ ] Azure function call features skip gracefully in Portkey mode
- [ ] No new package dependencies

**Step 4: Commit any cleanup**

If any adjustments needed during review.
