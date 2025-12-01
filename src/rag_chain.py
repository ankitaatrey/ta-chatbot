"""
RAG chain orchestrating retrieval and generation.

This is the core of the RAG (Retrieval-Augmented Generation) system:
1. Takes a user question
2. Retrieves relevant document chunks from vector database
3. Formats them into a prompt with instructions
4. Sends to LLM for answer generation
5. Extracts and formats citations
6. Returns answer with sources

The key insight of RAG: Instead of relying on LLM's internal knowledge
(which can hallucinate), we provide it with retrieved documents as context
and instruct it to ONLY use those documents.
"""

from typing import Dict, Any, List, Optional
import logging
import re
import time

from src.retriever import Retriever
from src.llm import LLM
from src.config import config
from src.utils.citations import create_context_block, merge_citations, format_citations_list
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# System prompt for the TA chatbot (GROUNDED mode - with course PDFs)
# This sets the "role" and behavior expectations for the LLM
# Key requirements: cite sources, say "don't know" if uncertain, be concise
SYSTEM_PROMPT_GROUNDED = """You are a university Teaching Assistant chatbot. Answer using only the retrieved sources. If the answer is not in the sources, say you don't know. Quote key snippets and add citations like [Title, pp. x–y]. Be concise and precise."""

# System prompt for FALLBACK mode (no relevant course context found)
# This is used when retrieval finds nothing useful
SYSTEM_PROMPT_FALLBACK = """You are a teaching assistant. You did not find any useful information in the course PDFs related to this question. 

Answer using your general knowledge, but you MUST start your response with a clear disclaimer:

"⚠️ Note: I couldn't find relevant information in the uploaded course materials, so this answer is based on general knowledge and may not reflect your specific course policies or content. Please verify with your instructor or course materials."

Then provide a helpful answer based on general educational knowledge. Be concise and helpful."""

# System prompt for CHITCHAT mode (casual conversation)
# This is used when user sends greetings, farewells, thanks, or casual queries
SYSTEM_PROMPT_CHITCHAT = """You are a friendly and helpful university Teaching Assistant. The student is having a casual conversation with you (greeting, farewell, or thanks).

Respond warmly and naturally, and gently guide them toward asking questions about their course materials if appropriate.

Examples:
- "Hello! I'm your course assistant. How can I help you with your course materials today?"
- "You're welcome! Feel free to ask if you have any questions about the course."
- "Goodbye! Good luck with your studies!"

Be concise, friendly, and professional."""


# Chitchat detection patterns (greetings, farewells, thanks, casual)
CHITCHAT_PATTERNS = [
    # Greetings
    r'^\s*(hi|hello|hey|sup|yo|good\s+morning|good\s+evening|good\s+afternoon|greetings)\s*[!.?]*\s*$',
    r'^\s*(hi|hello|hey)\s+(there|bot|assistant|ta)\s*[!.?]*\s*$',
    
    # Farewells
    r'^\s*(bye|goodbye|see\s+you|see\s+ya|later|take\s+care|cya)\s*[!.?]*\s*$',
    
    # Thanks
    r'^\s*(thanks?|thank\s+you|thx|ty|appreciate\s+it)\s*[!.?]*\s*$',
    
    # Casual questions
    r'^\s*(how\s+are\s+you|what\'?s\s+up|how\'?s\s+it\s+going|how\s+are\s+things)\s*[?!.]*\s*$',
]


def is_chitchat(query: str) -> bool:
    """
    Detect if a query is casual chitchat (greeting, farewell, thanks, etc.).
    
    Uses hybrid approach:
    1. Pattern matching for common phrases
    2. Heuristics for nonsense (very short, repetitive, etc.)
    
    Args:
        query: User's input query
        
    Returns:
        True if this appears to be chitchat, False otherwise
    """
    query_stripped = query.strip()
    query_lower = query_stripped.lower()
    
    # Empty or very short queries
    if len(query_stripped) == 0:
        return True
    
    # Pattern matching for greetings, farewells, thanks
    for pattern in CHITCHAT_PATTERNS:
        if re.match(pattern, query_lower, re.IGNORECASE):
            logger.info(f"Chitchat detected (pattern match): {query[:50]}")
            return True
    
    # Heuristic: Very short queries (1-3 words) that look casual
    words = query_stripped.split()
    if len(words) <= 3:
        # Check for single casual words
        casual_words = ['hi', 'hello', 'hey', 'bye', 'thanks', 'thx', 'ty', 'sup', 'yo']
        if words[0].lower() in casual_words:
            logger.info(f"Chitchat detected (short casual): {query[:50]}")
            return True
    
    # Heuristic: Repetitive characters (likely nonsense)
    # e.g., "aaaaaaa", "hahahaha"
    if len(query_stripped) > 5 and len(set(query_lower.replace(' ', ''))) <= 3:
        logger.info(f"Chitchat detected (repetitive): {query[:50]}")
        return True
    
    # Heuristic: Mostly symbols or numbers (gibberish)
    alphanumeric = sum(c.isalnum() for c in query_stripped)
    if len(query_stripped) > 0 and alphanumeric / len(query_stripped) < 0.5:
        logger.info(f"Chitchat detected (gibberish): {query[:50]}")
        return True
    
    # Not detected as chitchat
    return False


def enhance_query_for_retrieval(query: str) -> str:
    """
    Enhance query with related terms and synonyms for better retrieval.
    
    This bridges the vocabulary gap between user questions and document language.
    For example, "What is functional programming?" becomes 
    "functional programming FP paradigm lambda calculus pure functions immutable"
    
    Args:
        query: Original user query
        
    Returns:
        Enhanced query with additional search terms
    """
    query_lower = query.lower()
    
    # Define topic-specific expansions
    # Format: "key phrase": "key phrase + expansion terms"
    expansions = {
        # Functional programming concepts
        "functional programming": "functional programming FP paradigm lambda calculus pure functions immutable first-class functions higher-order",
        " fp ": " functional programming FP paradigm lambda calculus pure functions immutable",  # Handle abbreviation (with spaces to avoid matching "helpful")
        "lambda calculus": "lambda calculus anonymous function closure abstraction application",
        "anonymous function": "anonymous function lambda function closure",
        "pure function": "pure function side effect deterministic referential transparency",
        "immutability": "immutability immutable persistent data structure",
        "higher-order": "higher-order function map reduce filter fold",
        
        # Type systems
        "type system": "type system type checking static typing dynamic typing type inference",
        "type checking": "type checking type inference static analysis type safety",
        "type inference": "type inference Hindley-Milner algorithm W unification",
        
        # Programming language concepts
        "scala": "scala JVM functional object-oriented",
        "miniscala": "miniscala scala subset interpreter semantics",
        "syntax": "syntax grammar abstract syntax tree AST parser",
        "semantics": "semantics operational denotational evaluation",
        
        # Evaluation and execution
        "evaluation": "evaluation reduction substitution beta reduction",
        "interpreter": "interpreter evaluation execution abstract machine",
        "abstract machine": "abstract machine operational semantics small-step big-step",
        
        # Course-specific
        "lecture": "lecture video transcript course material",
        "assignment": "assignment homework exercise problem set",
        "grading": "grading policy rubric evaluation criteria",
    }
    
    # Check for matching key phrases and expand
    for key_phrase, expansion in expansions.items():
        # Handle different matching strategies
        if key_phrase.startswith(' ') and key_phrase.endswith(' '):
            # Word boundary matching (for abbreviations like " fp ")
            # Check if surrounded by word boundaries
            pattern = r'\b' + key_phrase.strip() + r'\b'
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info(f"Query expansion: '{query}' → adding terms from '{key_phrase.strip()}'")
                return f"{query} {expansion}"
        else:
            # Regular substring matching
            if key_phrase in query_lower:
                logger.info(f"Query expansion: '{query}' → adding terms from '{key_phrase}'")
                # Add expansion terms (but keep original query intact)
                return f"{query} {expansion}"
    
    # If no specific expansion found, return original
    return query


def create_rag_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Create the RAG prompt with question and context.
    
    This is the "user message" that gets sent to the LLM.
    Structure:
    1. The question (what the user asked)
    2. Retrieved context (documents that might contain the answer)
    3. Explicit instructions (how to format the answer)
    
    The instructions are crucial - they tell the LLM:
    - Only use provided context (no hallucination)
    - Add citations (grounding)
    - Say "don't know" if uncertain (honesty)
    - Be concise (usability)
    
    Args:
        question: User's question
        context_chunks: Retrieved context chunks with metadata (title, pages, text)
        
    Returns:
        Formatted prompt string ready for LLM
    """
    # Convert chunks to a readable format with [1], [2], etc. labels
    context_block = create_context_block(context_chunks)
    
    # Structure: Question → Context → Instructions
    # This format works well with most LLMs (GPT, Llama, etc.)
    prompt = f"""QUESTION:
{question}

TOP CONTEXT (ranked):
{context_block}

INSTRUCTIONS:
- Use only the provided context.
- When stating a fact, add a citation like [Title, pp. x–y].
- If context is insufficient, answer: "I don't know based on the provided materials."
- Start with a one-sentence direct answer, then briefly justify with 1–3 quotes."""
    
    return prompt


class RAGChain:
    """RAG pipeline orchestrating retrieval and generation."""
    
    def __init__(self, retriever: Retriever, llm: LLM):
        """
        Initialize the RAG chain.
        
        Args:
            retriever: Retriever instance
            llm: LLM instance
        """
        self.retriever = retriever
        self.llm = llm
    
    def query(
        self,
        question: str,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Query the RAG system - this is the main entry point.
        
        RAG Pipeline with Query Enhancement, Chitchat Detection and Fallback Support:
        0. DETECT CHITCHAT: Check if this is casual conversation (skip retrieval if yes)
        1. ENHANCE QUERY: Add related terms and synonyms for better retrieval
        2. RETRIEVE: Find relevant document chunks using vector similarity
        3. EVALUATE: Check if retrieved chunks meet quality threshold
        4. DECIDE: Choose between grounded mode (with context) or fallback mode (general knowledge)
        5. PROMPT: Format appropriate prompt based on mode
        6. GENERATE: Send to LLM to create answer
        7. CITE: Extract and format citations (only in grounded mode)
        8. RETURN: Package everything for the UI with mode indicator
        
        Args:
            question: User's question (e.g., "What is the grading policy?")
            return_sources: Whether to return full source documents (True for UI display)
            
        Returns:
            Dictionary containing:
            - answer: Generated text answer
            - sources: Retrieved document chunks (if return_sources=True)
            - citations: Formatted citation objects
            - mode: "grounded", "fallback", or "chitchat"
            - metadata: Retrieval scores, backend info, etc.
        """
        logger.info(f"Processing query: {question[:100]}...")
        
        # Start overall timing
        start_time = time.time()
        retrieval_time = 0.0
        generation_time = 0.0
        
        # ===== STEP 0: DETECT CHITCHAT =====
        # Check if this is casual conversation before doing expensive retrieval
        if is_chitchat(question):
            logger.info("Chitchat detected - skipping retrieval and using direct LLM response")
            
            # Use chitchat system prompt (friendly, warm, brief)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_CHITCHAT},
                {"role": "user", "content": question}
            ]
            
            try:
                gen_start = time.time()
                answer = self.llm.generate(messages, stream=False)
                generation_time = time.time() - gen_start
                logger.info("Generated chitchat response")
            except Exception as e:
                logger.error(f"Chitchat generation failed: {e}")
                answer = "Hello! How can I help you with your course materials today?"
                generation_time = time.time() - gen_start
            
            total_time = time.time() - start_time
            
            # Return with chitchat mode indicator
            return {
                "answer": answer,
                "sources": [],  # No sources for chitchat
                "citations": [],  # No citations for chitchat
                "citations_text": "",
                "num_sources": 0,
                "mode": "chitchat",  # KEY: Indicates this is casual conversation
                "metadata": {
                    "retrieved_chunks": 0,
                    "backend": self.llm.get_backend_info(),
                    "scores": [],
                    "chitchat": True,
                    "timing": {
                        "total": total_time,
                        "retrieval": 0.0,
                        "generation": generation_time
                    }
                }
            }
        
        # ===== STEP 1: QUERY ENHANCEMENT =====
        # Enhance query with related terms for better retrieval
        # This bridges vocabulary gap between user language and document language
        enhanced_query = enhance_query_for_retrieval(question)
        
        # ===== STEP 2: RETRIEVAL =====
        # Query vector database to find relevant chunks
        # This uses embedding similarity + optional MMR reranking
        retrieval_start = time.time()
        retrieved_chunks = self.retriever.retrieve(enhanced_query)
        retrieval_time = time.time() - retrieval_start
        
        # ===== STEP 3: EVALUATE RETRIEVAL QUALITY =====
        # Determine if we have good enough context to answer from course materials
        # Fallback conditions:
        # 1. No chunks retrieved at all, OR
        # 2. All chunks have scores below the threshold
        use_fallback_mode = False
        
        if not retrieved_chunks:
            logger.warning("No documents retrieved - entering fallback mode")
            use_fallback_mode = True
        else:
            # Check if any chunks meet the score threshold
            scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
            max_score = max(scores) if scores else 0.0
            
            # Use the configured threshold from config
            threshold = config.score_threshold
            
            if max_score < threshold:
                logger.warning(
                    f"All retrieval scores below threshold ({max_score:.3f} < {threshold:.3f}) - entering fallback mode"
                )
                use_fallback_mode = True
            else:
                logger.info(
                    f"RAG mode: grounded (found {len(retrieved_chunks)} chunks, max score: {max_score:.3f})"
                )
        
        # ===== STEP 4: GENERATE ANSWER =====
        # Two different paths based on whether we have good context
        
        if use_fallback_mode:
            # ===== FALLBACK MODE: No good context =====
            # Don't use retrieved chunks, just ask the LLM directly
            # But with a prompt that requires it to add a disclaimer
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_FALLBACK},
                {"role": "user", "content": question}  # Just the question, no context
            ]
            
            try:
                gen_start = time.time()
                answer = self.llm.generate(messages, stream=False)
                generation_time = time.time() - gen_start
                logger.info("RAG mode: fallback (using general knowledge)")
            except Exception as e:
                logger.error(f"Fallback generation failed: {e}")
                answer = f"Error generating answer: {e}"
                generation_time = time.time() - gen_start if 'gen_start' in locals() else 0.0
            
            total_time = time.time() - start_time
            
            # Return with fallback indicator
            return {
                "answer": answer,
                "sources": [],  # No sources in fallback mode
                "citations": [],  # No citations in fallback mode
                "citations_text": "",
                "num_sources": 0,
                "mode": "fallback",  # KEY: Indicates this is not grounded
                "metadata": {
                    "retrieved_chunks": len(retrieved_chunks) if retrieved_chunks else 0,
                    "backend": self.llm.get_backend_info(),
                    "scores": [chunk.get("score", 0.0) for chunk in retrieved_chunks] if retrieved_chunks else [],
                    "fallback_reason": "no_chunks" if not retrieved_chunks else "low_scores",
                    "timing": {
                        "total": total_time,
                        "retrieval": retrieval_time,
                        "generation": generation_time
                    }
                }
            }
        
        else:
            # ===== GROUNDED MODE: Normal RAG with good context =====
            
            # Format retrieved chunks into a structured prompt
            prompt = create_rag_prompt(question, retrieved_chunks)
            
            # Send to LLM with grounded system prompt
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_GROUNDED},
                {"role": "user", "content": prompt}
            ]
            
            try:
                gen_start = time.time()
                answer = self.llm.generate(messages, stream=False)
                generation_time = time.time() - gen_start
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                answer = f"Error generating answer: {e}"
                generation_time = time.time() - gen_start if 'gen_start' in locals() else 0.0
            
            total_time = time.time() - start_time
            
            # Extract citations from retrieved chunks
            citations = merge_citations(retrieved_chunks)
            
            # Calculate average confidence score
            scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            # Return with grounded indicator
            response = {
                "answer": answer,
                "sources": retrieved_chunks if return_sources else [],
                "citations": citations,
                "citations_text": format_citations_list(citations),
                "num_sources": len(retrieved_chunks),
                "mode": "grounded",  # KEY: Indicates this IS grounded in course docs
                "metadata": {
                    "retrieved_chunks": len(retrieved_chunks),
                    "backend": self.llm.get_backend_info(),
                    "scores": scores,
                    "avg_score": avg_score,
                    "timing": {
                        "total": total_time,
                        "retrieval": retrieval_time,
                        "generation": generation_time
                    }
                }
            }
            
            logger.info(f"Generated grounded answer with {len(citations)} citations")
            return response
    
    def query_stream(
        self,
        question: str
    ) -> tuple[str, List[Dict[str, Any]], List[Any]]:
        """
        Query with streaming support (simplified for now).
        
        Args:
            question: User's question
            
        Returns:
            Tuple of (answer, sources, citations)
        """
        # For now, just use regular query
        result = self.query(question, return_sources=True)
        return result["answer"], result["sources"], result["citations"]


def create_rag_chain(retriever: Retriever, llm: LLM) -> RAGChain:
    """
    Create a RAG chain instance.
    
    Args:
        retriever: Retriever instance
        llm: LLM instance
        
    Returns:
        RAGChain instance
    """
    return RAGChain(retriever, llm)
