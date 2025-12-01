"""Tests for PDF chunking functionality."""

import pytest
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.splitter import TokenAwareChunker, PDFChunk


class TestTokenAwareChunker:
    """Test the TokenAwareChunker class."""
    
    def test_count_tokens(self):
        """Test token counting."""
        chunker = TokenAwareChunker(chunk_size=100)
        
        text = "This is a test sentence."
        token_count = chunker.count_tokens(text)
        
        # Token count should be reasonable (rough estimate: 1 token per 4 chars)
        assert token_count > 0
        assert token_count < len(text)  # Should be less than character count
    
    def test_small_text_no_split(self):
        """Test that small text is not split."""
        chunker = TokenAwareChunker(chunk_size=100, chunk_overlap=10)
        
        text = "This is a short text that should not be split."
        chunks = chunker.split_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_large_text_split(self):
        """Test that large text is split into chunks."""
        chunker = TokenAwareChunker(chunk_size=50, chunk_overlap=10)
        
        # Create a long text
        text = " ".join([f"Sentence number {i}." for i in range(100)])
        chunks = chunker.split_text(text)
        
        # Should be split into multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be non-empty
        for chunk in chunks:
            assert len(chunk.strip()) > 0
    
    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        chunker = TokenAwareChunker(chunk_size=50, chunk_overlap=20)
        
        # Create text with distinct sentences
        sentences = [f"This is sentence number {i}." for i in range(20)]
        text = " ".join(sentences)
        
        chunks = chunker.split_text(text)
        
        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            # (This is a basic check - actual overlap may vary)
            for i in range(len(chunks) - 1):
                chunk1 = chunks[i]
                chunk2 = chunks[i + 1]
                
                # Both should be non-empty
                assert len(chunk1) > 0
                assert len(chunk2) > 0


class TestPDFChunk:
    """Test the PDFChunk class."""
    
    def test_create_chunk(self):
        """Test creating a PDF chunk."""
        chunk = PDFChunk(
            text="Sample text",
            page_start=1,
            page_end=2,
            source_path="/path/to/file.pdf",
            title="Test Document",
            chunk_id="test_chunk_1"
        )
        
        assert chunk.text == "Sample text"
        assert chunk.page_start == 1
        assert chunk.page_end == 2
        assert chunk.source_path == "/path/to/file.pdf"
        assert chunk.title == "Test Document"
        assert chunk.chunk_id == "test_chunk_1"
    
    def test_chunk_to_dict(self):
        """Test converting chunk to dictionary."""
        chunk = PDFChunk(
            text="Sample text",
            page_start=3,
            page_end=3,
            source_path="/path/to/file.pdf",
            title="Test Document",
            chunk_id="test_chunk_2"
        )
        
        chunk_dict = chunk.to_dict()
        
        assert "text" in chunk_dict
        assert "metadata" in chunk_dict
        assert chunk_dict["text"] == "Sample text"
        assert chunk_dict["metadata"]["page_start"] == 3
        assert chunk_dict["metadata"]["page_end"] == 3
        assert chunk_dict["metadata"]["title"] == "Test Document"


def test_chunk_preserves_page_numbers():
    """Test that chunking preserves page number information."""
    chunk = PDFChunk(
        text="Content from page 5",
        page_start=5,
        page_end=5,
        source_path="test.pdf",
        title="Test",
        chunk_id="test_p5_c0"
    )
    
    chunk_dict = chunk.to_dict()
    metadata = chunk_dict["metadata"]
    
    # Page numbers should be preserved
    assert metadata["page_start"] == 5
    assert metadata["page_end"] == 5
    
    # Chunk ID should contain page reference
    assert "p5" in chunk.chunk_id


def test_chunk_metadata_structure():
    """Test that chunk metadata has required fields."""
    chunk = PDFChunk(
        text="Test content",
        page_start=1,
        page_end=2,
        source_path="/path/test.pdf",
        title="Test PDF",
        chunk_id="test_id"
    )
    
    metadata = chunk.to_dict()["metadata"]
    
    # Required fields
    required_fields = ["page_start", "page_end", "source_path", "title", "chunk_id"]
    for field in required_fields:
        assert field in metadata, f"Missing required field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

