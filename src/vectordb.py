"""ChromaDB vector database management."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings

from src.config import config
from src.embedder import get_embedder
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class VectorDB:
    """ChromaDB vector database wrapper."""
    
    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: Optional[str] = None,
        embedder = None
    ):
        """
        Initialize the vector database.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
            embedder: Embedder instance (created if None)
        """
        self.persist_directory = persist_directory or config.chroma_path
        self.collection_name = collection_name or config.collection_name
        
        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        logger.info(f"Initializing ChromaDB at {self.persist_directory}")
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedder
        self.embedder = embedder or get_embedder()
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the collection.
        
        Args:
            texts: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        if not texts:
            logger.warning("No documents to add")
            return
        
        logger.info(f"Adding {len(texts)} documents to collection")
        
        # Generate embeddings
        embeddings = self.embedder.embed_documents(texts)
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Successfully added {len(texts)} documents")
    
    def upsert_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Upsert documents (add or update if exists).
        
        Args:
            texts: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        if not texts:
            logger.warning("No documents to upsert")
            return
        
        logger.info(f"Upserting {len(texts)} documents")
        
        # Generate embeddings
        embeddings = self.embedder.embed_documents(texts)
        
        # Upsert to collection
        self.collection.upsert(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Successfully upserted {len(texts)} documents")
    
    def query(
        self,
        query_text: str,
        n_results: int = 4,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection.
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
            
        Returns:
            Query results dictionary
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query_text)
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def get_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Get documents by IDs.
        
        Args:
            ids: List of document IDs
            
        Returns:
            Documents dictionary
        """
        return self.collection.get(
            ids=ids,
            include=["documents", "metadatas"]
        )
    
    def delete_by_source(self, source_path: str) -> int:
        """
        Delete all documents from a specific source.
        
        Args:
            source_path: Source file path
            
        Returns:
            Number of documents deleted
        """
        logger.info(f"Deleting documents from source: {source_path}")
        
        # Query to find all matching documents
        try:
            results = self.collection.get(
                where={"source_path": source_path},
                include=["documents"]
            )
            
            if results and results.get("ids"):
                ids_to_delete = results["ids"]
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} documents")
                return len(ids_to_delete)
            else:
                logger.info("No documents found to delete")
                return 0
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return 0
    
    def delete_collection(self) -> None:
        """Delete the entire collection."""
        logger.warning(f"Deleting collection: {self.collection_name}")
        self.client.delete_collection(name=self.collection_name)
        
        # Recreate empty collection
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Collection deleted and recreated")
    
    def count(self) -> int:
        """
        Get the number of documents in the collection.
        
        Returns:
            Document count
        """
        return self.collection.count()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Statistics dictionary
        """
        count = self.count()
        
        # Get unique sources
        if count > 0:
            results = self.collection.get(
                limit=count,
                include=["metadatas"]
            )
            sources = set()
            if results and results.get("metadatas"):
                for metadata in results["metadatas"]:
                    if metadata and "source_path" in metadata:
                        sources.add(metadata["source_path"])
            
            return {
                "total_chunks": count,
                "unique_documents": len(sources),
                "sources": sorted(list(sources))
            }
        
        return {
            "total_chunks": 0,
            "unique_documents": 0,
            "sources": []
        }


def get_vectordb(
    persist_directory: Optional[Path] = None,
    collection_name: Optional[str] = None
) -> VectorDB:
    """
    Get a VectorDB instance.
    
    Args:
        persist_directory: Optional persist directory override
        collection_name: Optional collection name override
        
    Returns:
        VectorDB instance
    """
    return VectorDB(
        persist_directory=persist_directory,
        collection_name=collection_name
    )

