# Multi-File-Type RAG System Guide

## Overview

Your TA chatbot now has a **clean, generic, extensible architecture** for handling multiple file types. This document explains how the system works and how to use/extend it.

---

## ✅ What Changed

### Phase 1: Rollback to Clean Baseline
- ✅ Restored `ingestion.py` to original PDF-only version
- ✅ Restored `rag_chain.py` (removed ad-hoc chitchat mode)
- ✅ Restored `compare_app.py` to baseline
- ✅ Removed ad-hoc SRT files (`srt_parser.py`, `test_srt_parsing.py`)
- ✅ System returned to stable PDF-only baseline

### Phase 2: Generic Loader Architecture
- ✅ Created `src/document_loaders.py` with pluggable loader system
- ✅ Updated `ingestion.py` to use generic loaders
- ✅ Updated `src/utils/citations.py` to be file-type aware
- ✅ Updated `src/app.py` and `src/compare_app.py` for multi-file-type display

---

## 📁 Architecture Overview

### Document Loaders (`src/document_loaders.py`)

The heart of the multi-file-type system is the **loader registry**:

```python
LOADER_REGISTRY = {
    ".pdf": PdfLoader(),
    ".srt": SrtLoader(),
    ".txt": TxtLoader(),
    ".md": MarkdownLoader(),
    # Add more here!
}
```

**Key Features:**
- ✅ Protocol-based design (all loaders implement `DocumentLoader`)
- ✅ Standardized output format (all return `{"text": str, "metadata": dict}`)
- ✅ Automatic file type detection by extension
- ✅ Course/collection ID extraction from folder structure

### Currently Supported File Types

| Extension | Loader | Description |
|-----------|--------|-------------|
| `.pdf` | `PdfLoader` | PDF documents with page number metadata |
| `.srt` | `SrtLoader` | Video transcripts (removes timestamps, keeps spoken text) |
| `.txt` | `TxtLoader` | Plain text files |
| `.md`, `.markdown` | `MarkdownLoader` | Markdown documents |

---

## 🚀 How to Use

### 1. Basic Ingestion

Ingest all supported files from a directory:

```bash
# Ingest from data/ directory (recursive)
python -m src.ingestion --data_dir data

# Force re-indexing
python -m src.ingestion --data_dir data --force

# Custom chunk settings
python -m src.ingestion --data_dir data --chunk_size 400 --chunk_overlap 50
```

### 2. Folder Structure

Organize your data for multi-course support:

```
data/
├── programming-languages/
│   ├── pdfs/
│   │   ├── intro.pdf
│   │   ├── functional.pdf
│   │   └── lambda.pdf
│   └── srt/
│       ├── lecture1.srt
│       ├── lecture2.srt
│       └── lecture3.srt
├── data-visualization/
│   ├── pdfs/
│   │   └── visualization.pdf
│   └── srt/
│       └── intro.srt
└── notes/
    ├── summary.txt
    └── README.md
```

**Benefits:**
- First folder under `data/` becomes `course_id` in metadata
- Enables filtering/grouping by course later
- Mix and match file types in the same course

### 3. UI Usage

**Web Interface (`src/app.py`):**
- Upload documents via sidebar (now accepts PDF, SRT, TXT, MD)
- Citations show file type with appropriate icons:
  - 📄 PDFs → "Document (PDF), p. 3"
  - 🎬 SRT → "Lecture Transcript"
  - 📝 TXT → "Notes (TXT)"
  - 📋 MD → "README (MD)"
- Debug mode shows file types clearly

**Comparison Mode (`src/compare_app.py`):**
- Same multi-file-type support in source display
- File-type-aware citations in both columns

---

## 🔧 How to Add a New File Type

Adding support for a new file type is **easy** and requires **no changes to core code**!

### Example: Adding PowerPoint Support

**Step 1: Create a Loader Class**

Add to `src/document_loaders.py`:

```python
class PptxLoader:
    """Loader for PowerPoint presentations."""
    
    def load(self, path: Path) -> Dict[str, Any]:
        # Parse PPTX (you'd use python-pptx library)
        from pptx import Presentation
        
        prs = Presentation(path)
        slides_text = []
        
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slides_text.append(shape.text)
        
        full_text = "\n\n".join(slides_text)
        full_text = normalize_whitespace(full_text)
        
        title = extract_title_from_filename(path.name)
        
        return {
            "text": full_text,
            "metadata": {
                "source": path.name,
                "file_type": "pptx",
                "path": str(path),
                "title": title,
                "num_slides": len(prs.slides),
            }
        }
```

**Step 2: Register the Loader**

In the same file, update `LOADER_REGISTRY`:

```python
LOADER_REGISTRY = {
    ".pdf": PdfLoader(),
    ".srt": SrtLoader(),
    ".txt": TxtLoader(),
    ".md": MarkdownLoader(),
    ".pptx": PptxLoader(),  # ← Add this!
}
```

**Step 3: Update UI File Upload (Optional)**

In `src/app.py`, line ~191:

```python
uploaded_files = st.file_uploader(
    "Add documents",
    type=["pdf", "srt", "txt", "md", "pptx"],  # ← Add "pptx"
    accept_multiple_files=True,
    help="Upload documents (PDF, SRT, TXT, MD, PPTX) to add to the knowledge base"
)
```

**Step 4: That's It!**

Run ingestion and it will automatically:
- ✅ Detect `.pptx` files
- ✅ Use your loader
- ✅ Chunk the text
- ✅ Store with metadata
- ✅ Display correctly in UI with citations

---

## 📋 Metadata Structure

All loaders return a standardized metadata format:

### Required Fields
```python
{
    "source": "filename.ext",       # File name only
    "file_type": "pdf",             # Type identifier
    "path": "/full/path/to/file",  # Full path
    "title": "Human Readable Title" # Derived from filename or content
}
```

### Optional Fields (Recommended)
```python
{
    "course_id": "programming-languages",  # Auto-derived from folder structure
    
    # PDF-specific:
    "num_pages": 42,
    # page_start/page_end added per-chunk during chunking
    
    # SRT-specific:
    "num_segments": 150,
    "duration": "01:23:45",
    
    # Generic:
    "author": "Prof. Smith",
    "date": "2024-11-24",
    # ... any other relevant metadata
}
```

**Important:** 
- Metadata flows through the entire pipeline (ingestion → retrieval → RAG → citations → UI)
- Citations use metadata to format appropriately (e.g., page numbers for PDFs, segments for SRT)

---

## 🔍 How Citations Work Across File Types

The `src/utils/citations.py` module formats citations based on `file_type`:

### PDF Citations
```python
metadata = {"file_type": "pdf", "title": "Intro to ML", "page_start": 3, "page_end": 5}
# Output: "[Intro to ML (PDF), pp. 3-5]"
```

### SRT Citations
```python
metadata = {"file_type": "srt", "title": "Lecture 1"}
# Output: "[Lecture 1 (Transcript)]"
```

### Text/Markdown Citations
```python
metadata = {"file_type": "txt", "title": "Course Notes"}
# Output: "[Course Notes (TXT)]"
```

### UI Display
The `format_source_for_display()` function adds icons and formats location:
- 📄 PDF → "Page 3" or "Pages 3-5"
- 🎬 SRT → "Video Transcript"
- 📝 TXT → "TXT"
- 📋 MD → "MD"

---

## 🧪 Testing the System

### 1. Test Ingestion

```bash
# Ingest sample data
python -m src.ingestion --data_dir data --log_level DEBUG

# Expected output:
# Found X PDF files
# Found Y SRT files
# Found Z TXT files
# ... (processing)
# Total chunks added: N
```

### 2. Test Retrieval

Check that different file types are retrieved:

```bash
# Use debug script
python -c "
from src.vectordb import get_vectordb
from src.retriever import get_retriever

vdb = get_vectordb()
retriever = get_retriever(vdb)

results = retriever.retrieve('What is functional programming?')

for r in results:
    meta = r['metadata']
    print(f\"{meta['title']} ({meta['file_type']}) - Score: {r['score']:.3f}\")
"
```

### 3. Test UI Citations

Run the app and ask a question:

```bash
streamlit run src/app.py
```

**Verify:**
- ✅ Sources show correct icons (📄 📬 📝 📋)
- ✅ PDFs display "Page X" or "Pages X-Y"
- ✅ SRTs display "Video Transcript"
- ✅ Answer includes mixed citations if query uses multiple types

### 4. Test Comparison Mode

```bash
streamlit run src/compare_app.py
```

**Verify:**
- ✅ RAG side shows sources with file types
- ✅ Citations display correctly for all file types

---

## 📊 Current vs. Previous State

### Before (Ad-hoc SRT Integration)
❌ SRT-specific code scattered across ingestion, retrieval, RAG  
❌ Hard to add new file types (would require touching many files)  
❌ Citations didn't work consistently for SRTs  
❌ UI showed SRT chunks in debug but not in citations  
❌ Tight coupling between file types and core logic

### After (Generic Architecture)
✅ **Single source of truth:** `LOADER_REGISTRY` in `document_loaders.py`  
✅ **Easy extension:** Add a new file type by registering a loader  
✅ **Consistent metadata:** All loaders return the same structure  
✅ **File-type-aware citations:** Citations format correctly for each type  
✅ **UI consistency:** All file types displayed with appropriate formatting  
✅ **Clean separation:** Core pipeline is file-type agnostic

---

## 🎯 Design Principles

1. **Separation of Concerns**
   - Loaders know how to parse files
   - Ingestion knows how to chunk and store
   - Retrieval is file-type agnostic
   - Citations know how to format display

2. **Open/Closed Principle**
   - Open for extension (add new loaders)
   - Closed for modification (core pipeline unchanged)

3. **Consistency**
   - All loaders follow the same protocol
   - All metadata follows the same structure
   - All citations use the same formatting logic

4. **Scalability**
   - Add 10 new file types without changing core code
   - Mix and match file types in the same course
   - Filter/group by file type in future enhancements

---

## 🔮 Future Enhancements

**Easy to add now:**
- `.docx` (Word documents) via `python-docx`
- `.html` (HTML pages) via `BeautifulSoup`
- `.csv` (Structured data) via `pandas`
- `.json` (JSON documents)
- `.epub` (E-books)

**Potential features:**
- Filter retrieval by file type (e.g., "only search PDFs")
- Group sources by course in UI
- Show file type statistics in sidebar
- Export citations in different formats (APA, MLA, etc.)

---

## 📚 Key Files Modified

| File | Purpose | Changes |
|------|---------|---------|
| `src/document_loaders.py` | **NEW** | Generic loader architecture |
| `src/ingestion.py` | Ingestion pipeline | Now uses generic loaders |
| `src/utils/citations.py` | Citation formatting | File-type-aware formatting |
| `src/app.py` | Main UI | Multi-file-type display |
| `src/compare_app.py` | Comparison UI | Multi-file-type display |
| `src/rag_chain.py` | RAG pipeline | Restored to baseline (no ad-hoc changes) |

---

## ✅ Summary

You now have a **production-ready, extensible RAG system** that:

1. ✅ **Works with multiple file types** (PDF, SRT, TXT, MD) out of the box
2. ✅ **Easy to extend** (add new types by registering loaders)
3. ✅ **Consistent citations** (file-type-aware formatting)
4. ✅ **Clean codebase** (no ad-hoc file-type logic scattered around)
5. ✅ **Robust metadata** (flows through entire pipeline)
6. ✅ **UI-ready** (displays all file types with appropriate formatting)

**To add a new file type:** Just create a loader class and register it. That's it!

---

## 🆘 Troubleshooting

**Issue:** Files not being ingested

**Solution:** Check if extension is in `LOADER_REGISTRY`:
```python
from src.document_loaders import get_supported_extensions
print(get_supported_extensions())
# Output: ['.pdf', '.srt', '.txt', '.md', '.markdown']
```

**Issue:** Citations showing wrong format

**Solution:** Check `file_type` in metadata:
```python
# In debug mode, inspect retrieved chunks
# Verify metadata["file_type"] is set correctly
```

**Issue:** New loader not working

**Checklist:**
1. ✅ Does loader implement `load(path: Path) -> Dict` method?
2. ✅ Does it return `{"text": str, "metadata": dict}`?
3. ✅ Is `file_type` set in metadata?
4. ✅ Is extension registered in `LOADER_REGISTRY`?

---

## 📞 Contact

For questions or issues with the multi-file-type system, refer to:
- This guide
- Code comments in `src/document_loaders.py`
- Example loaders (PDF, SRT, TXT, MD)

Happy RAG building! 🚀

