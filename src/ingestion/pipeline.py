"""
Document Ingestion Pipeline.

Implements the full RAG ingestion flow as defined in ARCHITECTURE.md §6.1:
    PDF/Markdown Upload
        → Text Extraction (pypdf / Unstructured)
        → Chunking (RecursiveCharacterTextSplitter, chunk_size=1000, overlap=200)
        → Embedding (text-embedding-004 via Gemini API)
        → Store in ChromaDB with metadata (filename, page_number, section_header)
"""

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import get_settings
from src.core.database import CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

# === Constants ===
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
COLLECTION_NAME = "internal_policies"
EMBEDDING_MODEL = "models/gemini-embedding-001"


# ============================================================
# 1. Document Loading
# ============================================================


def load_pdf(file_path: Path) -> list[Document]:
    """
    Loads a PDF file and extracts text page-by-page.

    Each page becomes a separate Document with metadata containing:
    - source: the filename
    - page: the 1-indexed page number

    Args:
        file_path: Path to the PDF file.

    Returns:
        A list of LangChain Documents, one per page.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a PDF.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {file_path.suffix}")

    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    documents: list[Document] = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            documents.append(
                Document(
                    page_content=text.strip(),
                    metadata={
                        "source": file_path.name,
                        "page": i + 1,
                        "total_pages": len(reader.pages),
                        "file_type": "pdf",
                    },
                )
            )

    logger.info("Loaded %d pages from %s", len(documents), file_path.name)
    return documents


def load_markdown(file_path: Path) -> list[Document]:
    """
    Loads a Markdown file as a single Document.

    Metadata includes:
    - source: the filename
    - file_type: "markdown"

    Args:
        file_path: Path to the Markdown file.

    Returns:
        A list containing a single LangChain Document.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")

    if not text.strip():
        logger.warning("Markdown file is empty: %s", file_path.name)
        return []

    documents = [
        Document(
            page_content=text.strip(),
            metadata={
                "source": file_path.name,
                "page": 1,
                "file_type": "markdown",
            },
        )
    ]

    logger.info("Loaded markdown file: %s (%d chars)", file_path.name, len(text))
    return documents


def load_document(file_path: Path) -> list[Document]:
    """
    Dispatches to the appropriate loader based on file extension.

    Supported formats: .pdf, .md

    Args:
        file_path: Path to the document.

    Returns:
        A list of LangChain Documents.

    Raises:
        ValueError: If the file format is not supported.
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(file_path)
    elif suffix == ".md":
        return load_markdown(file_path)
    else:
        raise ValueError(f"Unsupported file format: '{suffix}'. Supported: .pdf, .md")


# ============================================================
# 2. Text Chunking
# ============================================================


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Splits documents into smaller chunks for embedding.

    Uses RecursiveCharacterTextSplitter which respects paragraph
    and sentence boundaries for cleaner chunk boundaries.

    Chunk config (from ARCHITECTURE.md §6.1):
    - chunk_size: 1000 characters
    - chunk_overlap: 200 characters

    Each chunk inherits the parent document's metadata plus
    a 'chunk_index' field for traceability.

    Args:
        documents: List of Documents to split.

    Returns:
        A list of chunked Documents with preserved metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )

    chunks = splitter.split_documents(documents)

    # Add chunk_index to metadata for traceability
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    logger.info(
        "Split %d documents into %d chunks (size=%d, overlap=%d)",
        len(documents),
        len(chunks),
        CHUNK_SIZE,
        CHUNK_OVERLAP,
    )
    return chunks


# ============================================================
# 3. Embedding & Storage
# ============================================================


def get_embedding_function() -> GoogleGenerativeAIEmbeddings:
    """
    Returns the Gemini embedding function for vectorizing text.

    Uses Google's text-embedding-004 model for high-quality
    semantic embeddings that integrate with the Gemini ecosystem.

    Returns:
        A GoogleGenerativeAIEmbeddings instance.
    """
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
    )


def get_vector_store() -> Chroma:
    """
    Returns a persistent Chroma vector store instance.

    The store uses Google's text-embedding-004 for embeddings
    and persists data to disk at CHROMA_PERSIST_DIR.

    Returns:
        A LangChain Chroma vector store instance.
    """
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        persist_directory=str(CHROMA_PERSIST_DIR),
    )


def store_chunks(chunks: list[Document]) -> int:
    """
    Embeds and stores document chunks into ChromaDB.

    Args:
        chunks: List of chunked Documents to store.

    Returns:
        The number of chunks stored.
    """
    if not chunks:
        logger.warning("No chunks to store.")
        return 0

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    logger.info("Stored %d chunks in ChromaDB collection '%s'", len(chunks), COLLECTION_NAME)
    return len(chunks)


# ============================================================
# 4. Full Ingestion Pipeline (Orchestrator)
# ============================================================


def ingest_document(file_path: Path) -> dict:
    """
    Runs the complete ingestion pipeline for a single document.

    Pipeline stages:
        1. Load → extract raw text from PDF/Markdown
        2. Chunk → split into overlapping segments
        3. Embed & Store → vectorize and persist to ChromaDB

    Args:
        file_path: Path to the document to ingest.

    Returns:
        A summary dict with keys:
        - filename: name of the ingested file
        - pages_loaded: number of raw pages/sections extracted
        - chunks_created: number of chunks after splitting
        - chunks_stored: number of chunks persisted to vector store

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is unsupported.
    """
    logger.info("=== Starting ingestion: %s ===", file_path.name)

    # Stage 1: Load
    documents = load_document(file_path)
    logger.info("Stage 1/3 complete: loaded %d pages", len(documents))

    # Stage 2: Chunk
    chunks = chunk_documents(documents)
    logger.info("Stage 2/3 complete: created %d chunks", len(chunks))

    # Stage 3: Embed & Store
    stored_count = store_chunks(chunks)
    logger.info("Stage 3/3 complete: stored %d chunks", stored_count)

    summary = {
        "filename": file_path.name,
        "pages_loaded": len(documents),
        "chunks_created": len(chunks),
        "chunks_stored": stored_count,
    }
    logger.info("=== Ingestion complete: %s ===", summary)
    return summary
