"""Tests for citation functionality."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.citations import (
    Citation,
    merge_citations,
    format_citations_list,
    extract_citations_from_text,
    create_context_block
)


class TestCitation:
    """Test the Citation class."""
    
    def test_single_page_citation(self):
        """Test citation for a single page."""
        citation = Citation("Test Document", 5, 5)
        assert str(citation) == "[Test Document, p. 5]"
    
    def test_page_range_citation(self):
        """Test citation for a page range."""
        citation = Citation("Test Document", 5, 8)
        assert str(citation) == "[Test Document, pp. 5–8]"
    
    def test_citation_with_snippet(self):
        """Test citation with snippet."""
        citation = Citation("Test Document", 1, 1, "This is a snippet")
        assert citation.snippet == "This is a snippet"


def test_merge_citations_same_source():
    """Test merging citations from the same source."""
    chunks = [
        {
            "text": "Content from page 1",
            "metadata": {
                "title": "Biology 101",
                "page_start": 1,
                "page_end": 1
            }
        },
        {
            "text": "Content from page 2",
            "metadata": {
                "title": "Biology 101",
                "page_start": 2,
                "page_end": 2
            }
        }
    ]
    
    citations = merge_citations(chunks)
    
    # Should merge into a single citation with page range
    assert len(citations) > 0
    
    # Find the Biology citation
    bio_citation = next((c for c in citations if c.title == "Biology 101"), None)
    assert bio_citation is not None
    assert bio_citation.page_start == 1
    assert bio_citation.page_end == 2


def test_merge_citations_different_sources():
    """Test merging citations from different sources."""
    chunks = [
        {
            "text": "Content from bio",
            "metadata": {
                "title": "Biology 101",
                "page_start": 1,
                "page_end": 1
            }
        },
        {
            "text": "Content from physics",
            "metadata": {
                "title": "Physics 201",
                "page_start": 1,
                "page_end": 1
            }
        }
    ]
    
    citations = merge_citations(chunks)
    
    # Should create separate citations
    assert len(citations) >= 2
    
    titles = [c.title for c in citations]
    assert "Biology 101" in titles
    assert "Physics 201" in titles


def test_merge_citations_non_contiguous_pages():
    """Test merging citations with non-contiguous pages."""
    chunks = [
        {
            "text": "Page 1",
            "metadata": {
                "title": "Document",
                "page_start": 1,
                "page_end": 1
            }
        },
        {
            "text": "Page 5",
            "metadata": {
                "title": "Document",
                "page_start": 5,
                "page_end": 5
            }
        }
    ]
    
    citations = merge_citations(chunks)
    
    # Should create separate ranges for non-contiguous pages
    doc_citations = [c for c in citations if c.title == "Document"]
    
    # Either two separate citations or one with both ranges
    assert len(doc_citations) > 0


def test_format_citations_list():
    """Test formatting a list of citations."""
    citations = [
        Citation("Biology 101", 1, 2),
        Citation("Physics 201", 5, 5)
    ]
    
    formatted = format_citations_list(citations)
    
    assert "Biology 101" in formatted
    assert "Physics 201" in formatted
    assert "pp. 1–2" in formatted or "pp. 1-2" in formatted
    assert "p. 5" in formatted


def test_format_empty_citations():
    """Test formatting empty citations list."""
    formatted = format_citations_list([])
    assert formatted == "No sources"


def test_extract_citations_from_text():
    """Test extracting citations from text."""
    text = "The cell [Biology 101, pp. 1-2] contains organelles [Biology 101, p. 5]."
    
    citations = extract_citations_from_text(text)
    
    assert len(citations) == 2
    
    # First citation
    assert citations[0][0] == "Biology 101"
    assert citations[0][1] == 1  # page_start
    assert citations[0][2] == 2  # page_end
    
    # Second citation
    assert citations[1][0] == "Biology 101"
    assert citations[1][1] == 5
    assert citations[1][2] == 5


def test_extract_citations_no_citations():
    """Test extracting citations from text without citations."""
    text = "This text has no citations."
    
    citations = extract_citations_from_text(text)
    
    assert len(citations) == 0


def test_create_context_block():
    """Test creating a context block for LLM prompts."""
    chunks = [
        {
            "text": "The mitochondria is the powerhouse of the cell.",
            "metadata": {
                "title": "Biology 101",
                "page_start": 3,
                "page_end": 3
            }
        },
        {
            "text": "DNA replication occurs during S phase.",
            "metadata": {
                "title": "Biology 101",
                "page_start": 5,
                "page_end": 5
            }
        }
    ]
    
    context = create_context_block(chunks)
    
    # Should contain the text
    assert "mitochondria" in context
    assert "DNA replication" in context
    
    # Should contain page references
    assert "p. 3" in context
    assert "p. 5" in context
    
    # Should contain title
    assert "Biology 101" in context


def test_create_context_block_empty():
    """Test creating context block with no chunks."""
    context = create_context_block([])
    assert "No relevant context" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

