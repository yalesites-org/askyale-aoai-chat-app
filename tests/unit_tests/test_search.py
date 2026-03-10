import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.search import (
    build_citations,
    build_rag_system_prompt,
    search_documents,
)


# --- build_rag_system_prompt tests ---

def test_build_rag_system_prompt_no_documents():
    base = "You are a helpful assistant."
    result = build_rag_system_prompt(base, [])
    assert result == base


def test_build_rag_system_prompt_single_document():
    base = "You are a helpful assistant."
    docs = [{"id": "doc1", "title": "My Title", "content": "Some content"}]
    result = build_rag_system_prompt(base, docs)
    assert base in result
    assert "[doc1] My Title:" in result
    assert "Some content" in result
    assert "Cite sources" in result


def test_build_rag_system_prompt_multiple_documents():
    base = "System message."
    docs = [
        {"id": "doc1", "title": "Title A", "content": "Content A"},
        {"id": "doc2", "title": "Title B", "content": "Content B"},
        {"id": "doc3", "title": "", "content": "Content C"},
    ]
    result = build_rag_system_prompt(base, docs)
    assert "[doc1] Title A:" in result
    assert "[doc2] Title B:" in result
    assert "[doc3]:" in result
    assert "Content A" in result
    assert "Content B" in result
    assert "Content C" in result


# --- build_citations tests ---

def test_build_citations_empty():
    assert build_citations([]) == []


def test_build_citations_output_format():
    docs = [
        {
            "id": "doc1",
            "content": "Some text",
            "title": "Title",
            "filepath": "/path/file.pdf",
            "url": "https://example.com",
            "chunk_id": "0",
        }
    ]
    citations = build_citations(docs)
    assert len(citations) == 1
    c = citations[0]
    assert c["content"] == "Some text"
    assert c["id"] == "doc1"
    assert c["title"] == "Title"
    assert c["filepath"] == "/path/file.pdf"
    assert c["url"] == "https://example.com"
    assert c["chunk_id"] == "0"
    # Fields that may be missing from source should default to empty string
    assert c["metadata"] == ""
    assert c["reindex_id"] == ""


def test_build_citations_multiple():
    docs = [
        {"id": "doc1", "content": "A", "title": "T1", "filepath": "", "url": "", "chunk_id": "0"},
        {"id": "doc2", "content": "B", "title": "T2", "filepath": "", "url": "", "chunk_id": "1"},
    ]
    citations = build_citations(docs)
    assert len(citations) == 2
    assert citations[0]["id"] == "doc1"
    assert citations[1]["id"] == "doc2"


# --- search_documents tests ---

@pytest.fixture
def mock_search_settings():
    settings = MagicMock()
    settings.key = "test-key"
    settings.endpoint = "https://search.example.com"
    settings.index = "test-index"
    settings.top_k = 3
    settings.query_type = "simple"
    settings.content_columns = ["content"]
    settings.title_column = "title"
    settings.url_column = "url"
    settings.filename_column = "filepath"
    settings.vector_columns = None
    settings.semantic_search_config = ""
    return settings


@pytest.fixture
def mock_azure_openai_settings():
    settings = MagicMock()
    settings.endpoint = "https://openai.example.com"
    settings.key = "openai-key"
    settings.preview_api_version = "2024-05-01-preview"
    settings.embedding_name = "text-embedding-ada-002"
    settings.embedding_endpoint = None
    settings.embedding_key = None
    settings.extract_embedding_dependency.return_value = {
        "type": "deployment_name",
        "deployment_name": "text-embedding-ada-002",
    }
    return settings


@pytest.mark.asyncio
async def test_search_documents_simple(mock_search_settings, mock_azure_openai_settings):
    mock_results = [
        {"content": "Result 1", "title": "Title 1", "url": "url1", "filepath": "f1", "chunk_id": "0"},
        {"content": "Result 2", "title": "Title 2", "url": "url2", "filepath": "f2", "chunk_id": "1"},
    ]

    with patch("backend.search.SearchClient") as MockClient:
        mock_client = MagicMock()
        mock_client.search.return_value = iter(mock_results)
        MockClient.return_value = mock_client

        docs = await search_documents(
            "test query",
            mock_search_settings,
            mock_azure_openai_settings,
        )

    assert len(docs) == 2
    assert docs[0]["id"] == "doc1"
    assert docs[0]["content"] == "Result 1"
    assert docs[1]["id"] == "doc2"

    # Verify search was called with text search, not vector
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["search_text"] == "test query"
    assert "vectors" not in call_kwargs


@pytest.mark.asyncio
async def test_search_documents_semantic(mock_search_settings, mock_azure_openai_settings):
    mock_search_settings.query_type = "semantic"
    mock_search_settings.semantic_search_config = "my-semantic-config"

    with patch("backend.search.SearchClient") as MockClient:
        mock_client = MagicMock()
        mock_client.search.return_value = iter([])
        MockClient.return_value = mock_client

        await search_documents(
            "test query",
            mock_search_settings,
            mock_azure_openai_settings,
        )

    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["query_type"] == "semantic"
    assert call_kwargs["semantic_configuration_name"] == "my-semantic-config"


@pytest.mark.asyncio
async def test_search_documents_vector(mock_search_settings, mock_azure_openai_settings):
    mock_search_settings.query_type = "vector"
    mock_search_settings.vector_columns = ["contentVector"]

    mock_embedding = [0.1] * 1536

    with patch("backend.search.SearchClient") as MockClient, \
         patch("backend.search._get_embedding", new_callable=AsyncMock, return_value=mock_embedding):
        mock_client = MagicMock()
        mock_client.search.return_value = iter([])
        MockClient.return_value = mock_client

        await search_documents(
            "test query",
            mock_search_settings,
            mock_azure_openai_settings,
        )

    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["search_text"] is None  # Pure vector, no text
    assert "vectors" in call_kwargs


@pytest.mark.asyncio
async def test_search_documents_error_returns_empty(mock_search_settings, mock_azure_openai_settings):
    with patch("backend.search.SearchClient") as MockClient:
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Search failed")
        MockClient.return_value = mock_client

        docs = await search_documents(
            "test query",
            mock_search_settings,
            mock_azure_openai_settings,
        )

    assert docs == []
