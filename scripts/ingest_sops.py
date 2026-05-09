import asyncio
import logging
from pathlib import Path

from src.ingestion.pipeline import ingest_document
from src.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Cannot ingest.")
        return

    sops_dir = Path("data/sops")
    if not sops_dir.exists():
        logger.error(f"Directory not found: {sops_dir}")
        return

    md_files = list(sops_dir.glob("*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in {sops_dir}")
        return

    logger.info(f"Found {len(md_files)} SOP files to ingest.")
    
    total_chunks = 0
    for file_path in md_files:
        summary = ingest_document(file_path)
        total_chunks += summary.get("chunks_stored", 0)
        
    logger.info(f"Successfully ingested {len(md_files)} files into {total_chunks} chunks.")

if __name__ == "__main__":
    main()
