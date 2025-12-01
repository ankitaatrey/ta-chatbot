"""PDF text extraction and token-aware chunking."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    import pypdf

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from src.utils.text_normalize import clean_pdf_text, extract_title_from_filename
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class PDFChunk:
    """Represents a chunk of text from a PDF with metadata."""
    
    def __init__(
        self,
        text: str,
        page_start: int,
        page_end: int,
        source_path: str,
        title: str,
        chunk_id: str,
    ):
        """
        Initialize a PDF chunk.
        
        Args:
            text: Chunk text content
            page_start: Starting page number (1-indexed)
            page_end: Ending page number (1-indexed)
            source_path: Path to source PDF
            title: Document title
            chunk_id: Unique chunk identifier
        """
        self.text = text
        self.page_start = page_start
        self.page_end = page_end
        self.source_path = source_path
        self.title = title
        self.chunk_id = chunk_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary format."""
        return {
            "text": self.text,
            "metadata": {
                "page_start": self.page_start,
                "page_end": self.page_end,
                "source_path": self.source_path,
                "title": self.title,
                "chunk_id": self.chunk_id,
            }
        }


class TokenAwareChunker:
    """
    Token-aware recursive text chunker.
    
    This class splits text into chunks based on token count (not characters).
    Token-aware chunking is important because:
    1. LLMs have token-based context limits (e.g., 4096 tokens)
    2. Embeddings models also work with tokens
    3. Character-based splitting can split in the middle of words
    
    The recursive approach tries to split at natural boundaries (paragraphs,
    then sentences, then words) to maintain context coherence.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target chunk size in tokens (not characters!)
            chunk_overlap: Overlap between chunks in tokens - this helps maintain
                          context across chunk boundaries
            encoding_name: Tiktoken encoding name (cl100k_base used by GPT-4)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Try to load tiktoken for accurate token counting
        # Tiktoken is OpenAI's tokenizer library - gives exact token counts
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding: {e}. Using character-based estimation.")
                self.encoding = None
        else:
            logger.warning("tiktoken not available. Using character-based token estimation.")
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Input text
            
        Returns:
            Token count
        """
        if self.encoding:
            # Use tiktoken for accurate count (encodes text to token IDs)
            return len(self.encoding.encode(text))
        
        # Fallback: rough estimation if tiktoken unavailable
        # Rule of thumb: 1 token ≈ 4 characters for English text
        # This is approximate but good enough for chunking
        return len(text) // 4
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks recursively.
        
        Strategy: Try to split at natural boundaries to preserve meaning.
        We prefer larger semantic units (paragraphs) over smaller ones (words).
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Separators in order of preference (paragraph -> sentence -> word -> character)
        # Why this order? Keeps context together:
        # 1. "\n\n" - paragraph breaks (best: keeps related sentences together)
        # 2. "\n" - line breaks (good: maintains sentence structure)
        # 3. ". " - sentence endings (okay: splits between sentences)
        # 4. " " - word boundaries (last resort: at least splits between words)
        # 5. "" - character split (absolute last resort)
        separators = ["\n\n", "\n", ". ", " ", ""]
        
        return self._split_recursive(text, separators)
    
    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively split text using separators.
        
        Args:
            text: Text to split
            separators: List of separators to try
            
        Returns:
            List of chunks
        """
        if not text:
            return []
        
        token_count = self.count_tokens(text)
        
        # If text is small enough, return as-is
        if token_count <= self.chunk_size:
            return [text]
        
        # Try each separator
        for i, separator in enumerate(separators):
            if separator == "":
                # Last resort: split by characters
                return self._split_by_length(text)
            
            if separator in text:
                splits = text.split(separator)
                # Re-add separator to maintain context
                if separator != "\n\n":
                    splits = [s + separator for s in splits[:-1]] + [splits[-1]]
                else:
                    splits = [s + "\n\n" for s in splits[:-1]] + [splits[-1]]
                
                # Merge splits into chunks
                return self._merge_splits(splits, separators[i+1:])
        
        return [text]
    
    def _merge_splits(self, splits: List[str], remaining_separators: List[str]) -> List[str]:
        """
        Merge splits into appropriately sized chunks with overlap.
        
        This is the core algorithm that:
        1. Combines small splits into larger chunks (up to chunk_size)
        2. Adds overlap between chunks for context continuity
        3. Recursively splits any piece that's too large
        
        Args:
            splits: List of text splits from separator-based splitting
            remaining_separators: Remaining separators for recursive splitting
            
        Returns:
            List of chunks with appropriate size and overlap
        """
        chunks = []  # Final list of chunks to return
        current_chunk = []  # Text pieces being accumulated into current chunk
        current_size = 0  # Token count of current chunk
        
        for split in splits:
            split_size = self.count_tokens(split)
            
            # Case 1: Single split is larger than target chunk size
            # We can't just add it - need to split it further
            if split_size > self.chunk_size:
                # Save what we've accumulated so far
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Recursively split this large piece using next separator
                # (e.g., if we split by "\n\n", try "\n" next)
                sub_chunks = self._split_recursive(split, remaining_separators)
                chunks.extend(sub_chunks)
                continue
            
            # Case 2: Adding this split would exceed chunk size
            # Time to finalize current chunk and start a new one
            if current_size + split_size > self.chunk_size and current_chunk:
                # Finalize and save current chunk
                chunks.append("".join(current_chunk))
                
                # Create overlap for context continuity
                # Overlap helps retrieval by including context from previous chunk
                overlap_text = "".join(current_chunk)
                overlap_size = self.count_tokens(overlap_text)
                
                # Only keep the last part (up to chunk_overlap tokens)
                if overlap_size > self.chunk_overlap:
                    # Estimate character count for overlap
                    # This is approximate but works well in practice
                    overlap_chars = len(overlap_text) * self.chunk_overlap // max(overlap_size, 1)
                    overlap_text = overlap_text[-overlap_chars:]  # Take end of text
                
                # Start new chunk with overlap text
                current_chunk = [overlap_text] if overlap_text else []
                current_size = self.count_tokens(overlap_text) if overlap_text else 0
            
            # Case 3: Normal case - add split to current chunk
            current_chunk.append(split)
            current_size += split_size
        
        # Don't forget the last chunk we were building!
        if current_chunk:
            chunks.append("".join(current_chunk))
        
        return chunks
    
    def _split_by_length(self, text: str) -> List[str]:
        """
        Split text by character length as last resort.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunks
        """
        # Approximate character count for target tokens
        chars_per_chunk = self.chunk_size * 4
        overlap_chars = self.chunk_overlap * 4
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chars_per_chunk
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap_chars
        
        return chunks


def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text from PDF with page numbers.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dictionaries with 'page' and 'text' keys
    """
    pages = []
    
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                cleaned_text = clean_pdf_text(text)
                if cleaned_text.strip():
                    pages.append({"page": page_num, "text": cleaned_text})
            doc.close()
            return pages
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path}: {e}")
    
    # Fallback to pypdf
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                cleaned_text = clean_pdf_text(text)
                if cleaned_text.strip():
                    pages.append({"page": page_num, "text": cleaned_text})
        return pages
    except Exception as e:
        logger.error(f"pypdf extraction failed for {pdf_path}: {e}")
        return []


def chunk_pdf(
    pdf_path: Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    title: Optional[str] = None
) -> List[PDFChunk]:
    """
    Extract and chunk a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
        title: Optional document title (derived from filename if not provided)
        
    Returns:
        List of PDFChunk objects
    """
    logger.info(f"Chunking PDF: {pdf_path}")
    
    # Extract text with page numbers
    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        logger.warning(f"No text extracted from {pdf_path}")
        return []
    
    # Determine title
    if title is None:
        title = extract_title_from_filename(pdf_path.name)
    
    # Initialize chunker
    chunker = TokenAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Chunk each page and track page numbers
    all_chunks = []
    chunk_counter = 0
    
    for page_info in pages:
        page_num = page_info["page"]
        page_text = page_info["text"]
        
        # Split page text into chunks
        text_chunks = chunker.split_text(page_text)
        
        for chunk_text in text_chunks:
            chunk_id = f"{pdf_path.stem}_p{page_num}_c{chunk_counter}"
            
            chunk = PDFChunk(
                text=chunk_text.strip(),
                page_start=page_num,
                page_end=page_num,
                source_path=str(pdf_path),
                title=title,
                chunk_id=chunk_id,
            )
            
            all_chunks.append(chunk)
            chunk_counter += 1
    
    logger.info(f"Created {len(all_chunks)} chunks from {len(pages)} pages")
    return all_chunks

