"""Advanced retrieval with MMR and hybrid search support."""

from typing import List, Dict, Any, Optional
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.config import config
from src.vectordb import VectorDB
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

# Optional BM25 support
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not available. Hybrid search disabled.")


class Retriever:
    """Advanced retriever with MMR and optional hybrid search."""
    
    def __init__(
        self,
        vectordb: VectorDB,
        top_k: int = 4,
        score_threshold: float = 0.3,
        use_mmr: bool = True,
        mmr_diversity: float = 0.3,
        use_hybrid: bool = False
    ):
        """
        Initialize the retriever.
        
        Args:
            vectordb: VectorDB instance
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            use_mmr: Whether to use MMR reranking
            mmr_diversity: MMR diversity parameter (0=relevance, 1=diversity)
            use_hybrid: Whether to use hybrid search (requires BM25)
        """
        self.vectordb = vectordb
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.use_mmr = use_mmr
        self.mmr_diversity = mmr_diversity
        self.use_hybrid = use_hybrid and BM25_AVAILABLE
        
        # BM25 index (built lazily)
        self.bm25_index = None
        self.bm25_documents = None
    
    def _build_bm25_index(self) -> None:
        """Build BM25 index from all documents in the database."""
        if not BM25_AVAILABLE:
            logger.warning("BM25 not available")
            return
        
        logger.info("Building BM25 index...")
        
        # Get all documents
        count = self.vectordb.count()
        if count == 0:
            logger.warning("No documents in database")
            return
        
        results = self.vectordb.collection.get(
            limit=count,
            include=["documents", "metadatas"]
        )
        
        if not results or not results.get("documents"):
            logger.warning("No documents retrieved")
            return
        
        # Tokenize documents
        documents = results["documents"]
        self.bm25_documents = results
        tokenized_docs = [doc.lower().split() for doc in documents]
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)
        logger.info(f"Built BM25 index with {len(documents)} documents")
    
    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Perform BM25 search.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of results with scores
        """
        if not self.bm25_index:
            self._build_bm25_index()
        
        if not self.bm25_index:
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "document": self.bm25_documents["documents"][idx],
                    "metadata": self.bm25_documents["metadatas"][idx],
                    "id": self.bm25_documents["ids"][idx],
                    "score": float(scores[idx]),
                    "source": "bm25"
                })
        
        return results
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of results with scores
        """
        # Query the vector database
        raw_results = self.vectordb.query(query, n_results=top_k)
        
        # Format results
        results = []
        if raw_results and raw_results.get("documents"):
            for i in range(len(raw_results["documents"][0])):
                # ChromaDB returns distances (lower is better)
                # Convert to similarity score (higher is better)
                distance = raw_results["distances"][0][i]
                similarity = 1.0 - distance  # For cosine distance
                
                results.append({
                    "document": raw_results["documents"][0][i],
                    "metadata": raw_results["metadatas"][0][i],
                    "id": raw_results["ids"][0][i],
                    "score": similarity,
                    "source": "vector"
                })
        
        return results
    
    def _hybrid_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (BM25 + vector).
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of results with combined scores
        """
        # Get results from both methods
        bm25_results = self._bm25_search(query, top_k * 2)
        vector_results = self._vector_search(query, top_k * 2)
        
        # Combine and rerank using reciprocal rank fusion
        combined_scores = {}
        
        # Add BM25 scores
        for rank, result in enumerate(bm25_results, 1):
            doc_id = result["id"]
            combined_scores[doc_id] = combined_scores.get(doc_id, 0) + 1.0 / (rank + 60)
        
        # Add vector scores
        for rank, result in enumerate(vector_results, 1):
            doc_id = result["id"]
            combined_scores[doc_id] = combined_scores.get(doc_id, 0) + 1.0 / (rank + 60)
        
        # Sort by combined score
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        
        # Build final results
        id_to_result = {}
        for result in vector_results + bm25_results:
            if result["id"] not in id_to_result:
                id_to_result[result["id"]] = result
        
        results = []
        for doc_id in sorted_ids[:top_k]:
            if doc_id in id_to_result:
                result = id_to_result[doc_id]
                result["score"] = combined_scores[doc_id]
                result["source"] = "hybrid"
                results.append(result)
        
        return results
    
    def _mmr_rerank(
        self,
        query_embedding: List[float],
        results: List[Dict[str, Any]],
        top_k: int,
        lambda_param: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using Maximal Marginal Relevance (MMR).
        
        MMR Algorithm Purpose:
        - Balances relevance to query with diversity of results
        - Avoids returning multiple similar/redundant documents
        - Useful when top results might all come from same source/section
        
        How it works:
        1. Start with most relevant document
        2. For each next document, score = λ * relevance - (1-λ) * max_similarity_to_selected
        3. Pick document with highest MMR score
        4. Repeat until we have top_k documents
        
        Args:
            query_embedding: Query embedding vector
            results: Initial results from vector search
            top_k: Number of results to return
            lambda_param: Balance between relevance and diversity
                         1.0 = only relevance (no diversity)
                         0.0 = only diversity (no relevance)
                         0.5 = equal balance (typical)
            
        Returns:
            Reranked results with better diversity
        """
        # If we don't have more results than needed, no reranking necessary
        if len(results) <= top_k:
            return results
        
        # STEP 1: Get embeddings for all candidate results
        # We need embeddings to calculate similarity between documents
        result_embeddings = []
        for result in results:
            # Re-embed documents (in production, these would be cached in DB)
            embedding = self.vectordb.embedder.embed_query(result["document"])
            result_embeddings.append(embedding)
        
        # Convert to numpy arrays for efficient similarity calculations
        result_embeddings = np.array(result_embeddings)  # Shape: (n_results, embedding_dim)
        query_embedding = np.array(query_embedding).reshape(1, -1)  # Shape: (1, embedding_dim)
        
        # STEP 2: Calculate relevance scores (similarity to query)
        # cosine_similarity returns values in [-1, 1], higher = more similar
        relevance_scores = cosine_similarity(query_embedding, result_embeddings)[0]
        
        # STEP 3: MMR greedy selection algorithm
        selected_indices = []  # Indices of documents we've selected
        remaining_indices = list(range(len(results)))  # Indices still available
        
        # Always select the most relevant document first (greedy start)
        best_idx = np.argmax(relevance_scores)
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
        
        # STEP 4: Iteratively select remaining documents using MMR
        while len(selected_indices) < top_k and remaining_indices:
            mmr_scores = []
            
            # Calculate MMR score for each remaining document
            for idx in remaining_indices:
                # Component 1: How relevant is this document to the query?
                relevance = relevance_scores[idx]
                
                # Component 2: How similar is this to already selected documents?
                # We want to PENALIZE documents similar to what we already have
                selected_embeddings = result_embeddings[selected_indices]
                current_embedding = result_embeddings[idx].reshape(1, -1)
                similarities = cosine_similarity(current_embedding, selected_embeddings)[0]
                max_similarity = np.max(similarities)  # Most similar to any selected doc
                
                # MMR Formula: λ * relevance - (1-λ) * max_similarity
                # High λ (e.g., 0.9): prioritize relevance
                # Low λ (e.g., 0.3): prioritize diversity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                mmr_scores.append(mmr_score)
            
            # Select document with highest MMR score
            best_mmr_idx = np.argmax(mmr_scores)
            selected_idx = remaining_indices[best_mmr_idx]
            selected_indices.append(selected_idx)
            remaining_indices.remove(selected_idx)
        
        # Return documents in the order they were selected by MMR
        return [results[i] for i in selected_indices]
    
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query text
            
        Returns:
            List of retrieved documents with metadata and scores
        """
        logger.info(f"Retrieving documents for query: {query[:100]}...")
        
        # Perform search
        if self.use_hybrid:
            results = self._hybrid_search(query, self.top_k * 2)
        else:
            results = self._vector_search(query, self.top_k * 2)
        
        # Apply MMR reranking if enabled
        if self.use_mmr and len(results) > self.top_k:
            query_embedding = self.vectordb.embedder.embed_query(query)
            lambda_param = 1.0 - self.mmr_diversity
            results = self._mmr_rerank(query_embedding, results, self.top_k, lambda_param)
        else:
            results = results[:self.top_k]
        
        # Filter by score threshold
        filtered_results = [r for r in results if r["score"] >= self.score_threshold]
        
        logger.info(f"Retrieved {len(filtered_results)} documents (filtered from {len(results)})")
        
        # Format for output
        formatted_results = []
        for result in filtered_results:
            formatted_results.append({
                "text": result["document"],
                "metadata": result["metadata"],
                "score": result["score"]
            })
        
        return formatted_results


def get_retriever(
    vectordb: VectorDB,
    top_k: Optional[int] = None,
    score_threshold: Optional[float] = None,
    use_mmr: Optional[bool] = None,
    mmr_diversity: Optional[float] = None
) -> Retriever:
    """
    Get a Retriever instance with configuration.
    
    Args:
        vectordb: VectorDB instance
        top_k: Override config top_k
        score_threshold: Override config threshold
        use_mmr: Override config MMR setting
        mmr_diversity: Override config MMR diversity
        
    Returns:
        Retriever instance
    """
    return Retriever(
        vectordb=vectordb,
        top_k=top_k or config.top_k,
        score_threshold=score_threshold or config.score_threshold,
        use_mmr=use_mmr if use_mmr is not None else config.use_mmr,
        mmr_diversity=mmr_diversity or config.mmr_diversity,
        use_hybrid=False  # Disabled by default
    )

