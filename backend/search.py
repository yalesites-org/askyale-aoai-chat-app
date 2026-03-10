import json
import logging
from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import Vector
from openai import AsyncAzureOpenAI


async def _get_embedding(query, azure_openai_settings):
    """Get embedding vector for a query using Azure OpenAI.

    Uses API key auth when available (AZURE_OPENAI_EMBEDDING_KEY or
    AZURE_OPENAI_KEY), otherwise falls back to managed identity via
    DefaultAzureCredential.
    """
    endpoint = (
        azure_openai_settings.embedding_endpoint
        or azure_openai_settings.endpoint
    )
    api_key = (
        azure_openai_settings.embedding_key
        or azure_openai_settings.key
    )
    deployment = azure_openai_settings.embedding_name

    ad_token_provider = None
    if not api_key:
        async with DefaultAzureCredential() as credential:
            ad_token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )

    client = AsyncAzureOpenAI(
        api_key=api_key,
        azure_ad_token_provider=ad_token_provider,
        azure_endpoint=endpoint,
        api_version=azure_openai_settings.preview_api_version,
    )
    try:
        response = await client.embeddings.create(
            input=query,
            model=deployment,
        )
        return response.data[0].embedding
    finally:
        await client.close()


async def search_documents(
    query: str,
    search_settings,
    azure_openai_settings,
    search_common_settings=None,
) -> List[dict]:
    """Query Azure Search and return top-k document chunks.

    Supports simple, semantic, vector, and hybrid query types based on
    the configured ``search_settings.query_type``.
    """
    if search_settings.key:
        credential = AzureKeyCredential(search_settings.key)
    else:
        credential = DefaultAzureCredential()

    client = SearchClient(
        endpoint=search_settings.endpoint,
        index_name=search_settings.index,
        credential=credential,
    )

    # Build select fields from configured column names
    select_fields = []
    if search_settings.content_columns:
        select_fields.extend(search_settings.content_columns)
    if search_settings.title_column:
        select_fields.append(search_settings.title_column)
    if search_settings.url_column:
        select_fields.append(search_settings.url_column)
    if search_settings.filename_column:
        select_fields.append(search_settings.filename_column)

    search_kwargs = {
        "search_text": query,
        "top": search_settings.top_k,
    }

    if select_fields:
        search_kwargs["select"] = select_fields

    query_type = search_settings.query_type

    # Semantic search configuration
    if query_type in ("semantic", "vector_semantic_hybrid"):
        search_kwargs["query_type"] = "semantic"
        if search_settings.semantic_search_config:
            search_kwargs["semantic_configuration_name"] = (
                search_settings.semantic_search_config
            )

    # Vector search configuration
    needs_vector = query_type in (
        "vector",
        "vector_simple_hybrid",
        "vector_semantic_hybrid",
    )
    if needs_vector:
        embedding_dep = azure_openai_settings.extract_embedding_dependency()
        if not embedding_dep:
            logging.warning(
                "Vector search requested but no embedding configuration found. "
                "Falling back to text-only search."
            )
        else:
            embedding = await _get_embedding(query, azure_openai_settings)
            vector_fields = (
                search_settings.vector_columns[0]
                if search_settings.vector_columns
                else "contentVector"
            )
            vector = Vector(
                value=embedding,
                k=search_settings.top_k,
                fields=vector_fields,
            )
            search_kwargs["vectors"] = [vector]

    # For pure vector search, don't send search_text
    if query_type == "vector":
        search_kwargs["search_text"] = None

    try:
        results = client.search(**search_kwargs)
    except Exception:
        logging.exception("Error querying Azure Search")
        return []

    documents = []
    content_field = (
        search_settings.content_columns[0]
        if search_settings.content_columns
        else "content"
    )
    title_field = search_settings.title_column or "title"
    url_field = search_settings.url_column or "url"
    filename_field = search_settings.filename_column or "filepath"

    for i, result in enumerate(results):
        doc = {
            "id": f"doc{i + 1}",
            "content": result.get(content_field, ""),
            "title": result.get(title_field, ""),
            "url": result.get(url_field, ""),
            "filepath": result.get(filename_field, ""),
            "chunk_id": result.get("chunk_id", str(i)),
        }
        documents.append(doc)

    return documents


def build_rag_system_prompt(
    base_system_message: str,
    documents: List[dict],
) -> str:
    """Build a system prompt with retrieved document context and citation instructions."""
    if not documents:
        return base_system_message

    sources_text = ""
    for doc in documents:
        title = doc.get("title", "")
        content = doc.get("content", "")
        header = f"[{doc['id']}]"
        if title:
            header += f" {title}"
        sources_text += f"{header}:\n{content}\n\n"

    return (
        f"{base_system_message}\n\n"
        "## Retrieved Sources\n"
        "Use the following sources to answer the user's question. "
        "Cite sources using their reference IDs (e.g., [doc1], [doc2]) "
        "when you use information from them. If the sources don't contain "
        "relevant information, say so.\n\n"
        f"{sources_text}"
    )


def build_citations(documents: List[dict]) -> List[dict]:
    """Convert search results to the citation format expected by the frontend.

    Returns a list matching the frontend Citation type:
    ``{content, id, title, filepath, url, metadata, chunk_id, reindex_id}``
    """
    citations = []
    for doc in documents:
        citations.append({
            "content": doc.get("content", ""),
            "id": doc.get("id", ""),
            "title": doc.get("title", ""),
            "filepath": doc.get("filepath", ""),
            "url": doc.get("url", ""),
            "metadata": doc.get("metadata", ""),
            "chunk_id": doc.get("chunk_id", ""),
            "reindex_id": doc.get("reindex_id", ""),
        })
    return citations
