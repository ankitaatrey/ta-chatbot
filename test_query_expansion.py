"""
Test script to verify query expansion is working and improving confidence scores.
"""

from src.vectordb import get_vectordb
from src.retriever import get_retriever
from src.rag_chain import enhance_query_for_retrieval

# Test queries
test_queries = [
    "What is functional programming?",
    "Explain lambda calculus",
    "What is a type system?",
    "How does the interpreter work?",
    "Tell me about Scala",
]

print("🧪 Testing Query Expansion")
print("=" * 70)

for query in test_queries:
    enhanced = enhance_query_for_retrieval(query)
    print(f"\n📝 Original:  {query}")
    print(f"✨ Enhanced:  {enhanced}")
    print("-" * 70)

print("\n\n🔍 Testing Retrieval with Query Expansion")
print("=" * 70)

vdb = get_vectordb()
retriever = get_retriever(vdb, top_k=4, use_mmr=False)

# Test with and without expansion
test_query = "What is functional programming?"

print(f"\nQuery: '{test_query}'")
print("=" * 70)

# Without expansion
print("\n📊 WITHOUT EXPANSION:")
results_original = retriever.retrieve(test_query)
scores_original = [r['score'] for r in results_original]
avg_original = sum(scores_original) / len(scores_original) if scores_original else 0

for i, r in enumerate(results_original, 1):
    ft = r['metadata'].get('file_type', '?')
    source = r['metadata'].get('source', '?')
    score = r['score']
    emoji = '📄' if ft == 'pdf' else '🎬' if ft == 'srt' else '📝'
    print(f"{i}. {emoji} {ft.upper()} - {source[:30]:30s} - Score: {score:.3f}")

print(f"\n   Average Confidence: {avg_original*100:.1f}% (█{'█'*int(avg_original*10)}{'░'*(10-int(avg_original*10))})")

# With expansion
print("\n✨ WITH EXPANSION:")
enhanced_query = enhance_query_for_retrieval(test_query)
results_enhanced = retriever.retrieve(enhanced_query)
scores_enhanced = [r['score'] for r in results_enhanced]
avg_enhanced = sum(scores_enhanced) / len(scores_enhanced) if scores_enhanced else 0

for i, r in enumerate(results_enhanced, 1):
    ft = r['metadata'].get('file_type', '?')
    source = r['metadata'].get('source', '?')
    score = r['score']
    emoji = '📄' if ft == 'pdf' else '🎬' if ft == 'srt' else '📝'
    print(f"{i}. {emoji} {ft.upper()} - {source[:30]:30s} - Score: {score:.3f}")

print(f"\n   Average Confidence: {avg_enhanced*100:.1f}% (█{'█'*int(avg_enhanced*10)}{'░'*(10-int(avg_enhanced*10))})")

# Show improvement
improvement = (avg_enhanced - avg_original) * 100
print("\n" + "=" * 70)
print(f"📈 IMPROVEMENT: {improvement:+.1f} percentage points")
if improvement > 0:
    print(f"✅ Query expansion is working! Confidence boosted from {avg_original*100:.1f}% to {avg_enhanced*100:.1f}%")
else:
    print(f"⚠️ No improvement detected. Query might not match expansion dictionary.")
print("=" * 70)

