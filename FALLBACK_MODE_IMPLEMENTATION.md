# RAG Fallback Mode Implementation

## Overview

The RAG system now supports a **fallback mode** that provides general knowledge-based answers when no relevant course documents are found, instead of simply saying "I don't know."

---

## ✅ What Was Implemented

### 1. **Two-Mode RAG System**

The RAG pipeline now operates in two distinct modes:

#### **Grounded Mode** (Default)
- **When**: Relevant course documents are found with scores above threshold
- **Behavior**: 
  - Uses retrieved PDF chunks as context
  - LLM answers strictly from course materials
  - Provides citations with page numbers
  - Sources are displayed in UI
- **System Prompt**: Instructs LLM to use only retrieved sources

#### **Fallback Mode** (New)
- **When**: 
  - No documents retrieved, OR
  - All retrieval scores below `SCORE_THRESHOLD` (default: 0.3)
- **Behavior**:
  - No course context provided to LLM
  - LLM uses general knowledge
  - Adds automatic disclaimer in answer
  - No citations shown
  - Clear warning banner in UI
- **System Prompt**: Instructs LLM to add disclaimer and answer from general knowledge

---

## 🔧 Implementation Details

### Modified Files

#### 1. **`src/rag_chain.py`** (Core Logic)

**Changes:**
- Split `SYSTEM_PROMPT` into two variants:
  - `SYSTEM_PROMPT_GROUNDED` - For normal RAG with context
  - `SYSTEM_PROMPT_FALLBACK` - For fallback mode with disclaimer
  
- Enhanced `query()` method with fallback detection:

```python
# Fallback Decision Logic (lines 138-164)
if not retrieved_chunks:
    # No chunks at all → fallback
    use_fallback_mode = True
else:
    # Check if any chunks meet the score threshold
    scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
    max_score = max(scores) if scores else 0.0
    threshold = config.score_threshold  # From .env (default: 0.3)
    
    if max_score < threshold:
        # All scores too low → fallback
        use_fallback_mode = True
```

- Two separate code paths:

**Grounded Mode** (lines 202-239):
```python
# Uses retrieved context
prompt = create_rag_prompt(question, retrieved_chunks)
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_GROUNDED},
    {"role": "user", "content": prompt}
]
# Returns: mode="grounded", includes sources and citations
```

**Fallback Mode** (lines 169-200):
```python
# No context, just the question
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_FALLBACK},
    {"role": "user", "content": question}  # No retrieved context!
]
# Returns: mode="fallback", empty sources and citations
```

- **Return Value**: All responses now include:
  - `"mode"`: `"grounded"` or `"fallback"`
  - `"metadata"` includes `"fallback_reason"` if applicable

**Logging:**
- Line 163: `logger.info("RAG mode: grounded (found N chunks, max score: X)")`
- Line 181: `logger.info("RAG mode: fallback (using general knowledge)")`

---

#### 2. **`src/app.py`** (Main Chatbot UI)

**Changes:**

- **`render_message()` function** (lines 271-319):
  - Added fallback warning banner display
  - Only shows sources in grounded mode
  - Shows "No citations available" message in fallback mode

```python
# Lines 278-284
if role == "assistant" and mode == "fallback":
    st.warning(
        "⚠️ **No Supporting Course Documents Found**\n\n"
        "This answer is based on general model knowledge..."
    )
```

- **Main response generation** (lines 363-426):
  - Extracts `mode` from RAG result
  - Shows fallback warning before answer
  - Saves mode in message history
  - Conditionally displays sources based on mode

```python
# Lines 372, 375-380
mode = result.get("mode", "grounded")

if mode == "fallback":
    st.warning("⚠️ **No Supporting Course Documents Found**...")
```

---

#### 3. **`src/compare_app.py`** (Comparison UI)

**Changes:**

- **`render_answer_panel()` function** (lines 82-158):
  - Added `mode` parameter
  - Shows fallback warning banner for fallback mode
  - Different border colors:
    - Green (#4CAF50) for grounded
    - Orange (#FFA726) for fallback
    - Blue (#2196F3) for plain ChatGPT
  - Conditionally shows sources/citations based on mode

```python
# Lines 97-102
if is_rag and mode == "fallback":
    st.warning("⚠️ **No Supporting Course Documents Found**...")

# Lines 106-114
if mode == "fallback":
    border_color = "#FFA726"  # Orange
    bg_color = "#FFF3E0"
else:
    border_color = "#4CAF50"  # Green
```

- **Main comparison logic** (lines 220-237):
  - Extracts mode from RAG result
  - Passes mode to render function
  - Updates metrics to show "Fallback Mode" vs "X Sources"

```python
# Lines 228, 236
mode = rag_result.get("mode", "grounded")
render_answer_panel(..., mode=mode)

# Lines 254-267
if mode == "grounded":
    st.metric("RAG TA Bot", f"{len(sources)} Sources", ...)
else:
    st.metric("RAG TA Bot", "Fallback Mode", delta="General knowledge", ...)
```

---

## 🎯 Fallback Trigger Conditions

Fallback mode is activated when **either** condition is true:

1. **Zero Chunks Retrieved**
   ```
   retrieved_chunks is empty
   → No documents in database match the query at all
   ```

2. **All Scores Below Threshold**
   ```
   max(chunk.score for chunk in retrieved_chunks) < SCORE_THRESHOLD
   → Documents found but none are relevant enough
   ```

**Configuration:**
- `SCORE_THRESHOLD` is set in `.env` (default: `0.3`)
- Line 154 in `src/rag_chain.py`: `threshold = config.score_threshold`

---

## 🎨 UI Differentiation

### Grounded Mode
- ✅ **Green border** on answer box
- ✅ **No warning banner**
- ✅ **"📚 Sources (N)"** expander with citations
- ✅ **Page numbers and relevance scores**
- ✅ **Metrics**: "X Sources" / "Grounded in PDFs"

### Fallback Mode
- ⚠️ **Orange border** on answer box
- ⚠️ **Warning banner** at top:
  > "⚠️ **No Supporting Course Documents Found**  
  > This answer is based on general model knowledge and is NOT grounded in your uploaded PDFs. Please double-check for accuracy..."
- ⚠️ **Info message**: "📝 No citations available - Answer not based on course documents."
- ⚠️ **Metrics**: "Fallback Mode" / "General knowledge"

---

## 📋 Examples

### Example 1: Grounded Mode (Good Context)
**Question:** "What is the grading policy?"  
**PDFs:** Contains "grading_policy.pdf"  
**Retrieval:** Finds 4 chunks with scores [0.85, 0.78, 0.65, 0.52]  
**Result:**
- ✅ Mode: `"grounded"`
- ✅ Uses course context
- ✅ Shows citations: [grading_policy.pdf, pp. 3-5]
- ✅ No warning banner

### Example 2: Fallback Mode (No Context)
**Question:** "What is quantum computing?"  
**PDFs:** Biology course materials only  
**Retrieval:** Finds 0 relevant chunks OR all scores < 0.3  
**Result:**
- ⚠️ Mode: `"fallback"`
- ⚠️ No course context used
- ⚠️ Answer starts with disclaimer
- ⚠️ Orange border + warning banner
- ⚠️ No sources/citations shown

### Example 3: Fallback Mode (Low Scores)
**Question:** "How do you use a microscope?"  
**PDFs:** Course has one brief mention (score: 0.18)  
**Retrieval:** Finds 1 chunk but score = 0.18 < 0.3 threshold  
**Result:**
- ⚠️ Mode: `"fallback"` (threshold not met)
- ⚠️ Uses general knowledge instead
- ⚠️ Warning banner shown
- ⚠️ Metadata includes: `"fallback_reason": "low_scores"`

---

## 🔍 Logging Output

### Grounded Mode Logs
```
INFO: Processing query: What is the grading policy?
INFO: RAG mode: grounded (found 4 chunks, max score: 0.852)
INFO: Generated grounded answer with 2 citations
```

### Fallback Mode Logs (No Chunks)
```
INFO: Processing query: What is quantum computing?
WARNING: No documents retrieved - entering fallback mode
INFO: RAG mode: fallback (using general knowledge)
```

### Fallback Mode Logs (Low Scores)
```
INFO: Processing query: How do you use a microscope?
WARNING: All retrieval scores below threshold (0.180 < 0.300) - entering fallback mode
INFO: RAG mode: fallback (using general knowledge)
```

---

## 🧪 Testing the Implementation

### Test Grounded Mode
1. Ingest course PDFs: `python -m src.ingestion --data_dir data/pdfs`
2. Ask a question directly from the PDFs
3. **Expected**: Green border, citations, no warning

### Test Fallback Mode (No Context)
1. Ask about a topic NOT in your PDFs (e.g., "What is machine learning?")
2. **Expected**: Orange border, warning banner, no citations, answer with disclaimer

### Test Threshold Adjustment
1. Edit `.env`: Set `SCORE_THRESHOLD=0.8` (very strict)
2. Ask a question
3. **Expected**: More likely to trigger fallback mode

---

## ⚙️ Configuration

Edit `.env` to adjust fallback behavior:

```bash
# Minimum similarity score for grounded mode
# Higher = stricter (more fallback triggers)
# Lower = more permissive (fewer fallback triggers)
SCORE_THRESHOLD=0.3

# Number of chunks to retrieve
TOP_K=4

# Use MMR for diversity (helps avoid fallback)
USE_MMR=true
```

---

## 🚨 Important Notes

1. **ChatGPT-only baseline unchanged**: The left side of the comparison UI (plain ChatGPT) always operates without RAG - this was NOT modified.

2. **Backward compatibility**: Old messages without `"mode"` field default to `"grounded"` (line 275 in app.py).

3. **Ingestion not affected**: PDF processing, embedding generation, and vector storage remain unchanged.

4. **LLM backend agnostic**: Fallback mode works with OpenAI, Ollama, or transformers backends.

5. **Disclaimer in answer**: The LLM is instructed to add a disclaimer in fallback mode. If the LLM doesn't comply, the UI still shows the warning banner.

---

## 📝 Summary

**What triggers fallback mode:**
- Zero chunks retrieved, OR
- All chunks have scores below `SCORE_THRESHOLD` (default: 0.3)

**How the UI differentiates:**
- **Grounded**: Green border, citations, sources, no warning
- **Fallback**: Orange border, warning banner, no citations, disclaimer message

**Files modified:**
- `src/rag_chain.py` - Core fallback logic and dual prompts
- `src/app.py` - Main chatbot UI with fallback warnings
- `src/compare_app.py` - Comparison UI with fallback styling

**No changes to:**
- Ingestion pipeline (`src/ingestion.py`)
- Embedding generation (`src/embedder.py`)
- Plain ChatGPT baseline (`answer_with_chatgpt_only()`)

---

## 🎉 Result

Your RAG system now gracefully handles questions outside the course materials by:
1. Clearly marking fallback answers as "not grounded"
2. Still providing helpful general knowledge
3. Warning users to verify with instructors
4. Maintaining visual distinction between grounded and fallback modes

