# debug_index.py
"""
Debug script to inspect what's stored in the vector database.
Save this in your ta-chatbot directory and run: python debug_index.py
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.vectordb import get_vectordb
from src.config import config
import json

def inspect_index():
    """Inspect the contents of the vector database."""
    
    print("=" * 80)
    print("VECTOR DATABASE INSPECTION")
    print("=" * 80)
    
    # Initialize vector database
    vectordb = get_vectordb()
    
    # Get statistics
    stats = vectordb.get_stats()
    print(f"\n📊 Statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Unique documents: {stats['unique_documents']}")
    
    print(f"\n📁 Source Documents:")
    for source in stats['sources']:
        print(f"  - {Path(source).name}")
    
    # Get all documents (limit to first 1000 for safety)
    print(f"\n📄 Sample Chunks (first 5):")
    print("-" * 80)
    
    if stats['total_chunks'] > 0:
        results = vectordb.collection.get(
            limit=min(5, stats['total_chunks']),
            include=["documents", "metadatas"]
        )
        
        for i, (doc_id, doc, metadata) in enumerate(zip(
            results['ids'], 
            results['documents'], 
            results['metadatas']
        ), 1):
            print(f"\nChunk {i}:")
            print(f"  ID: {doc_id}")
            print(f"  Title: {metadata.get('title', 'N/A')}")
            print(f"  Page: {metadata.get('page_start', 'N/A')}")
            print(f"  Source: {Path(metadata.get('source_path', 'N/A')).name}")
            print(f"  Text preview: {doc[:200]}...")
            print(f"  Full text length: {len(doc)} characters")
    
    print("\n" + "=" * 80)

def inspect_specific_document(filename):
    """Inspect chunks from a specific document (PDF or SRT)."""
    
    print(f"\n🔍 Inspecting Document: {filename}")
    print("=" * 80)
    
    vectordb = get_vectordb()
    
    # Get all chunks and filter manually (ChromaDB doesn't support $contains)
    all_results = vectordb.collection.get(
        include=["documents", "metadatas"]
    )
    
    # Filter results by PDF name
    filtered_ids = []
    filtered_docs = []
    filtered_metas = []
    
    for doc_id, doc, metadata in zip(
        all_results['ids'], 
        all_results['documents'], 
        all_results['metadatas']
    ):
        source_path = metadata.get('source_path', '')
        if filename in source_path:
            filtered_ids.append(doc_id)
            filtered_docs.append(doc)
            filtered_metas.append(metadata)
    
    if not filtered_ids:
        print(f"❌ No chunks found for document: {filename}")
        print(f"\n💡 Available documents in the index:")
        
        # Show available documents
        unique_docs = set()
        for metadata in all_results['metadatas']:
            source_path = metadata.get('source_path', '')
            file_type = metadata.get('file_type', 'pdf')
            if source_path:
                doc_name = Path(source_path).name
                unique_docs.add(f"{doc_name} ({file_type})")
        
        for doc in sorted(unique_docs):
            print(f"  - {doc}")
        return
    
    print(f"\n✅ Found {len(filtered_ids)} chunks")
    
    # Show each chunk
    for i, (doc_id, doc, metadata) in enumerate(zip(
        filtered_ids, 
        filtered_docs, 
        filtered_metas
    ), 1):
        print(f"\n{'─' * 80}")
        print(f"Chunk {i}/{len(filtered_ids)}")
        print(f"{'─' * 80}")
        print(f"ID: {doc_id}")
        print(f"File Type: {metadata.get('file_type', 'pdf')}")
        page_start = metadata.get('page_start', 0)
        if page_start > 0:
            print(f"Page: {page_start}")
        print(f"Length: {len(doc)} characters")
        print(f"\nFull Text:\n{doc}")

def test_query(query_text):
    """Test a query to see what chunks are retrieved."""
    
    print(f"\n🔎 Testing Query: '{query_text}'")
    print("=" * 80)
    
    vectordb = get_vectordb()
    results = vectordb.query(query_text, n_results=3)
    
    print(f"\n✅ Retrieved {len(results['ids'][0])} chunks")
    
    for i, (doc_id, doc, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        print(f"\n{'─' * 80}")
        print(f"Result {i} (Similarity: {1 - distance:.4f})")
        print(f"{'─' * 80}")
        print(f"ID: {doc_id}")
        print(f"Source: {Path(metadata['source_path']).name}")
        print(f"Page: {metadata['page_start']}")
        print(f"\nText:\n{doc[:300]}...")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "inspect":
            inspect_index()
        
        elif command == "doc" and len(sys.argv) > 2:
            filename = sys.argv[2]
            inspect_specific_document(filename)
        
        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            test_query(query)
        
        else:
            print("Usage:")
            print("  python debug_index.py inspect                           # Show index overview")
            print("  python debug_index.py doc intro.pdf                     # Show all chunks from a document")
            print("  python debug_index.py doc sample_lecture.srt            # Show all chunks from an SRT")
            print("  python debug_index.py query 'your question'             # Test a query")
    else:
        # Default: show overview
        inspect_index()