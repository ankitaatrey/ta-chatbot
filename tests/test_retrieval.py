"""Tests for retrieval functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vectordb import VectorDB
from src.embedder import Embedder
from src.retriever import Retriever


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for the test database."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def vectordb(temp_db_dir):
    """Create a test vector database."""
    embedder = Embedder(use_openai=False)
    db = VectorDB(
        persist_directory=temp_db_dir,
        collection_name="test_collection",
        embedder=embedder
    )
    return db


def test_add_and_retrieve(vectordb):
    """Test adding documents and retrieving them."""
    # Add test documents
    texts = [
        "The mitochondria is the powerhouse of the cell.",
        "DNA replication occurs during the S phase of the cell cycle.",
        "Photosynthesis converts light energy into chemical energy."
    ]
    
    metadatas = [
        {"title": "Biology", "page_start": 1, "page_end": 1, "source_path": "bio.pdf", "chunk_id": "bio_1"},
        {"title": "Biology", "page_start": 2, "page_end": 2, "source_path": "bio.pdf", "chunk_id": "bio_2"},
        {"title": "Biology", "page_start": 3, "page_end": 3, "source_path": "bio.pdf", "chunk_id": "bio_3"}
    ]
    
    ids = ["doc_1", "doc_2", "doc_3"]
    
    vectordb.add_documents(texts, metadatas, ids)
    
    # Verify documents were added
    assert vectordb.count() == 3
    
    # Query for mitochondria
    results = vectordb.query("What is the mitochondria?", n_results=1)
    
    assert results is not None
    assert len(results["documents"]) > 0
    assert len(results["documents"][0]) > 0
    
    # The most relevant document should contain "mitochondria"
    top_doc = results["documents"][0][0]
    assert "mitochondria" in top_doc.lower()


def test_retriever_score_threshold(vectordb):
    """Test that retriever filters by score threshold."""
    # Add documents
    texts = [
        "Cell biology is the study of cells.",
        "Physics studies matter and energy.",
        "Chemistry examines substances and reactions."
    ]
    
    metadatas = [
        {"title": "Bio", "page_start": 1, "page_end": 1, "source_path": "bio.pdf", "chunk_id": "b1"},
        {"title": "Phys", "page_start": 1, "page_end": 1, "source_path": "phys.pdf", "chunk_id": "p1"},
        {"title": "Chem", "page_start": 1, "page_end": 1, "source_path": "chem.pdf", "chunk_id": "c1"}
    ]
    
    ids = ["d1", "d2", "d3"]
    
    vectordb.add_documents(texts, metadatas, ids)
    
    # Create retriever with high threshold
    retriever = Retriever(
        vectordb=vectordb,
        top_k=3,
        score_threshold=0.9,  # Very high threshold
        use_mmr=False
    )
    
    # Query about cells (should match first document well)
    results = retriever.retrieve("Tell me about cells")
    
    # With high threshold, only very relevant docs should be returned
    # (exact number depends on similarity scores)
    assert isinstance(results, list)
    
    # All returned results should meet threshold
    for result in results:
        assert result["score"] >= 0.9 or len(results) == 0


def test_retriever_metadata_preserved(vectordb):
    """Test that metadata is preserved through retrieval."""
    # Add a document with specific metadata
    texts = ["Test document about biology."]
    metadatas = [{
        "title": "Test Title",
        "page_start": 5,
        "page_end": 7,
        "source_path": "/path/to/test.pdf",
        "chunk_id": "test_chunk_1"
    }]
    ids = ["test_id"]
    
    vectordb.add_documents(texts, metadatas, ids)
    
    # Retrieve
    retriever = Retriever(
        vectordb=vectordb,
        top_k=1,
        score_threshold=0.0,
        use_mmr=False
    )
    
    results = retriever.retrieve("biology")
    
    assert len(results) > 0
    
    result = results[0]
    metadata = result["metadata"]
    
    # Check all metadata fields are preserved
    assert metadata["title"] == "Test Title"
    assert metadata["page_start"] == 5
    assert metadata["page_end"] == 7
    assert metadata["source_path"] == "/path/to/test.pdf"
    assert metadata["chunk_id"] == "test_chunk_1"


def test_delete_by_source(vectordb):
    """Test deleting documents by source."""
    # Add documents from two sources
    texts = ["Doc from source 1", "Another from source 1", "Doc from source 2"]
    metadatas = [
        {"title": "S1", "page_start": 1, "page_end": 1, "source_path": "source1.pdf", "chunk_id": "s1_1"},
        {"title": "S1", "page_start": 2, "page_end": 2, "source_path": "source1.pdf", "chunk_id": "s1_2"},
        {"title": "S2", "page_start": 1, "page_end": 1, "source_path": "source2.pdf", "chunk_id": "s2_1"}
    ]
    ids = ["d1", "d2", "d3"]
    
    vectordb.add_documents(texts, metadatas, ids)
    
    assert vectordb.count() == 3
    
    # Delete source 1
    deleted = vectordb.delete_by_source("source1.pdf")
    
    assert deleted == 2
    assert vectordb.count() == 1


def test_vectordb_stats(vectordb):
    """Test database statistics."""
    # Add documents
    texts = ["Doc 1", "Doc 2", "Doc 3"]
    metadatas = [
        {"title": "T1", "page_start": 1, "page_end": 1, "source_path": "file1.pdf", "chunk_id": "f1_1"},
        {"title": "T1", "page_start": 2, "page_end": 2, "source_path": "file1.pdf", "chunk_id": "f1_2"},
        {"title": "T2", "page_start": 1, "page_end": 1, "source_path": "file2.pdf", "chunk_id": "f2_1"}
    ]
    ids = ["1", "2", "3"]
    
    vectordb.add_documents(texts, metadatas, ids)
    
    stats = vectordb.get_stats()
    
    assert stats["total_chunks"] == 3
    assert stats["unique_documents"] == 2
    assert len(stats["sources"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

