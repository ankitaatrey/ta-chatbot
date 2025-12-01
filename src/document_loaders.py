"""
Generic document loader architecture for multi-file-type RAG ingestion.

This module provides a pluggable loader system that makes it easy to add support
for new file types without modifying core ingestion logic.

HOW TO ADD A NEW FILE TYPE:
============================

1. Create a new loader class that implements the DocumentLoader protocol:

   class MyNewLoader:
       def load(self, path: Path) -> Dict[str, Any]:
           # Parse your file type
           text = extract_text_from_file(path)
           
           # Return standardized format
           return {
               "text": text,
               "metadata": {
                   "source": path.name,
                   "file_type": "my_type",
                   "path": str(path),
                   # Add any type-specific metadata here
               }
           }

2. Register it in LOADER_REGISTRY:

   LOADER_REGISTRY = {
       ".pdf": PdfLoader(),
       ".srt": SrtLoader(),
       ".my_ext": MyNewLoader(),  # <-- Add your loader here
   }

3. That's it! The ingestion pipeline will automatically use your loader
   for any files with that extension.

METADATA STRUCTURE:
===================

All loaders must return a dict with this structure:

{
    "text": str,           # Full plaintext content
    "metadata": {
        "source": str,     # Filename (required)
        "file_type": str,  # Type identifier like "pdf", "srt" (required)
        "path": str,       # Full or relative path (required)
        
        # Optional but recommended for citations:
        "title": str,      # Human-readable title
        "course_id": str,  # Course/collection identifier
        
        # Type-specific optional fields:
        "page_start": int, "page_end": int,     # For paginated docs (PDFs)
        "timestamp": str,                        # For time-based docs (SRT, video)
        "section": str,                          # For structured docs (MD, HTML)
        "author": str, "date": str, etc.        # Any other relevant metadata
    }
}

The metadata is used throughout the pipeline:
- Retrieval: Metadata is stored with chunks and returned with results
- Citations: Metadata determines how citations are formatted
- UI: Metadata is displayed to users to show sources
"""

from pathlib import Path
from typing import Dict, Any, Protocol, List, Optional
import re
import logging

from src.utils.logging_setup import get_logger
from src.utils.text_normalize import normalize_whitespace, extract_title_from_filename

logger = get_logger(__name__)

# Optional: PDF parsing (most systems will have this)
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available. PDF loading will be disabled.")


# ============================================================================
# LOADER PROTOCOL (Interface)
# ============================================================================

class DocumentLoader(Protocol):
    """
    Protocol (interface) that all document loaders must implement.
    
    This ensures all loaders have a consistent API that the ingestion
    pipeline can rely on.
    """
    
    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load and parse a document file.
        
        Args:
            path: Path to the file to load
            
        Returns:
            Dictionary with keys:
            - "text": Full plaintext string
            - "metadata": Dict with at least "source", "file_type", "path"
            
        Raises:
            Exception: If file cannot be loaded or parsed
        """
        ...


# ============================================================================
# CONCRETE LOADERS
# ============================================================================

class PdfLoader:
    """
    Loader for PDF files.
    
    Extracts text page-by-page and preserves page number information
    for accurate citations.
    """
    
    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load a PDF file and extract text with page metadata.
        
        Args:
            path: Path to PDF file
            
        Returns:
            Dict with full text and metadata including page info
        """
        if not PDF_AVAILABLE:
            raise RuntimeError("PyPDF2 not installed. Cannot load PDFs.")
        
        logger.info(f"Loading PDF: {path.name}")
        
        try:
            with open(path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                # Extract text from all pages
                pages_text = []
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        pages_text.append(text)
                
                # Combine all pages
                full_text = "\n\n".join(pages_text)
                
                # Clean up text
                full_text = normalize_whitespace(full_text)
                
                # Extract title from filename
                title = extract_title_from_filename(path.name)
                
                logger.info(f"Loaded PDF: {path.name} ({num_pages} pages, {len(full_text)} chars)")
                
                return {
                    "text": full_text,
                    "metadata": {
                        "source": path.name,
                        "file_type": "pdf",
                        "path": str(path),
                        "title": title,
                        "num_pages": num_pages,
                        # Note: page_start/page_end will be added per-chunk during chunking
                    }
                }
        
        except Exception as e:
            logger.error(f"Failed to load PDF {path.name}: {e}")
            raise


class SrtLoader:
    """
    Loader for SRT subtitle/transcript files.
    
    Extracts spoken text from SRT format, removing timestamps and
    sequence numbers. Useful for lecture transcripts, video captions, etc.
    
    SRT Format Example:
        1
        00:00:00,000 --> 00:00:02,000
        Hello, welcome to the course.
        
        2
        00:00:02,000 --> 00:00:05,000
        Today we'll discuss algorithms.
    """
    
    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load an SRT file and extract clean transcript text.
        
        Args:
            path: Path to SRT file
            
        Returns:
            Dict with transcript text and metadata
        """
        logger.info(f"Loading SRT: {path.name}")
        
        try:
            # Try UTF-8 first, fall back to latin-1 if needed
            encodings = ['utf-8', 'latin-1', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"Could not decode file with any supported encoding")
            
            # Parse SRT format
            # Split into subtitle blocks (separated by double newlines)
            blocks = content.strip().split('\n\n')
            
            text_lines = []
            timestamps = []
            
            for block in blocks:
                lines = block.strip().split('\n')
                
                # Each block should have at least 3 lines:
                # 1. Sequence number
                # 2. Timestamp (e.g., "00:00:00,000 --> 00:00:02,000")
                # 3+ Subtitle text
                if len(lines) < 3:
                    continue
                
                # Extract timestamp from line 2 (for optional metadata)
                timestamp_line = lines[1]
                if '-->' in timestamp_line:
                    start_time = timestamp_line.split('-->')[0].strip()
                    timestamps.append(start_time)
                
                # Lines 3+ are the actual subtitle text
                subtitle_text = ' '.join(lines[2:])
                
                # Clean up subtitle artifacts
                subtitle_text = self._clean_subtitle_text(subtitle_text)
                
                if subtitle_text.strip():
                    text_lines.append(subtitle_text)
            
            # Join all subtitle texts
            full_text = ' '.join(text_lines)
            
            # Normalize whitespace
            full_text = normalize_whitespace(full_text)
            
            # Extract title from filename
            title = extract_title_from_filename(path.name)
            
            logger.info(f"Loaded SRT: {path.name} ({len(text_lines)} segments, {len(full_text)} chars)")
            
            return {
                "text": full_text,
                "metadata": {
                    "source": path.name,
                    "file_type": "srt",
                    "path": str(path),
                    "title": title,
                    "num_segments": len(text_lines),
                    "duration": timestamps[-1] if timestamps else None,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to load SRT {path.name}: {e}")
            raise
    
    def _clean_subtitle_text(self, text: str) -> str:
        """
        Clean subtitle text from common artifacts.
        
        Removes:
        - HTML tags (<i>, <b>, etc.)
        - Speaker labels ([John:], (Speaker:))
        - Sound effects ([music], (applause))
        
        Args:
            text: Raw subtitle text
            
        Returns:
            Cleaned text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove speaker labels like [John:] or (Speaker:)
        text = re.sub(r'[\[\(][^\]\)]*:[\]\)]', '', text)
        
        # Remove sound effects like [music], (applause), etc.
        text = re.sub(
            r'[\[\(](music|applause|laughter|sound|noise|sfx|♪)[^\]\)]*[\]\)]',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()


class TxtLoader:
    """
    Loader for plain text (.txt) files.
    
    Simple loader for markdown, plain text notes, etc.
    """
    
    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load a plain text file.
        
        Args:
            path: Path to text file
            
        Returns:
            Dict with text content and metadata
        """
        logger.info(f"Loading TXT: {path.name}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Clean up whitespace
            text = normalize_whitespace(text)
            
            # Extract title from filename
            title = extract_title_from_filename(path.name)
            
            logger.info(f"Loaded TXT: {path.name} ({len(text)} chars)")
            
            return {
                "text": text,
                "metadata": {
                    "source": path.name,
                    "file_type": "txt",
                    "path": str(path),
                    "title": title,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to load TXT {path.name}: {e}")
            raise


class MarkdownLoader:
    """
    Loader for Markdown (.md) files.
    
    Loads markdown as plain text. Could be enhanced to preserve structure
    (headings, code blocks, etc.) in metadata if needed.
    """
    
    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load a Markdown file.
        
        Args:
            path: Path to markdown file
            
        Returns:
            Dict with text content and metadata
        """
        logger.info(f"Loading Markdown: {path.name}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Extract title from first # heading if present
            title_match = re.match(r'^#\s+(.+)$', text, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = extract_title_from_filename(path.name)
            
            # Clean up whitespace
            text = normalize_whitespace(text)
            
            logger.info(f"Loaded Markdown: {path.name} ({len(text)} chars)")
            
            return {
                "text": text,
                "metadata": {
                    "source": path.name,
                    "file_type": "md",
                    "path": str(path),
                    "title": title,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to load Markdown {path.name}: {e}")
            raise


# ============================================================================
# LOADER REGISTRY
# ============================================================================

# Map file extensions to loader instances
# TO ADD A NEW FILE TYPE: Just add a new entry here!
LOADER_REGISTRY: Dict[str, DocumentLoader] = {
    ".pdf": PdfLoader(),
    ".srt": SrtLoader(),
    ".txt": TxtLoader(),
    ".md": MarkdownLoader(),
    ".markdown": MarkdownLoader(),
    # Add more as needed:
    # ".docx": DocxLoader(),
    # ".pptx": PptxLoader(),
    # ".html": HtmlLoader(),
    # etc.
}


def get_loader_for_file(file_path: Path) -> Optional[DocumentLoader]:
    """
    Get the appropriate loader for a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Loader instance if extension is supported, None otherwise
    """
    extension = file_path.suffix.lower()
    return LOADER_REGISTRY.get(extension)


def get_supported_extensions() -> List[str]:
    """
    Get list of all supported file extensions.
    
    Returns:
        List of extensions like [".pdf", ".srt", ".txt", ...]
    """
    return list(LOADER_REGISTRY.keys())


def is_supported_file(file_path: Path) -> bool:
    """
    Check if a file type is supported by the loader system.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file extension is in the registry
    """
    return file_path.suffix.lower() in LOADER_REGISTRY


# ============================================================================
# UTILITY: EXTRACT COURSE ID FROM PATH
# ============================================================================

def extract_course_id_from_path(file_path: Path, data_root: Path) -> Optional[str]:
    """
    Extract a course/collection ID from the file path.
    
    Assumes directory structure like:
        data/
            programming-languages/
                pdfs/...
                srt/...
            data-visualization/
                pdfs/...
                srt/...
    
    Returns the first directory under data_root as the course ID.
    
    Args:
        file_path: Full path to file
        data_root: Root data directory
        
    Returns:
        Course ID string, or None if not derivable
    """
    try:
        # Get relative path from data root
        rel_path = file_path.relative_to(data_root)
        
        # First part of path is the course ID
        parts = rel_path.parts
        if parts:
            return parts[0]
    except (ValueError, IndexError):
        pass
    
    return None

