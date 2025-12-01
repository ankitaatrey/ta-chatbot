"""
Citation generation and formatting utilities for multi-file-type RAG.

This module provides file-type-aware citation formatting that works
consistently across PDFs, transcripts, text files, and other document types.

Citation Format Examples:
- PDF: "[Introduction to ML (PDF), pp. 3-5]"
- SRT: "[Lecture 1 Transcript (SRT), segment 12]"
- TXT/MD: "[Course Notes (TXT)]"
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict
import re


class Citation:
    """
    Represents a citation with source and location information.
    
    Now supports multiple file types with appropriate formatting.
    """
    
    def __init__(
        self,
        title: str,
        file_type: str = "pdf",
        page_start: int = None,
        page_end: int = None,
        snippet: str = "",
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize a citation.
        
        Args:
            title: Document title
            file_type: Type of document ("pdf", "srt", "txt", "md", etc.)
            page_start: Starting page number (for PDFs)
            page_end: Ending page number (for PDFs)
            snippet: Optional text snippet
            metadata: Additional metadata for type-specific formatting
        """
        self.title = title
        self.file_type = file_type.lower()
        self.page_start = page_start
        self.page_end = page_end
        self.snippet = snippet
        self.metadata = metadata or {}
    
    def __str__(self) -> str:
        """Format citation as string based on file type."""
        return self.format_citation()
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def format_citation(self) -> str:
        """
        Format citation appropriately for the file type.
        
        Returns:
            Formatted citation string
        """
        # Uppercase file type for display
        type_label = self.file_type.upper()
        
        if self.file_type == "pdf":
            # PDF: Include page numbers
            if self.page_start is not None and self.page_end is not None:
                if self.page_start == self.page_end:
                    return f"[{self.title} (PDF), p. {self.page_start}]"
                else:
                    return f"[{self.title} (PDF), pp. {self.page_start}–{self.page_end}]"
            else:
                return f"[{self.title} (PDF)]"
        
        elif self.file_type == "srt":
            # SRT: Could include segment number or timestamp
            # For now, just indicate it's a transcript
            return f"[{self.title} (Transcript)]"
        
        elif self.file_type in ["txt", "md", "markdown"]:
            # Text files: Just title and type
            return f"[{self.title} ({type_label})]"
        
        else:
            # Generic fallback for unknown types
            return f"[{self.title} ({type_label})]"


def merge_citations(chunks: List[Dict[str, Any]]) -> List[Citation]:
    """
    Merge chunks from the same source into citation objects.
    
    Now handles multiple file types and formats them appropriately.
    
    Args:
        chunks: List of chunk dictionaries with metadata
        
    Returns:
        List of Citation objects with merged info
    """
    # Group by (title, file_type) to handle multiple file types
    by_source = defaultdict(list)
    
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Unknown")
        file_type = metadata.get("file_type", "pdf")  # Default to PDF for backward compat
        
        # Create a key combining title and file type
        source_key = (title, file_type)
        
        by_source[source_key].append({
            "metadata": metadata,
            "snippet": chunk.get("text", "")[:200]  # First 200 chars
        })
    
    # Create citations for each source
    citations = []
    
    for (title, file_type), chunks_info in by_source.items():
        metadata = chunks_info[0]["metadata"]  # Use first chunk's metadata
        snippets = [c["snippet"] for c in chunks_info]
        combined_snippet = " ... ".join(snippets)
        
        if file_type == "pdf":
            # For PDFs, merge page ranges
            page_ranges = []
            for chunk_info in chunks_info:
                m = chunk_info["metadata"]
                page_start = m.get("page_start", 1)
                page_end = m.get("page_end", page_start)
                page_ranges.append((page_start, page_end))
            
            # Sort by page number
            page_ranges.sort(key=lambda x: x[0])
            
            # Merge contiguous ranges
            if page_ranges:
                merged_ranges = []
                current_start, current_end = page_ranges[0]
                
                for page_start, page_end in page_ranges[1:]:
                    if page_start <= current_end + 1:
                        # Contiguous or overlapping
                        current_end = max(current_end, page_end)
                    else:
                        # Gap found
                        merged_ranges.append((current_start, current_end))
                        current_start, current_end = page_start, page_end
                
                # Don't forget the last range
                merged_ranges.append((current_start, current_end))
                
                # Create citation for each merged range
                for start, end in merged_ranges:
                    citations.append(Citation(
                        title=title,
                        file_type=file_type,
                        page_start=start,
                        page_end=end,
                        snippet=combined_snippet,
                        metadata=metadata
                    ))
        else:
            # For non-PDF files, just create one citation per source
            citations.append(Citation(
                title=title,
                file_type=file_type,
                snippet=combined_snippet,
                metadata=metadata
            ))
    
    return citations


def format_citations_list(citations: List[Citation]) -> str:
    """
    Format a list of citations as a string.
    
    Args:
        citations: List of Citation objects
        
    Returns:
        Formatted citation string
    """
    if not citations:
        return "No sources"
    
    citation_strs = [str(c) for c in citations]
    return "; ".join(citation_strs)


def extract_citations_from_text(text: str) -> List[Tuple[str, str, int, int]]:
    """
    Extract citation markers from generated text.
    
    Now handles multiple file type formats:
    - [Title (PDF), pp. 1-2]
    - [Title (Transcript)]
    - [Title (TXT)]
    
    Args:
        text: Text containing citations
        
    Returns:
        List of (title, file_type, page_start, page_end) tuples
    """
    citations = []
    
    # Pattern 1: PDF-style with pages [Title (PDF), pp. 1-2]
    pdf_pattern = r'\[([^\]]+?)\s*\(PDF\),\s*pp?\.\s*(\d+)(?:[-–](\d+))?\]'
    for match in re.finditer(pdf_pattern, text, re.IGNORECASE):
        title = match.group(1).strip()
        page_start = int(match.group(2))
        page_end = int(match.group(3)) if match.group(3) else page_start
        citations.append((title, "pdf", page_start, page_end))
    
    # Pattern 2: Generic type without pages [Title (TYPE)]
    generic_pattern = r'\[([^\]]+?)\s*\(([A-Z]+)\)\]'
    for match in re.finditer(generic_pattern, text):
        title = match.group(1).strip()
        file_type = match.group(2).lower()
        if file_type != "pdf":  # Don't double-count PDFs
            citations.append((title, file_type, None, None))
    
    return citations


def format_source_block(citation: Citation) -> str:
    """
    Format a source block with title, location, and snippet.
    
    Args:
        citation: Citation object
        
    Returns:
        Formatted markdown block
    """
    # Format location based on file type
    if citation.file_type == "pdf" and citation.page_start is not None:
        if citation.page_start == citation.page_end:
            location = f"p. {citation.page_start}"
        else:
            location = f"pp. {citation.page_start}–{citation.page_end}"
    else:
        location = citation.file_type.upper()
    
    block = f"**{citation.title}** ({location})"
    
    if citation.snippet:
        block += f"\n> {citation.snippet}"
    
    return block


def create_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Create a formatted context block for LLM prompts.
    
    Now includes file type information in the context.
    
    Args:
        chunks: Retrieved chunks with metadata
        
    Returns:
        Formatted context string
    """
    if not chunks:
        return "No relevant context found."
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Unknown")
        file_type = metadata.get("file_type", "pdf")
        text = chunk.get("text", "")
        
        # Format location based on file type
        if file_type == "pdf":
            page_start = metadata.get("page_start", 1)
            page_end = metadata.get("page_end", page_start)
            if page_start == page_end:
                location = f"p. {page_start}"
            else:
                location = f"pp. {page_start}–{page_end}"
        else:
            location = file_type.upper()
        
        context_parts.append(
            f"[{i}] {title} ({location}):\n\"{text}\"\n"
        )
    
    return "\n".join(context_parts)


def format_source_for_display(metadata: Dict[str, Any], score: float = None) -> Dict[str, str]:
    """
    Format source metadata for display in UI.
    
    Creates a standardized display format that works across all file types.
    
    Args:
        metadata: Chunk metadata
        score: Optional relevance score
        
    Returns:
        Dict with display_title, display_location, file_type_icon
    """
    title = metadata.get("title", "Unknown")
    file_type = metadata.get("file_type", "unknown")
    
    # Choose appropriate icon/emoji for file type
    type_icons = {
        "pdf": "📄",
        "srt": "🎬",
        "txt": "📝",
        "md": "📋",
        "markdown": "📋",
    }
    icon = type_icons.get(file_type, "📎")
    
    # Format location based on file type
    if file_type == "pdf":
        page_start = metadata.get("page_start", "?")
        page_end = metadata.get("page_end", page_start)
        if page_start == page_end:
            location = f"Page {page_start}"
        else:
            location = f"Pages {page_start}–{page_end}"
    elif file_type == "srt":
        num_segments = metadata.get("num_segments", "?")
        location = f"Video Transcript"
    else:
        location = file_type.upper()
    
    display_title = f"{icon} {title}"
    
    return {
        "display_title": display_title,
        "display_location": location,
        "file_type": file_type,
        "icon": icon
    }
