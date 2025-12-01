"""
Comparison functions for RAG vs plain ChatGPT answers.

This module provides two functions:
1. answer_with_rag() - Uses course PDFs via RAG
2. answer_with_chatgpt_only() - Direct ChatGPT without any course context
"""

from typing import Dict, Any
import logging
from openai import OpenAI

from src.config import config
from src.vectordb import get_vectordb
from src.retriever import get_retriever
from src.llm import get_llm
from src.rag_chain import create_rag_chain
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

# Plain ChatGPT system prompt (no RAG, no course context)
CHATGPT_SYSTEM_PROMPT = """You are ChatGPT, a helpful general-purpose teaching assistant. Answer using only your own knowledge; do not assume access to any course PDFs or specific course materials. Provide general educational guidance based on common practices."""


def answer_with_rag(question: str) -> Dict[str, Any]:
    """
    Answer using RAG: Retrieves relevant chunks from course PDFs and generates answer.
    
    This is the full RAG pipeline:
    1. Query vector database for relevant PDF chunks
    2. Construct prompt with retrieved context
    3. Send to OpenAI with context
    4. Return answer with citations
    
    Args:
        question: User's question
        
    Returns:
        Dictionary with:
        - answer: Generated answer text
        - sources: Retrieved document chunks
        - citations: Formatted citations
        - num_sources: Number of sources used
    """
    logger.info(f"RAG answer for: {question[:100]}...")
    
    try:
        # Initialize RAG components
        vectordb = get_vectordb()
        llm = get_llm()
        retriever = get_retriever(vectordb)
        rag_chain = create_rag_chain(retriever, llm)
        
        # Query the RAG system
        result = rag_chain.query(question, return_sources=True)
        
        return result
        
    except Exception as e:
        logger.error(f"RAG answer failed: {e}")
        return {
            "answer": f"Error generating RAG answer: {str(e)}",
            "sources": [],
            "citations": [],
            "num_sources": 0
        }


def answer_with_chatgpt_only(question: str) -> str:
    """
    Answer using plain ChatGPT without RAG - no course PDFs, no retrieval.
    
    This sends the question directly to OpenAI's ChatGPT model
    without any course context or retrieved documents.
    
    Args:
        question: User's question
        
    Returns:
        Plain ChatGPT answer as string
    """
    logger.info(f"Plain ChatGPT answer for: {question[:100]}...")
    
    # Check if OpenAI API key is available
    if not config.openai_api_key:
        return "Error: OpenAI API key not configured. Set OPENAI_API_KEY in .env file."
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=config.openai_api_key)
        
        # Construct messages (no retrieved context, just the question)
        messages = [
            {"role": "system", "content": CHATGPT_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        # Call OpenAI API directly
        response = client.chat.completions.create(
            model=config.openai_model,
            messages=messages,
            temperature=0.7,  # Slightly higher for more general answers
            max_tokens=500    # Shorter responses for comparison
        )
        
        answer = response.choices[0].message.content
        logger.info("Plain ChatGPT answer generated successfully")
        return answer
        
    except Exception as e:
        logger.error(f"ChatGPT-only answer failed: {e}")
        return f"Error generating ChatGPT answer: {str(e)}"


# Example questions for the comparison UI
EXAMPLE_QUESTIONS = [
    "What is the grading policy for Biology 101?",
    "What are the office hours for this course?",
    "What is the policy on late submissions?",
    "What topics are covered in the midterm exam?",
    "Is there a required textbook for this course?",
]

