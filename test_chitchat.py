"""
Quick test script for chitchat detection.

Run this to verify that chitchat detection is working correctly before testing in the UI.
"""

from src.rag_chain import is_chitchat

# Test cases
test_queries = [
    # Should be detected as chitchat (True)
    ("hi", True),
    ("hello", True),
    ("Hello!", True),
    ("hey there", True),
    ("good morning", True),
    ("bye", True),
    ("goodbye", True),
    ("thanks", True),
    ("thank you", True),
    ("thx", True),
    ("how are you", True),
    ("what's up", True),
    ("aaaaaaa", True),  # Repetitive gibberish
    ("!!!", True),  # Symbols
    
    # Should NOT be detected as chitchat (False)
    ("What is functional programming?", False),
    ("Explain lambda calculus", False),
    ("What is the grading policy?", False),
    ("Tell me about type systems", False),
    ("How do I solve this problem?", False),
    ("What are the prerequisites?", False),
]

def run_tests():
    """Run all test cases and report results."""
    print("🧪 Testing Chitchat Detection")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query, expected in test_queries:
        result = is_chitchat(query)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | Query: '{query}' | Expected: {expected} | Got: {result}")
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Chitchat detection is working correctly.")
    else:
        print("⚠️ Some tests failed. Review the detection logic.")

if __name__ == "__main__":
    run_tests()

