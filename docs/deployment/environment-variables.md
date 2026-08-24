# Environment Variables Reference

This document covers all environment variables supported by the application. Variables are loaded from a `.env` file at the project root. See `.env.sample` for a template.

Variables marked **required** must be set for the application to start. All other variables are optional unless noted otherwise for a specific datasource.

---

## Table of Contents

1. [General Settings](#general-settings)
2. [Azure OpenAI](#azure-openai)
3. [Portkey](#portkey)
4. [User Interface](#user-interface)
5. [Chat History (CosmosDB)](#chat-history-cosmosdb)
6. [Search Common](#search-common)
7. [Azure AI Search](#azure-ai-search)
8. [Other Datasources](#other-datasources)
   - [CosmosDB Mongo vCore](#cosmosdb-mongo-vcore)
   - [Elasticsearch](#elasticsearch)
   - [Pinecone](#pinecone)
   - [Azure ML Index](#azure-ml-index)
   - [Azure SQL Server](#azure-sql-server)
   - [MongoDB](#mongodb)
9. [PromptFlow](#promptflow)

---

## General Settings

These top-level variables control core application behavior and are not scoped to a specific subsystem prefix.

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATASOURCE_TYPE` | string | _(unset)_ | Selects the datasource for grounded (RAG) chat. Accepted values: `AzureCognitiveSearch`, `AzureCosmosDB`, `Elasticsearch`, `Pinecone`, `AzureMLIndex`, `AzureSqlServer`, `MongoDB`. When unset, the application runs without grounding data. |
| `AUTH_ENABLED` | bool | `True` | Enables Azure Active Directory authentication. When `True`, user identity is extracted from request headers set by Azure App Service Easy Auth. Set to `False` for local development or unauthenticated deployments. |
| `SANITIZE_ANSWER` | bool | `False` | When `True`, post-processes the model response to strip citation markers and other artifacts before returning to the client. |
| `LLM_SOURCE` | string | `azure` | Selects the LLM backend. Accepted values: `azure` (Azure OpenAI direct), `portkey` (Portkey AI gateway). When set to `portkey`, the `PORTKEY_*` variables must also be configured. |
| `USE_PROMPTFLOW` | bool | `False` | Routes chat requests through a PromptFlow endpoint instead of calling Azure OpenAI directly. Requires `PROMPTFLOW_*` variables to be set. |

---

## Azure OpenAI

All variables in this section use the `AZURE_OPENAI_` prefix.

### Connection

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | string | _(unset)_ | Full URL of the Azure OpenAI resource, e.g. `https://my-resource.openai.azure.com`. Required unless `AZURE_OPENAI_RESOURCE` is set. |
| `AZURE_OPENAI_RESOURCE` | string | _(unset)_ | Azure OpenAI resource name (without the domain). Used to construct the endpoint as `https://{resource}.openai.azure.com`. Ignored when `AZURE_OPENAI_ENDPOINT` is set. |
| `AZURE_OPENAI_KEY` | string | _(unset)_ | API key for authenticating to Azure OpenAI. When unset, the application falls back to managed identity authentication. |
| `AZURE_OPENAI_MODEL` | string | **required** | Deployment name of the Azure OpenAI model to use for chat completions, e.g. `gpt-4o`. |
| `AZURE_OPENAI_PREVIEW_API_VERSION` | string | `2024-05-01-preview` | Azure OpenAI API version string. Must be at or above the minimum supported version (`2024-05-01-preview`). |

### Generation Parameters

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_TEMPERATURE` | float | `0` | Sampling temperature for response generation. Range 0.0 to 2.0. Lower values produce more deterministic output. |
| `AZURE_OPENAI_TOP_P` | float | `0` | Nucleus sampling probability mass. Range 0.0 to 1.0. Controls diversity of token selection. |
| `AZURE_OPENAI_MAX_TOKENS` | int | `1000` | Maximum number of tokens to generate in the completion. |
| `AZURE_OPENAI_STREAM` | bool | `True` | When `True`, responses are streamed to the client incrementally using server-sent events. |
| `AZURE_OPENAI_STOP_SEQUENCE` | string | _(unset)_ | Comma-separated list of sequences at which the model will stop generating. Example: `\n,Human:`. |
| `AZURE_OPENAI_SEED` | int | _(unset)_ | Seed for deterministic sampling. When set, the model attempts to return identical results for identical inputs (best-effort). |
| `AZURE_OPENAI_CHOICES_COUNT` | int | `1` | Number of chat completion choices to generate per request. Valid range: 1 to 128. Maps to the API `n` parameter. |
| `AZURE_OPENAI_PRESENCE_PENALTY` | float | `0.0` | Penalizes new tokens based on whether they have appeared in the text so far. Range -2.0 to 2.0. Positive values increase topic diversity. |
| `AZURE_OPENAI_FREQUENCY_PENALTY` | float | `0.0` | Penalizes new tokens based on their frequency in the text so far. Range -2.0 to 2.0. Positive values reduce repetition. |
| `AZURE_OPENAI_USER` | string | _(unset)_ | An identifier representing the end user. Passed through to the API for abuse monitoring. |
| `AZURE_OPENAI_LOGIT_BIAS` | string (JSON) | _(unset)_ | JSON object mapping token IDs to bias values (-100 to 100). Adjusts the likelihood of specific tokens appearing in completions. |

### System Messages

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_SYSTEM_MESSAGE` | string | `You are an AI assistant that helps people find information.` | The user-configurable system prompt sent to the model at the start of each conversation. Users with appropriate permissions can modify this value through the UI. |
| `AZURE_OPENAI_ADMIN_SYSTEM_MESSAGE` | string | _(unset)_ | Admin-only system prompt prepended to the user-configurable system message before sending to the LLM. Invisible to end users. Use for safety rules, compliance requirements, and behavioral constraints that should not be overridden. When unset or empty, has no effect. **Known limitation:** Does not apply in Azure mode with a datasource (server-side RAG) where Azure's API handles system messages internally. |

### Tools and Function Calling

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_TOOLS` | string (JSON) | _(unset)_ | JSON definition of a tool available to the model. Must be a valid `_AzureOpenAITool` object with `type` and `function` fields. |
| `AZURE_OPENAI_TOOL_CHOICE` | string | _(unset)_ | Controls which tool the model may call. Accepted values: `none`, `auto`, or a specific tool name as a JSON object. |
| `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_ENABLED` | bool | `False` | Enables remote Azure Functions integration for function calling. When `True`, tools are fetched from the URL specified by `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_TOOLS_BASE_URL`. |
| `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_TOOLS_BASE_URL` | string | _(unset)_ | Base URL of the Azure Function that returns tool definitions. Used when `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_ENABLED` is `True`. |
| `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_TOOLS_KEY` | string | _(unset)_ | Authentication key appended as a `code` query parameter when fetching tool definitions from the Azure Function. |
| `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_TOOL_BASE_URL` | string | _(unset)_ | Base URL of the Azure Function that executes individual function calls. |
| `AZURE_OPENAI_FUNCTION_CALL_AZURE_FUNCTIONS_TOOL_KEY` | string | _(unset)_ | Authentication key for the function-execution Azure Function endpoint. |

### Embeddings

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_EMBEDDING_NAME` | string | _(unset)_ | Deployment name of the Azure OpenAI embedding model. Used to compute vector embeddings for datasource queries. Takes precedence over `AZURE_OPENAI_EMBEDDING_ENDPOINT`. |
| `AZURE_OPENAI_EMBEDDING_ENDPOINT` | string | _(unset)_ | Full URL of a separate Azure OpenAI embedding endpoint. Used when the embedding model is deployed in a different resource from the chat model. |
| `AZURE_OPENAI_EMBEDDING_KEY` | string | _(unset)_ | API key for the embedding endpoint. When unset with `AZURE_OPENAI_EMBEDDING_ENDPOINT`, managed identity authentication is used. |

### Advanced

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_OPENAI_EXCLUDED_PARAMS` | string | _(unset)_ | Comma-separated list of API parameter names to strip from the request before sending to the LLM. Useful when targeting model deployments that do not support certain parameters (e.g. `frequency_penalty,presence_penalty`). Applied after all other parameters are assembled. |

---

## Portkey

These variables are required when `LLM_SOURCE=portkey`. Portkey acts as an AI gateway, routing requests to the underlying model provider.

| Variable | Type | Default | Description |
|---|---|---|---|
| `PORTKEY_API_KEY` | string | **required** | API key for authenticating to the Portkey gateway. Sent via the `x-portkey-api-key` request header. |
| `PORTKEY_BASE_URI` | string | **required** | Base URL of the Portkey gateway, e.g. `https://api.portkey.ai/v1`. |

---

## User Interface

All variables in this section use the `UI_` prefix and control the frontend appearance.

| Variable | Type | Default | Description |
|---|---|---|---|
| `UI_TITLE` | string | `Contoso` | Browser tab title and application name displayed in the UI header. |
| `UI_LOGO` | string | _(unset)_ | URL or path to the logo image displayed in the application header. When unset, no logo is shown. |
| `UI_CHAT_LOGO` | string | _(unset)_ | URL or path to a logo displayed on the chat welcome screen. When unset, no chat logo is shown. |
| `UI_CHAT_TITLE` | string | `Start chatting` | Heading shown on the chat welcome screen before any conversation has started. |
| `UI_CHAT_DESCRIPTION` | string | `This chatbot is configured to answer your questions` | Descriptive text shown below the chat title on the welcome screen. |
| `UI_FAVICON` | string | `/favicon.ico` | Path or URL to the browser tab favicon. |
| `UI_SHOW_SHARE_BUTTON` | bool | `True` | When `True`, displays a share button in the chat interface allowing users to copy a conversation link. |
| `UI_SHOW_CHAT_HISTORY_BUTTON` | bool | `True` | When `True`, displays the chat history panel toggle button. Has no effect when chat history (CosmosDB) is not configured. |

---

## Chat History (CosmosDB)

These variables configure persistence of conversation history in Azure CosmosDB. All use the `AZURE_COSMOSDB_` prefix. The chat history feature is disabled when these variables are not set.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_COSMOSDB_ACCOUNT` | string | **required** | Name of the Azure CosmosDB account used for conversation storage. |
| `AZURE_COSMOSDB_DATABASE` | string | **required** | Name of the CosmosDB database that contains the conversations container. |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | string | **required** | Name of the CosmosDB container where conversation documents are stored. |
| `AZURE_COSMOSDB_ACCOUNT_KEY` | string | _(unset)_ | CosmosDB account key for authentication. When unset, managed identity authentication is used. |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | bool | `False` | When `True`, exposes a message feedback endpoint and displays thumbs up/down controls in the chat UI for each assistant response. |

---

## Search Common

These variables use the `SEARCH_` prefix and apply shared retrieval parameters that are merged into the datasource-specific payload at request time. They supplement or override the per-datasource defaults.

| Variable | Type | Default | Description |
|---|---|---|---|
| `SEARCH_MAX_SEARCH_QUERIES` | int | _(unset)_ | Maximum number of search queries the model may generate per turn. When unset, the backend default is used. |
| `SEARCH_ALLOW_PARTIAL_RESULT` | bool | `False` | When `True`, the application returns partial results even if some search queries fail. |
| `SEARCH_INCLUDE_CONTEXTS` | string | `citations,intent` | Comma-separated list of context types to include in the response. Accepted values: `citations`, `intent`, `all`. |
| `SEARCH_VECTORIZATION_DIMENSIONS` | int | _(unset)_ | Number of dimensions for vector embeddings. Required by some datasources when using vector or hybrid search. |

---

## Azure AI Search

These variables configure Azure AI Search as the grounding datasource. Set `DATASOURCE_TYPE=AzureCognitiveSearch` to activate this datasource.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_SEARCH_SERVICE` | string | **required** | Name of the Azure AI Search service (without the domain), e.g. `my-search-service`. |
| `AZURE_SEARCH_INDEX` | string | **required** | Name of the search index to query. |
| `AZURE_SEARCH_KEY` | string | _(unset)_ | Admin or query API key for the search service. When unset, managed identity authentication is used. |
| `AZURE_SEARCH_TOP_K` | int | `5` | Number of documents to retrieve from the index per search query. |
| `AZURE_SEARCH_STRICTNESS` | int | `3` | Integer from 1 to 5 controlling how strictly the model limits responses to retrieved content. Higher values reduce the chance of out-of-domain answers. |
| `AZURE_SEARCH_ENABLE_IN_DOMAIN` | bool | `True` | When `True`, the model restricts responses to content found in the index and declines out-of-scope questions. |
| `AZURE_SEARCH_QUERY_TYPE` | string | `simple` | Search query mode. Accepted values: `simple`, `vector`, `semantic`, `vector_simple_hybrid`, `vector_semantic_hybrid`. |
| `AZURE_SEARCH_USE_SEMANTIC_SEARCH` | bool | `False` | Enables semantic ranking on search results. Requires an Azure AI Search semantic configuration. |
| `AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG` | string | `""` | Name of the semantic configuration defined in the Azure AI Search index. Required when `AZURE_SEARCH_USE_SEMANTIC_SEARCH` is `True`. |
| `AZURE_SEARCH_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of index fields that contain the document body text. |
| `AZURE_SEARCH_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of index fields that contain vector embeddings. Required for vector and hybrid query types. |
| `AZURE_SEARCH_TITLE_COLUMN` | string | _(unset)_ | Index field name that contains the document title, shown in citations. |
| `AZURE_SEARCH_URL_COLUMN` | string | _(unset)_ | Index field name that contains a URL for the source document, linked in citations. |
| `AZURE_SEARCH_FILENAME_COLUMN` | string | _(unset)_ | Index field name that contains the source file path, shown in citations. |
| `AZURE_SEARCH_PERMITTED_GROUPS_COLUMN` | string | _(unset)_ | Index field name that contains the AAD group IDs permitted to view each document. When set, enables document-level access control using the authenticated user's token. |
| `AZURE_SEARCH_ENDPOINT_SUFFIX` | string | `search.windows.net` | Domain suffix used to construct the search service endpoint. Override only when using sovereign or private cloud deployments. |

---

## Other Datasources

Each subsection describes variables for an alternative datasource. Only the variables for the datasource selected by `DATASOURCE_TYPE` need to be set.

### CosmosDB Mongo vCore

Set `DATASOURCE_TYPE=AzureCosmosDB` to activate. Requires vector query mode.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING` | string | **required** | MongoDB-compatible connection string for the CosmosDB Mongo vCore cluster. |
| `AZURE_COSMOSDB_MONGO_VCORE_DATABASE` | string | **required** | Name of the database within the Mongo vCore cluster. |
| `AZURE_COSMOSDB_MONGO_VCORE_CONTAINER` | string | **required** | Name of the collection (container) to query. |
| `AZURE_COSMOSDB_MONGO_VCORE_INDEX` | string | **required** | Name of the vector index within the collection. |
| `AZURE_COSMOSDB_MONGO_VCORE_TOP_K` | int | `5` | Number of documents to retrieve per query. |
| `AZURE_COSMOSDB_MONGO_VCORE_STRICTNESS` | int | `3` | Response strictness level, 1 to 5. |
| `AZURE_COSMOSDB_MONGO_VCORE_ENABLE_IN_DOMAIN` | bool | `True` | Restricts responses to content from the datasource. |
| `AZURE_COSMOSDB_MONGO_VCORE_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing document body text. |
| `AZURE_COSMOSDB_MONGO_VCORE_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing vector embeddings. |
| `AZURE_COSMOSDB_MONGO_VCORE_TITLE_COLUMN` | string | _(unset)_ | Field name for the document title shown in citations. |
| `AZURE_COSMOSDB_MONGO_VCORE_URL_COLUMN` | string | _(unset)_ | Field name for the source document URL shown in citations. |
| `AZURE_COSMOSDB_MONGO_VCORE_FILENAME_COLUMN` | string | _(unset)_ | Field name for the source file path shown in citations. |

### Elasticsearch

Set `DATASOURCE_TYPE=Elasticsearch` to activate.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ELASTICSEARCH_ENDPOINT` | string | **required** | Full URL of the Elasticsearch cluster, e.g. `https://my-cluster.es.io:9243`. |
| `ELASTICSEARCH_ENCODED_API_KEY` | string | **required** | Base64-encoded Elasticsearch API key for authentication. |
| `ELASTICSEARCH_INDEX` | string | **required** | Name of the Elasticsearch index to query. |
| `ELASTICSEARCH_QUERY_TYPE` | string | `simple` | Query mode. Accepted values: `simple`, `vector`. |
| `ELASTICSEARCH_TOP_K` | int | `5` | Number of documents to retrieve per query. |
| `ELASTICSEARCH_STRICTNESS` | int | `3` | Response strictness level, 1 to 5. |
| `ELASTICSEARCH_ENABLE_IN_DOMAIN` | bool | `True` | Restricts responses to content from the datasource. |
| `ELASTICSEARCH_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing document body text. |
| `ELASTICSEARCH_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing vector embeddings. Required for vector query type. |
| `ELASTICSEARCH_TITLE_COLUMN` | string | _(unset)_ | Field name for the document title shown in citations. |
| `ELASTICSEARCH_URL_COLUMN` | string | _(unset)_ | Field name for the source document URL shown in citations. |
| `ELASTICSEARCH_FILENAME_COLUMN` | string | _(unset)_ | Field name for the source file path shown in citations. |
| `ELASTICSEARCH_EMBEDDING_MODEL_ID` | string | _(unset)_ | ID of the embedding model hosted within Elasticsearch. When set, takes precedence over `AZURE_OPENAI_EMBEDDING_*` for this datasource. |

### Pinecone

Set `DATASOURCE_TYPE=Pinecone` to activate. Requires vector query mode.

| Variable | Type | Default | Description |
|---|---|---|---|
| `PINECONE_ENVIRONMENT` | string | **required** | Pinecone environment identifier, e.g. `us-east1-gcp`. |
| `PINECONE_API_KEY` | string | **required** | Pinecone API key for authentication. |
| `PINECONE_INDEX_NAME` | string | **required** | Name of the Pinecone index to query. |
| `PINECONE_TOP_K` | int | `5` | Number of documents to retrieve per query. |
| `PINECONE_STRICTNESS` | int | `3` | Response strictness level, 1 to 5. |
| `PINECONE_ENABLE_IN_DOMAIN` | bool | `True` | Restricts responses to content from the datasource. |
| `PINECONE_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing document body text. |
| `PINECONE_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing vector embeddings. |
| `PINECONE_TITLE_COLUMN` | string | _(unset)_ | Field name for the document title shown in citations. |
| `PINECONE_URL_COLUMN` | string | _(unset)_ | Field name for the source document URL shown in citations. |
| `PINECONE_FILENAME_COLUMN` | string | _(unset)_ | Field name for the source file path shown in citations. |

### Azure ML Index

Set `DATASOURCE_TYPE=AzureMLIndex` to activate.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_MLINDEX_NAME` | string | **required** | Name of the Azure Machine Learning index asset. |
| `AZURE_MLINDEX_VERSION` | string | **required** | Version of the Azure Machine Learning index asset. |
| `AZURE_ML_PROJECT_RESOURCE_ID` | string | **required** | Full Azure resource ID of the Azure Machine Learning workspace, e.g. `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices/workspaces/{workspace}`. |
| `AZURE_MLINDEX_TOP_K` | int | `5` | Number of documents to retrieve per query. |
| `AZURE_MLINDEX_STRICTNESS` | int | `3` | Response strictness level, 1 to 5. |
| `AZURE_MLINDEX_ENABLE_IN_DOMAIN` | bool | `True` | Restricts responses to content from the datasource. |
| `AZURE_MLINDEX_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing document body text. |
| `AZURE_MLINDEX_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing vector embeddings. |
| `AZURE_MLINDEX_TITLE_COLUMN` | string | _(unset)_ | Field name for the document title shown in citations. |
| `AZURE_MLINDEX_URL_COLUMN` | string | _(unset)_ | Field name for the source document URL shown in citations. |
| `AZURE_MLINDEX_FILENAME_COLUMN` | string | _(unset)_ | Field name for the source file path shown in citations. |

### Azure SQL Server

Set `DATASOURCE_TYPE=AzureSqlServer` to activate. Authentication uses either a connection string or managed identity (when server, database, and port are all set).

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_SQL_SERVER_CONNECTION_STRING` | string | _(unset)_ | Full ADO.NET connection string for the SQL Server database. When set, takes precedence over the individual server/database/port fields. |
| `AZURE_SQL_SERVER_DATABASE_SERVER` | string | _(unset)_ | Fully qualified SQL Server hostname, e.g. `my-server.database.windows.net`. Required when not using a connection string. |
| `AZURE_SQL_SERVER_DATABASE_NAME` | string | _(unset)_ | Name of the database on the SQL Server. Required when not using a connection string. |
| `AZURE_SQL_SERVER_PORT` | int | _(unset)_ | TCP port of the SQL Server. Required when not using a connection string. Typically `1433`. |
| `AZURE_SQL_SERVER_TABLE_SCHEMA` | string | _(unset)_ | Schema description provided to the model to help it generate SQL queries. |
| `AZURE_SQL_SERVER_SCHEMA_MAX_ROW` | int | _(unset)_ | Maximum number of schema rows included in the prompt context. |
| `AZURE_SQL_SERVER_TOP_N_RESULTS` | int | _(unset)_ | Maximum number of SQL result rows to include in the model context. |

### MongoDB

Set `DATASOURCE_TYPE=MongoDB` to activate. Requires vector query mode and username/password authentication.

| Variable | Type | Default | Description |
|---|---|---|---|
| `MONGODB_ENDPOINT` | string | **required** | Connection endpoint for the MongoDB cluster. |
| `MONGODB_USERNAME` | string | **required** | Username for MongoDB authentication. |
| `MONGODB_PASSWORD` | string | **required** | Password for MongoDB authentication. |
| `MONGODB_DATABASE_NAME` | string | **required** | Name of the MongoDB database. |
| `MONGODB_COLLECTION_NAME` | string | **required** | Name of the MongoDB collection to query. |
| `MONGODB_APP_NAME` | string | **required** | Application name sent to MongoDB for connection identification. |
| `MONGODB_INDEX_NAME` | string | **required** | Name of the vector index within the collection. |
| `MONGODB_TOP_K` | int | `5` | Number of documents to retrieve per query. |
| `MONGODB_STRICTNESS` | int | `3` | Response strictness level, 1 to 5. |
| `MONGODB_ENABLE_IN_DOMAIN` | bool | `True` | Restricts responses to content from the datasource. |
| `MONGODB_CONTENT_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing document body text. |
| `MONGODB_VECTOR_COLUMNS` | string | _(unset)_ | Comma-separated list of fields containing vector embeddings. |
| `MONGODB_TITLE_COLUMN` | string | _(unset)_ | Field name for the document title shown in citations. |
| `MONGODB_URL_COLUMN` | string | _(unset)_ | Field name for the source document URL shown in citations. |
| `MONGODB_FILENAME_COLUMN` | string | _(unset)_ | Field name for the source file path shown in citations. |

---

## PromptFlow

These variables configure integration with an Azure Machine Learning PromptFlow endpoint. Set `USE_PROMPTFLOW=True` to route chat requests through PromptFlow instead of calling Azure OpenAI directly.

| Variable | Type | Default | Description |
|---|---|---|---|
| `USE_PROMPTFLOW` | bool | `False` | Enables PromptFlow routing. When `True`, chat requests are forwarded to the PromptFlow endpoint rather than Azure OpenAI. Listed here for completeness; also documented in [General Settings](#general-settings). |
| `PROMPTFLOW_ENDPOINT` | string | **required** | Full URL of the PromptFlow deployment endpoint. |
| `PROMPTFLOW_API_KEY` | string | **required** | API key for authenticating to the PromptFlow endpoint. |
| `PROMPTFLOW_RESPONSE_TIMEOUT` | float | `30.0` | Seconds to wait for a response from the PromptFlow endpoint before timing out. |
| `PROMPTFLOW_REQUEST_FIELD_NAME` | string | `query` | Field name in the PromptFlow request payload that receives the user's message. |
| `PROMPTFLOW_RESPONSE_FIELD_NAME` | string | `reply` | Field name in the PromptFlow response payload that contains the assistant's reply. |
| `PROMPTFLOW_CITATIONS_FIELD_NAME` | string | `documents` | Field name in the PromptFlow response payload that contains citation documents. |
