# Quick Start: Multi-File-Type RAG

## 🚀 Get Started in 3 Steps

### Step 1: Organize Your Data

Create a data folder with your course materials:

```bash
mkdir -p data/my-course/pdfs
mkdir -p data/my-course/srt
mkdir -p data/my-course/notes
```

Add your files:
```
data/
└── my-course/
    ├── pdfs/
    │   ├── lecture1.pdf
    │   └── textbook.pdf
    ├── srt/
    │   ├── lecture1-transcript.srt
    │   └── lecture2-transcript.srt
    └── notes/
        ├── summary.txt
        └── README.md
```

### Step 2: Ingest Your Documents

Run ingestion (this indexes all supported file types):

```bash
python -m src.ingestion --data_dir data
```

**What happens:**
- ✅ Scans recursively for PDF, SRT, TXT, MD files
- ✅ Uses appropriate loader for each file type
- ✅ Chunks text intelligently
- ✅ Stores in vector database with metadata
- ✅ Reports stats by file type

**Example output:**
```
Found 15 supported documents in data
  .pdf: 5 files
  .srt: 8 files
  .txt: 1 files
  .md: 1 files

Processing documents: 100%|██████████| 15/15

INGESTION SUMMARY
==================================
Total files processed: 15/15
Total chunks added: 487

By file type:
  .pdf: 5 files, 231 chunks
  .srt: 8 files, 198 chunks
  .txt: 1 files, 32 chunks
  .md: 1 files, 26 chunks

Database total chunks: 487
Database unique documents: 15
```

### Step 3: Ask Questions!

Launch the web UI:

```bash
streamlit run src/app.py
```

Or use comparison mode:

```bash
streamlit run src/compare_app.py
```

**What you'll see:**
- 📄 PDF citations: "Lecture Notes (PDF), pp. 3-5"
- 🎬 SRT citations: "Lecture 1 Transcript"
- 📝 TXT citations: "Summary Notes (TXT)"
- 📋 MD citations: "README (MD)"

---

## 🎯 Example Queries

### Query: "What is functional programming?"

**Response might cite:**
- 📄 "Intro to Programming (PDF), pp. 12-14"
- 🎬 "Lecture 2 Transcript" 
- 📝 "FP Summary (TXT)"

**In the UI:**
- Answer with mixed citations
- Sources section shows all file types
- Each source has appropriate icon and location format

---

## ⚡ Quick Commands

### Ingestion
```bash
# Basic ingestion
python -m src.ingestion --data_dir data

# Force re-index (overwrites existing)
python -m src.ingestion --data_dir data --force

# Custom chunk settings
python -m src.ingestion --data_dir data --chunk_size 400 --chunk_overlap 50

# Debug mode
python -m src.ingestion --data_dir data --log_level DEBUG
```

### Running the Apps
```bash
# Main chatbot
streamlit run src/app.py

# Comparison mode (RAG vs ChatGPT)
streamlit run src/compare_app.py
```

---

## 🔧 Adding a New File Type

**Example: Add `.docx` support**

1. Install library:
```bash
pip install python-docx
```

2. Add loader in `src/document_loaders.py`:
```python
class DocxLoader:
    def load(self, path: Path) -> Dict[str, Any]:
        from docx import Document
        doc = Document(path)
        text = "\n".join([p.text for p in doc.paragraphs])
        text = normalize_whitespace(text)
        
        return {
            "text": text,
            "metadata": {
                "source": path.name,
                "file_type": "docx",
                "path": str(path),
                "title": extract_title_from_filename(path.name),
            }
        }

# Register it
LOADER_REGISTRY = {
    ".pdf": PdfLoader(),
    ".srt": SrtLoader(),
    ".txt": TxtLoader(),
    ".md": MarkdownLoader(),
    ".docx": DocxLoader(),  # ← Add this
}
```

3. (Optional) Update UI file uploader in `src/app.py`:
```python
type=["pdf", "srt", "txt", "md", "docx"]  # Add "docx"
```

4. Re-run ingestion:
```bash
python -m src.ingestion --data_dir data --force
```

That's it! `.docx` files now work throughout the entire pipeline.

---

## 📊 Check Your Index

View database stats in Python:

```python
from src.vectordb import get_vectordb

vdb = get_vectordb()
stats = vdb.get_stats()

print(f"Total chunks: {stats['total_chunks']}")
print(f"Unique documents: {stats['unique_documents']}")
print("\nSources:")
for source in stats['sources']:
    print(f"  - {source}")
```

Test retrieval by file type:

```python
from src.retriever import get_retriever

retriever = get_retriever(vdb)
results = retriever.retrieve("functional programming")

print(f"Found {len(results)} results:")
for r in results:
    meta = r['metadata']
    file_type = meta.get('file_type', 'unknown')
    title = meta.get('title', 'Unknown')
    score = r['score']
    print(f"  [{file_type.upper()}] {title} (score: {score:.3f})")
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Ingestion processes all file types
- [ ] Database shows correct chunk count
- [ ] UI launches without errors
- [ ] Asking a question returns an answer
- [ ] Sources section shows mixed file types
- [ ] PDFs show page numbers
- [ ] SRTs show "Transcript" label
- [ ] Icons appear correctly (📄 🎬 📝 📋)
- [ ] Debug mode shows relevance scores

---

## 🐛 Common Issues

**Issue:** "No supported files found"

**Fix:** Check file extensions match `LOADER_REGISTRY`:
```python
from src.document_loaders import get_supported_extensions
print(get_supported_extensions())
```

---

**Issue:** "PyPDF2 not found"

**Fix:** Install dependencies:
```bash
pip install -r requirements.txt
```

---

**Issue:** Ingestion succeeds but no results when querying

**Fix:** Check embedding model is working:
```python
from src.embedder import get_embedder

embedder = get_embedder()
embedding = embedder.embed_query("test")
print(f"Embedding dim: {len(embedding)}")  # Should be > 0
```

---

**Issue:** Citations showing wrong format

**Fix:** Verify `file_type` metadata:
```python
from src.vectordb import get_vectordb

vdb = get_vectordb()
sample = vdb.collection.get(limit=1, include=["metadatas"])
print(sample['metadatas'][0])
# Should have "file_type": "pdf" or "srt" etc.
```

---

## 📚 Next Steps

1. Read `MULTI_FILE_TYPE_GUIDE.md` for complete documentation
2. Explore `src/document_loaders.py` to see loader examples
3. Add your own file types as needed
4. Customize citation formatting in `src/utils/citations.py`

---

## 🎉 You're Ready!

Your RAG system now supports:
- ✅ PDF documents with page numbers
- ✅ SRT video transcripts
- ✅ Plain text files
- ✅ Markdown documents
- ✅ Easy extension for new file types

Enjoy your multi-source RAG chatbot! 🚀

