"""Evaluation harness for the TA chatbot."""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.vectordb import get_vectordb
from src.retriever import get_retriever
from src.llm import get_llm
from src.rag_chain import create_rag_chain
from src.utils.logging_setup import setup_logging, get_logger

logger = get_logger(__name__)


def load_questions(filepath: Path) -> List[Dict[str, Any]]:
    """
    Load evaluation questions from JSONL file.
    
    Args:
        filepath: Path to questions.jsonl
        
    Returns:
        List of question dictionaries
    """
    questions = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def check_retrieval_coverage(
    question: str,
    retrieved_sources: List[Dict[str, Any]],
    expected_source: str
) -> bool:
    """
    Check if the expected source was retrieved.
    
    Args:
        question: Question text
        retrieved_sources: List of retrieved sources
        expected_source: Expected source filename (without extension)
        
    Returns:
        True if expected source was retrieved
    """
    for source in retrieved_sources:
        source_path = source.get("metadata", {}).get("source_path", "")
        if expected_source in source_path:
            return True
    return False


def calculate_keyword_coverage(
    answer: str,
    expected_keywords: List[str]
) -> float:
    """
    Calculate the percentage of expected keywords present in the answer.
    
    Args:
        answer: Generated answer
        expected_keywords: List of expected keywords
        
    Returns:
        Coverage percentage (0.0 to 1.0)
    """
    if not expected_keywords:
        return 1.0
    
    answer_lower = answer.lower()
    matches = 0
    
    for keyword in expected_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in answer_lower:
            matches += 1
    
    return matches / len(expected_keywords)


def check_citation_presence(answer: str) -> bool:
    """
    Check if the answer contains citation markers.
    
    Args:
        answer: Generated answer
        
    Returns:
        True if citations are present
    """
    # Look for citation patterns like [Title, pp. 1-2] or [Title, p. 1]
    citation_pattern = r'\[([^\]]+?),\s*pp?\.\s*\d+(?:[-–]\d+)?\]'
    return bool(re.search(citation_pattern, answer))


def run_evaluation(
    questions: List[Dict[str, Any]],
    rag_chain,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run evaluation on all questions.
    
    Args:
        questions: List of question dictionaries
        rag_chain: RAGChain instance
        verbose: Whether to print detailed results
        
    Returns:
        Evaluation results dictionary
    """
    results = {
        "total_questions": len(questions),
        "retrieval_coverage": 0,
        "avg_keyword_coverage": 0.0,
        "citation_presence": 0,
        "question_results": []
    }
    
    total_keyword_coverage = 0.0
    
    for i, q in enumerate(questions, 1):
        question = q["question"]
        expected_keywords = q.get("expected_keywords", [])
        expected_source = q.get("expected_source", "")
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Question {i}/{len(questions)}")
            print(f"{'='*60}")
            print(f"Q: {question}")
        
        try:
            # Query the RAG system
            result = rag_chain.query(question)
            
            answer = result["answer"]
            sources = result["sources"]
            
            # Check retrieval coverage
            has_expected_source = check_retrieval_coverage(
                question, sources, expected_source
            )
            if has_expected_source:
                results["retrieval_coverage"] += 1
            
            # Check keyword coverage
            keyword_coverage = calculate_keyword_coverage(answer, expected_keywords)
            total_keyword_coverage += keyword_coverage
            
            # Check citation presence
            has_citations = check_citation_presence(answer)
            if has_citations:
                results["citation_presence"] += 1
            
            # Store individual result
            question_result = {
                "question": question,
                "answer": answer,
                "num_sources": len(sources),
                "expected_source_retrieved": has_expected_source,
                "keyword_coverage": keyword_coverage,
                "has_citations": has_citations
            }
            results["question_results"].append(question_result)
            
            if verbose:
                print(f"\nA: {answer}\n")
                print(f"Sources retrieved: {len(sources)}")
                print(f"Expected source retrieved: {'✓' if has_expected_source else '✗'}")
                print(f"Keyword coverage: {keyword_coverage:.1%}")
                print(f"Has citations: {'✓' if has_citations else '✗'}")
        
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            if verbose:
                print(f"\nError: {e}")
    
    # Calculate averages
    results["retrieval_coverage_pct"] = results["retrieval_coverage"] / results["total_questions"]
    results["avg_keyword_coverage"] = total_keyword_coverage / results["total_questions"]
    results["citation_presence_pct"] = results["citation_presence"] / results["total_questions"]
    
    return results


def print_summary(results: Dict[str, Any]):
    """Print evaluation summary."""
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total Questions: {results['total_questions']}")
    print(f"Retrieval Coverage: {results['retrieval_coverage_pct']:.1%} "
          f"({results['retrieval_coverage']}/{results['total_questions']})")
    print(f"Avg Keyword Coverage: {results['avg_keyword_coverage']:.1%}")
    print(f"Citation Presence: {results['citation_presence_pct']:.1%} "
          f"({results['citation_presence']}/{results['total_questions']})")
    print("="*60)


def main():
    """Main evaluation entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate the TA chatbot RAG system"
    )
    parser.add_argument(
        "--questions",
        type=str,
        default="eval/questions.jsonl",
        help="Path to questions JSONL file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file for detailed results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results for each question"
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Load questions
    questions_path = Path(args.questions)
    if not questions_path.exists():
        print(f"Error: Questions file not found: {questions_path}")
        return 1
    
    questions = load_questions(questions_path)
    print(f"Loaded {len(questions)} evaluation questions")
    
    # Initialize components
    print("Initializing RAG components...")
    vectordb = get_vectordb()
    
    # Check if database has content
    stats = vectordb.get_stats()
    if stats["total_chunks"] == 0:
        print("Error: Vector database is empty. Please ingest documents first.")
        print("Run: python -m src.ingestion --data_dir data/pdfs")
        return 1
    
    print(f"Database has {stats['total_chunks']} chunks from {stats['unique_documents']} documents")
    
    llm = get_llm()
    retriever = get_retriever(vectordb)
    rag_chain = create_rag_chain(retriever, llm)
    
    # Run evaluation
    print("\nRunning evaluation...")
    results = run_evaluation(questions, rag_chain, verbose=args.verbose)
    
    # Print summary
    print_summary(results)
    
    # Save detailed results if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())

