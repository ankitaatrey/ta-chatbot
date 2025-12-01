# Setup with Your Own PDFs

This guide shows you how to use the AU TA Chatbot with your own course PDFs.

## ✅ What Changed

- **Removed**: Sample PDF generation script requirement
- **Removed**: reportlab dependency (commented out in requirements.txt)
- **Changed**: Default folder from `data/sample` to `data/pdfs`
- **Simplified**: No need to generate fake PDFs - just use your real ones!

---

## 📁 Where to Put Your PDFs

**Folder**: `data/pdfs/`

This is the main folder where you should place all your course materials (syllabi, lecture notes, policies, etc.)

---

## 🚀 Quick Start Commands

### 1. Create the PDFs directory

```bash
mkdir -p data/pdfs
```

### 2. Add your PDFs

Copy your course PDFs into the folder:

```bash
# Example on Mac/Linux:
cp ~/Downloads/syllabus.pdf data/pdfs/
cp ~/Documents/lecture_notes.pdf data/pdfs/

# Or drag-and-drop files into the data/pdfs/ folder
```

### 3. Ingest (index) your PDFs

```bash
python -m src.ingestion --data_dir data/pdfs
```

You'll see output like:
```
Found X PDF files in data/pdfs
Processing: syllabus.pdf
Created 15 chunks from 3 pages
...
INGESTION SUMMARY
PDFs processed: 3/3
Total chunks added: 45
```

### 4. Start the chatbot

```bash
streamlit run src/app.py
```

Open http://localhost:8501 and start asking questions!

---

## 🛠️ Using Makefile (Alternative)

If you have `make` installed:

```bash
# 1. Setup and create directories
make setup
make init-dirs

# 2. Add your PDFs to data/pdfs/
# (copy files into the folder)

# 3. Ingest and run
make ingest
make run
```

---

## 📋 Common Commands

### Re-index after adding new PDFs

```bash
python -m src.ingestion --data_dir data/pdfs
```

### Force re-indexing (if you updated PDFs)

```bash
python -m src.ingestion --data_dir data/pdfs --force
```

### Use a different folder

```bash
python -m src.ingestion --data_dir /path/to/your/pdfs
```

### Check what's indexed

```bash
make stats
```

Or in Python:
```python
from src.vectordb import get_vectordb

db = get_vectordb()
stats = db.get_stats()
print(f"Documents: {stats['unique_documents']}")
print(f"Chunks: {stats['total_chunks']}")
```

---

## ❓ Troubleshooting

### "No PDF files found"

Check if PDFs are in the right place:
```bash
ls data/pdfs/
```

Make sure files end with `.pdf`

### "Vector database is empty"

You need to run ingestion first:
```bash
python -m src.ingestion --data_dir data/pdfs
```

### "data/pdfs/ doesn't exist"

Create it:
```bash
mkdir -p data/pdfs
```

---

## 📝 Notes

- The system recursively finds all PDFs in `data/pdfs/` and subdirectories
- PDFs are indexed idempotently (won't re-index unless you use `--force`)
- Large PDFs (100+ pages) may take a few minutes to process
- You can upload PDFs through the Streamlit UI (they go to `data/uploads/`)
- Page numbers are preserved for citations

---

## 🎯 What About Sample PDFs?

The `scripts/create_sample_pdfs.py` script is still available if you want to test the system, but it's **optional**. 

To use it:
```bash
pip install reportlab
python scripts/create_sample_pdfs.py
python -m src.ingestion --data_dir data/sample
```

But for real use, just add your own PDFs to `data/pdfs/`!

---

**You're all set!** 🎉

The chatbot will answer questions based on your course PDFs with citations and page numbers.

