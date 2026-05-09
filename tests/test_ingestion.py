"""
Integration tests for the RAG ingestion pipeline.

Tests cover:
    - Document loading (PDF + Markdown)
    - Text chunking with metadata preservation
    - Full ingestion pipeline orchestration
"""

from pathlib import Path

import pytest

from src.ingestion.pipeline import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_documents,
    load_document,
    load_markdown,
)

# === Fixtures ===

SAMPLE_SOP_PATH = Path("data/sample_security_policy.md")


@pytest.fixture
def sample_sop_path() -> Path:
    """Returns the path to the sample SOP markdown file."""
    if not SAMPLE_SOP_PATH.exists():
        pytest.skip("Sample SOP not found at data/sample_security_policy.md")
    return SAMPLE_SOP_PATH


# ============================================================
# Test: Document Loading
# ============================================================


class TestDocumentLoading:
    """Tests for document loading functions."""

    def test_load_markdown_returns_documents(self, sample_sop_path: Path) -> None:
        """Markdown loader should return a non-empty list of Documents."""
        docs = load_markdown(sample_sop_path)
        assert len(docs) > 0
        assert docs[0].page_content  # Content is not empty

    def test_load_markdown_has_metadata(self, sample_sop_path: Path) -> None:
        """Each loaded document should have source metadata."""
        docs = load_markdown(sample_sop_path)
        metadata = docs[0].metadata

        assert metadata["source"] == sample_sop_path.name
        assert metadata["file_type"] == "markdown"
        assert metadata["page"] == 1

    def test_load_document_dispatches_markdown(self, sample_sop_path: Path) -> None:
        """load_document() should route .md files to the markdown loader."""
        docs = load_document(sample_sop_path)
        assert len(docs) > 0
        assert docs[0].metadata["file_type"] == "markdown"

    def test_load_document_rejects_unsupported_format(self, tmp_path: Path) -> None:
        """load_document() should raise ValueError for unsupported file types."""
        bad_file = tmp_path / "test.docx"
        bad_file.write_text("some content")

        with pytest.raises(ValueError, match="Unsupported file format"):
            load_document(bad_file)

    def test_load_document_raises_on_missing_file(self) -> None:
        """load_document() should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_document(Path("nonexistent_file.pdf"))


# ============================================================
# Test: Text Chunking
# ============================================================


class TestChunking:
    """Tests for the text chunking stage."""

    def test_chunking_splits_large_document(self, sample_sop_path: Path) -> None:
        """A multi-section SOP should be split into multiple chunks."""
        docs = load_markdown(sample_sop_path)
        chunks = chunk_documents(docs)

        # The sample SOP is ~5000+ chars, so should produce multiple chunks
        assert len(chunks) > 1

    def test_chunks_respect_size_limit(self, sample_sop_path: Path) -> None:
        """No chunk should exceed chunk_size + a reasonable margin."""
        docs = load_markdown(sample_sop_path)
        chunks = chunk_documents(docs)

        # Allow some margin because the splitter tries to find a clean boundary
        max_allowed = CHUNK_SIZE + CHUNK_OVERLAP
        for chunk in chunks:
            assert len(chunk.page_content) <= max_allowed, (
                f"Chunk too large: {len(chunk.page_content)} chars (max {max_allowed})"
            )

    def test_chunks_preserve_metadata(self, sample_sop_path: Path) -> None:
        """Chunks should inherit the parent document's metadata."""
        docs = load_markdown(sample_sop_path)
        chunks = chunk_documents(docs)

        for chunk in chunks:
            assert "source" in chunk.metadata
            assert "chunk_index" in chunk.metadata
            assert chunk.metadata["source"] == sample_sop_path.name

    def test_chunk_index_is_sequential(self, sample_sop_path: Path) -> None:
        """chunk_index should be 0-indexed and sequential."""
        docs = load_markdown(sample_sop_path)
        chunks = chunk_documents(docs)

        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_input_returns_empty(self) -> None:
        """Chunking an empty list should return an empty list."""
        assert chunk_documents([]) == []
