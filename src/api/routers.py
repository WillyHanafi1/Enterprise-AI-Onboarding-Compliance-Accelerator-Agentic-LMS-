"""
API Route Definitions.

All endpoint logic is defined here and mounted onto the FastAPI app
via `app.include_router(router)` in server.py.

Current endpoints:
    - POST /api/v1/documents/ingest  (Phase 2)

Future endpoints (Phase 5):
    - POST /api/v1/sessions
    - POST /api/v1/sessions/{id}/chat
    - GET  /api/v1/sessions/{id}/status
    - POST /api/v1/sessions/{id}/approve
    - POST /api/v1/sessions/{id}/reject
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from src.core.config import get_settings
from src.ingestion.pipeline import ingest_document
from src.schemas.responses import IngestionResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix=settings.API_PREFIX, tags=["Documents"])

# === Allowed file types ===
ALLOWED_EXTENSIONS = {".pdf", ".md"}
MAX_FILE_SIZE_MB = 50


@router.post(
    "/documents/ingest",
    response_model=IngestionResponse,
    summary="Ingest an SOP document",
    description=(
        "Upload a PDF or Markdown document to be processed through the RAG pipeline. "
        "The document is extracted, chunked, embedded, and stored in the vector database "
        "for later retrieval by the Explainer and Planner agents."
    ),
)
async def ingest_document_endpoint(file: UploadFile) -> IngestionResponse:
    """
    Processes an uploaded document through the full ingestion pipeline.

    1. Validates file type and size
    2. Saves to temporary location
    3. Runs ingestion pipeline (load → chunk → embed → store)
    4. Returns ingestion summary
    """
    # --- Validate file extension ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # --- Validate file size ---
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum allowed: {MAX_FILE_SIZE_MB}MB.",
        )

    # --- Save to temporary file and process ---
    tmp_path = None  # BUG-11 FIX: Initialize before try to prevent UnboundLocalError
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            prefix="sop_",
        ) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        logger.info(
            "Received file '%s' (%.2f MB), saved to temp: %s",
            file.filename,
            file_size_mb,
            tmp_path,
        )

        # Run the ingestion pipeline
        result = ingest_document(tmp_path)

        return IngestionResponse(
            filename=file.filename,  # Use original filename, not temp name
            pages_loaded=result["pages_loaded"],
            chunks_created=result["chunks_created"],
            chunks_stored=result["chunks_stored"],
        )

    except Exception as e:
        logger.exception("Ingestion failed for file '%s'", file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {e!s}",
        ) from e

    finally:
        # Clean up temp file (BUG-11 FIX: check for None)
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
            logger.debug("Cleaned up temp file: %s", tmp_path)
