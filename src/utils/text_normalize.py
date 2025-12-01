"""Text normalization utilities."""

import re
from typing import Optional


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r'\n\n+', '\n\n', text)
    # Remove trailing/leading whitespace
    text = text.strip()
    return text


def clean_pdf_text(text: str) -> str:
    """
    Clean text extracted from PDF.
    
    Args:
        text: Raw PDF text
        
    Returns:
        Cleaned text
    """
    # Fix hyphenated words at line breaks
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    # Remove excessive whitespace
    text = normalize_whitespace(text)
    # Remove form feed characters
    text = text.replace('\f', '\n')
    # Remove zero-width characters
    text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
    return text


def extract_title_from_filename(filename: str) -> str:
    """
    Extract a readable title from a filename.
    
    Args:
        filename: File name (with or without extension)
        
    Returns:
        Human-readable title
    """
    # Remove extension
    name = filename.rsplit('.', 1)[0]
    # Replace underscores and hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    # Capitalize words
    name = ' '.join(word.capitalize() for word in name.split())
    return name


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].rstrip() + suffix


def remove_citations(text: str) -> str:
    """
    Remove citation markers from text.
    
    Args:
        text: Text potentially containing citations
        
    Returns:
        Text without citation markers
    """
    # Remove bracketed citations like [Title, pp. 1-2]
    text = re.sub(r'\[([^\]]+?),\s*pp?\.\s*\d+(?:[-–]\d+)?\]', '', text)
    return text.strip()


def detect_language(text: str) -> str:
    """
    Simple language detection (English vs other).
    
    Args:
        text: Input text
        
    Returns:
        Language code ('en' or 'other')
    """
    # Very simple: check for common English words
    english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for']
    text_lower = text.lower()
    matches = sum(1 for word in english_words if f' {word} ' in text_lower)
    return 'en' if matches >= 3 else 'other'

