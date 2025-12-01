# RAG Fallback Mode - Quick Guide

## 🎯 What Changed?

Before, when no relevant PDFs were found:
```
❌ "I don't have any relevant information..."
```

Now, with fallback mode:
```
✅ "⚠️ Note: I couldn't find relevant information in the uploaded course materials, 
   so this answer is based on general knowledge..."
   
   [Helpful general answer follows]
```

---

## 🔀 Decision Flow

```
User Question
     ↓
Retrieve from Vector DB
     ↓
     ├─→ Found chunks with score ≥ 0.3?
     │        ↓ YES
     │   ╔═══════════════════════╗
     │   ║  GROUNDED MODE        ║
     │   ║  • Use PDF context    ║
     │   ║  • Add citations      ║
     │   ║  • Green border       ║
     │   ║  • Show sources       ║
     │   ╚═══════════════════════╝
     │
     └─→ NO chunks OR all scores < 0.3
              ↓
         ╔═══════════════════════╗
         ║  FALLBACK MODE        ║
         ║  • General knowledge  ║
         ║  • No citations       ║
         ║  • Orange border      ║
         ║  • Warning banner     ║
         ╚═══════════════════════╝
```

---

## 📊 Visual Comparison

### Grounded Mode (Normal RAG)
```
┌─────────────────────────────────────┐
│ 🎓 RAG TA Bot (With Course PDFs)   │ GREEN BORDER
├─────────────────────────────────────┤
│                                     │
│ The grading policy states that...  │
│ [Syllabus, pp. 3-4]                 │
│                                     │
│ Late submissions receive a 10%...  │
│ [Syllabus, pp. 5-6]                 │
│                                     │
└─────────────────────────────────────┘
├─────────────────────────────────────┤
│ 📚 Sources (2)                      │
│   ▸ syllabus.pdf (pp. 3-6)          │
│     Score: 0.85                     │
└─────────────────────────────────────┘
```

### Fallback Mode (General Knowledge)
```
┌─────────────────────────────────────┐
│ 🎓 RAG TA Bot (With Course PDFs)   │ ORANGE BORDER
├─────────────────────────────────────┤
│ ⚠️  No Supporting Course Documents  │
│     Found                           │
│                                     │
│ This answer is NOT grounded in your │
│ PDFs. Please verify with instructor.│
├─────────────────────────────────────┤
│                                     │
│ ⚠️ Note: I couldn't find relevant   │
│ information in the course materials.│
│                                     │
│ Generally, quantum computing uses...│
│ [Answer continues with general info]│
│                                     │
└─────────────────────────────────────┘
├─────────────────────────────────────┤
│ 📝 No citations available           │
└─────────────────────────────────────┘
```

---

## 🧪 How to Test

### Test 1: Grounded Mode
```bash
# 1. Make sure you have PDFs ingested
python -m src.ingestion --data_dir data/pdfs

# 2. Run the app
streamlit run src/app.py

# 3. Ask a question from your PDFs
"What is the grading policy?"

# ✅ Expected: Green border, citations, sources
```

### Test 2: Fallback Mode
```bash
# 1. Run the app
streamlit run src/app.py

# 2. Ask a question NOT in your PDFs
"What is quantum computing?"

# ⚠️ Expected: Orange border, warning banner, no citations
```

### Test 3: Compare Side-by-Side
```bash
# 1. Run comparison app
streamlit run src/compare_app.py

# 2. Ask both types of questions
# - Course-specific → RAG will be grounded (green)
# - Off-topic → RAG will be fallback (orange)
```

---

## ⚙️ Tuning Fallback Sensitivity

Edit `.env`:

```bash
# Strict mode (more fallback triggers)
SCORE_THRESHOLD=0.5

# Permissive mode (fewer fallback triggers)
SCORE_THRESHOLD=0.2

# Default (balanced)
SCORE_THRESHOLD=0.3
```

**Higher threshold** = More questions trigger fallback  
**Lower threshold** = Fewer questions trigger fallback

---

## 📁 Key Code Locations

| What | Where | Lines |
|------|-------|-------|
| Fallback decision logic | `src/rag_chain.py` | 138-164 |
| Grounded mode prompt | `src/rag_chain.py` | 202-239 |
| Fallback mode prompt | `src/rag_chain.py` | 169-200 |
| UI warning banner (main app) | `src/app.py` | 278-284, 375-380 |
| UI warning banner (comparison) | `src/compare_app.py` | 97-102 |
| Border color styling | `src/compare_app.py` | 105-114 |

---

## 🔍 Debugging

Check logs to see which mode was used:

```bash
# Grounded mode
INFO: RAG mode: grounded (found 4 chunks, max score: 0.852)

# Fallback mode - no chunks
WARNING: No documents retrieved - entering fallback mode

# Fallback mode - low scores
WARNING: All retrieval scores below threshold (0.180 < 0.300) - entering fallback mode
```

Enable score display in UI:
- In main app: Check "Show retrieval scores" in sidebar
- In comparison: Scores always shown in source expander

---

## ✅ Success Criteria

You'll know it's working when:

1. ✅ Questions about course content → Green border + citations
2. ✅ Off-topic questions → Orange border + warning
3. ✅ Fallback answers start with disclaimer
4. ✅ No citations shown in fallback mode
5. ✅ Logs show correct mode selection

---

## 🚀 Quick Start

```bash
# 1. Your PDFs should already be ingested
ls data/pdfs/  # Check they're here

# 2. Run the main app
streamlit run src/app.py

# 3. Try both:
# - "What is the grading policy?" → Should be grounded (green)
# - "What is quantum computing?" → Should be fallback (orange)
```

That's it! Your RAG system now handles both grounded and fallback scenarios gracefully. 🎉

