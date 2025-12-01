# Data Directory

Place your PDF course materials in this directory.

## Structure

- `pdfs/` - **Put your course PDFs here** (main folder for ingestion)
- `uploads/` - PDFs uploaded through the Streamlit UI (auto-created)

## Getting Started

1. **Create the pdfs folder** (if it doesn't exist):
   ```bash
   mkdir -p data/pdfs
   ```

2. **Add your PDFs**: Copy your course materials (syllabi, lecture notes, etc.) into `data/pdfs/`

3. **Ingest them**: Run the indexing command:
   ```bash
   python -m src.ingestion --data_dir data/pdfs
   ```

## Ingestion Commands

```bash
# Ingest all PDFs from data/pdfs
python -m src.ingestion --data_dir data/pdfs

# Ingest from a different directory
python -m src.ingestion --data_dir /path/to/your/pdfs

# Force re-index existing files
python -m src.ingestion --data_dir data/pdfs --force
```

## Supported Formats

- PDF files (.pdf)

## Notes

- PDFs are automatically chunked with page number preservation
- Files are indexed idempotently (won't re-index unless --force is used)
- Large PDFs may take a few minutes to process
- The system recursively finds all PDFs in subdirectories

