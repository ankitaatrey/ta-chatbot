"""
Generic document ingestion pipeline supporting multiple file types.

This module uses the document_loaders system to ingest various file types
(PDFs, SRT transcripts, text files, etc.) into the vector database.

The pipeline:
1. Recursively finds all supported files in the data directory
2. Uses appropriate loader for each file type
3. Chunks the text using token-aware chunking
4. Stores chunks with metadata in the vector database

To add support for new file types, just add a loader to document_loaders.py!
"""

import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from tqdm import tqdm

from src.config import config
from src.splitter import TokenAwareChunker, PDFChunk, chunk_pdf
from src.vectordb import get_vectordb
from src.utils.logging_setup import setup_logging, get_logger
from src.document_loaders import (
    get_loader_for_file,
    get_supported_extensions,
    is_supported_file,
    extract_course_id_from_path
)

logger = get_logger(__name__)


def find_documents(directory: Path) -> List[Path]:
    """
    Recursively find all supported document files in a directory.
    
    Uses the loader registry to determine which files are supported.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of file paths that have registered loaders
    """
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return []
    
    supported_extensions = get_supported_extensions()
    logger.info(f"Scanning for files with extensions: {', '.join(supported_extensions)}")
    
    # Find all files with supported extensions
    files = []
    for extension in supported_extensions:
        # Use glob to find all files with this extension (recursive)
        pattern = f"**/*{extension}"
        found = list(directory.glob(pattern))
        files.extend(found)
    
    logger.info(f"Found {len(files)} supported documents in {directory}")
    
    # Log breakdown by file type
    by_type = {}
    for file in files:
        ext = file.suffix.lower()
        by_type[ext] = by_type.get(ext, 0) + 1
    
    for ext, count in sorted(by_type.items()):
        logger.info(f"  {ext}: {count} files")
    
    return files


def ingest_document(
    file_path: Path,
    vectordb,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    force_reindex: bool = False,
    data_root: Optional[Path] = None
) -> int:
    """
    Ingest a single document file into the vector database.
    
    This function:
    1. Finds the appropriate loader for the file type
    2. Loads and parses the document
    3. Chunks the text (using page-aware chunking for PDFs)
    4. Adds chunks with metadata to vector database
    
    Args:
        file_path: Path to document file
        vectordb: VectorDB instance
        chunk_size: Optional chunk size override
        chunk_overlap: Optional chunk overlap override
        force_reindex: Whether to force re-indexing
        data_root: Root data directory (for deriving course_id)
        
    Returns:
        Number of chunks added
    """
    logger.info(f"Processing: {file_path.name}")
    
    # Check if already indexed (unless force_reindex)
    if not force_reindex:
        existing = vectordb.collection.get(
            where={"source_path": str(file_path)},
            limit=1
        )
        if existing and existing.get("ids"):
            logger.info(f"Already indexed: {file_path.name} (use --force to re-index)")
            return 0
    else:
        # Delete existing chunks for this source
        vectordb.delete_by_source(str(file_path))
    
    # Special handling for PDFs to preserve page numbers
    if file_path.suffix.lower() == ".pdf":
        try:
            # Use the page-aware chunk_pdf function
            chunks = chunk_pdf(
                file_path,
                chunk_size=chunk_size or config.chunk_size,
                chunk_overlap=chunk_overlap or config.chunk_overlap
            )
            
            if not chunks:
                logger.warning(f"No chunks created from {file_path.name}")
                return 0
            
            # Prepare data for insertion
            texts = [chunk.text for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = chunk.to_dict()["metadata"]
                # Add file_type for PDFs
                metadata["file_type"] = "pdf"
                # Add course_id if derivable
                if data_root:
                    course_id = extract_course_id_from_path(file_path, data_root)
                    if course_id:
                        metadata["course_id"] = course_id
                metadatas.append(metadata)
            
            ids = [chunk.chunk_id for chunk in chunks]
            
            # Add to vector database
            vectordb.upsert_documents(texts, metadatas, ids)
            
            logger.info(f"Added {len(chunks)} chunks from {file_path.name} (PDF)")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to process PDF {file_path.name}: {e}")
            return 0
    
    # Generic handling for non-PDF files (SRT, TXT, MD, etc.)
    loader = get_loader_for_file(file_path)
    if not loader:
        logger.warning(f"No loader found for file type: {file_path.suffix}")
        return 0
    
    # Load document using appropriate loader
    try:
        doc = loader.load(file_path)
        text = doc["text"]
        base_metadata = doc["metadata"]
    except Exception as e:
        logger.error(f"Failed to load {file_path.name}: {e}")
        return 0
    
    if not text or not text.strip():
        logger.warning(f"No text extracted from {file_path.name}")
        return 0
    
    # Add course_id if we can derive it from path
    if data_root:
        course_id = extract_course_id_from_path(file_path, data_root)
        if course_id:
            base_metadata["course_id"] = course_id
    
    # Store the full source path for deduplication
    base_metadata["source_path"] = str(file_path)
    
    # Initialize chunker
    chunker = TokenAwareChunker(
        chunk_size=chunk_size or config.chunk_size,
        chunk_overlap=chunk_overlap or config.chunk_overlap
    )
    
    # Split text into chunks
    text_chunks = chunker.split_text(text)
    
    if not text_chunks:
        logger.warning(f"No chunks created from {file_path.name}")
        return 0
    
    # Create chunk objects with metadata
    chunks = []
    file_type = base_metadata.get("file_type", "unknown")
    
    for i, chunk_text in enumerate(text_chunks):
        # Create a unique chunk ID
        chunk_id = f"{file_path.stem}_{file_type}_c{i}"
        
        # Create chunk with base metadata
        chunk = PDFChunk(
            text=chunk_text.strip(),
            page_start=0,  # Non-PDF files don't have pages
            page_end=0,
            source_path=str(file_path),
            title=base_metadata.get("title", file_path.stem),
            chunk_id=chunk_id,
        )
        chunks.append(chunk)
    
    # Prepare data for insertion
    texts = [chunk.text for chunk in chunks]
    metadatas = []
    
    for chunk in chunks:
        # Get base metadata from chunk
        metadata = chunk.to_dict()["metadata"]
        
        # Merge in document-level metadata
        # This adds file_type, course_id, and any other loader-specific metadata
        for key, value in base_metadata.items():
            if key not in metadata or metadata[key] is None:
                metadata[key] = value
        
        metadatas.append(metadata)
    
    ids = [chunk.chunk_id for chunk in chunks]
    
    # Add to vector database
    vectordb.upsert_documents(texts, metadatas, ids)
    
    file_type_display = base_metadata.get("file_type", "unknown").upper()
    logger.info(f"Added {len(chunks)} chunks from {file_path.name} ({file_type_display})")
    return len(chunks)


def ingest_directory(
    data_dir: Path,
    force_reindex: bool = False,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> None:
    """
    Ingest all supported documents from a directory.
    
    Recursively scans the directory for files with registered loaders
    and ingests them into the vector database.
    
    Args:
        data_dir: Directory containing documents
        force_reindex: Whether to force re-indexing
        chunk_size: Optional chunk size override
        chunk_overlap: Optional chunk overlap override
    """
    logger.info(f"Starting ingestion from: {data_dir}")
    logger.info(f"Supported file types: {', '.join(get_supported_extensions())}")
    
    # Find all supported documents
    files = find_documents(data_dir)
    
    if not files:
        logger.warning("No supported files found")
        logger.info(f"Looking for files with extensions: {', '.join(get_supported_extensions())}")
        return
    
    # Initialize vector database
    vectordb = get_vectordb()
    
    # Process statistics
    total_chunks = 0
    success_count = 0
    
    # Track stats by file type
    stats_by_type = {}
    
    # Process each file
    for file_path in tqdm(files, desc="Ingesting documents"):
        try:
            chunks_added = ingest_document(
                file_path,
                vectordb,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                force_reindex=force_reindex,
                data_root=data_dir
            )
            
            total_chunks += chunks_added
            if chunks_added > 0:
                success_count += 1
                
                # Track by file type
                file_type = file_path.suffix.lower()
                if file_type not in stats_by_type:
                    stats_by_type[file_type] = {"count": 0, "chunks": 0}
                stats_by_type[file_type]["count"] += 1
                stats_by_type[file_type]["chunks"] += chunks_added
        
        except Exception as e:
            logger.error(f"Failed to ingest {file_path.name}: {e}")
    
    # Print summary
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files processed: {success_count}/{len(files)}")
    logger.info(f"Total chunks added: {total_chunks}")
    logger.info("")
    logger.info("By file type:")
    for file_type, stats in sorted(stats_by_type.items()):
        logger.info(f"  {file_type}: {stats['count']} files, {stats['chunks']} chunks")
    logger.info("")
    
    # Get database stats
    stats = vectordb.get_stats()
    logger.info(f"Database total chunks: {stats['total_chunks']}")
    logger.info(f"Database unique documents: {stats['unique_documents']}")
    logger.info("=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into the vector database (supports PDF, SRT, TXT, MD, and more)"
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default="data",
        help="Directory containing document files (default: data)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing of already processed files"
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=None,
        help="Chunk size in tokens (default: from config)"
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=None,
        help="Chunk overlap in tokens (default: from config)"
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Convert data_dir to Path
    data_dir = Path(args.data_dir)
    
    # Run ingestion
    try:
        ingest_directory(
            data_dir=data_dir,
            force_reindex=args.force,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        logger.info("Ingestion completed successfully")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
