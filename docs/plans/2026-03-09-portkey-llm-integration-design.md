# Portkey LLM Integration Design

## Problem

The application is hardcoded to use Azure OpenAI as its LLM provider. We need the ability to optionally route LLM chat completion calls through Portkey (an AI gateway) while keeping Azure OpenAI as the default and preserving full backwards compatibility.

## Scope

LLM chat completions only. Embeddings, datasource grounding, and all other Azure services remain unchanged.

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `LLM_SOURCE` | `"azure"` | No | `"azure"` or `"portkey"` |
| `PORTKEY_API_KEY` | -- | When `LLM_SOURCE=portkey` | Portkey API key |
| `PORTKEY_BASE_URI` | -- | When `LLM_SOURCE=portkey` | Portkey gateway URL |
| `PORTKEY_MODEL` | -- | When `LLM_SOURCE=portkey` | Model identifier for Portkey routing |

When `LLM_SOURCE` is unset or `"azure"`, existing `AZURE_OPENAI_*` variables are used. No change to existing deployments.

## Design

### Settings (`backend/settings.py`)

1. Add `llm_source: str = "azure"` to `_BaseSettings` (env var `LLM_SOURCE`).
2. Add `_PortkeySettings` class with env prefix `PORTKEY_` containing `api_key`, `base_uri`, and `model` fields.
3. Add optional `portkey: Optional[_PortkeySettings]` to `_AppSettings`, instantiated via model validator (same pattern as `_PromptflowSettings`).
4. Make `_AzureOpenAISettings` instantiation tolerate missing required fields when `LLM_SOURCE=portkey` (Azure OpenAI settings may still be partially present for embedding/datasource config, but the LLM-specific fields like `model` and `endpoint` should not be strictly required).

### Client Init (`app.py`)

Modify `init_openai_client()`:

- If `LLM_SOURCE=azure` (default): existing `AsyncAzureOpenAI` path, unchanged.
- If `LLM_SOURCE=portkey`: create `AsyncOpenAI(api_key=PORTKEY_API_KEY, base_url=PORTKEY_BASE_URI)`. Skip Azure-specific validation (API version check, endpoint check) and Azure function call tools loading.

### Model Args (`app.py`)

In `prepare_model_args()`:

- Use `PORTKEY_MODEL` for the `model` field when `LLM_SOURCE=portkey`, otherwise `AZURE_OPENAI_MODEL`.
- All other params (temperature, max_tokens, top_p, stop, stream, messages) are OpenAI-compatible and remain the same.
- `extra_body.data_sources` is still attached when a datasource is configured; Portkey proxying to Azure OpenAI handles it.

### Title Generation (`app.py`)

`generate_title()` uses `init_openai_client()` and references `app_settings.azure_openai.model`. Update the model reference to be Portkey-aware.

### Dependencies

No new packages. The existing `openai` SDK provides `AsyncOpenAI` which is all Portkey needs.

## Backwards Compatibility

When `LLM_SOURCE` is unset:
- Defaults to `"azure"`
- All existing `AZURE_OPENAI_*` env vars work as before
- No behavioral change whatsoever
