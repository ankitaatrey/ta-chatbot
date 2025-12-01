# Quick Start Guide

Get the AU TA Chatbot running in 5 minutes! 🚀

## Prerequisites

- Python 3.10 or higher
- 4GB RAM minimum
- Internet connection (for initial setup)

## Installation Steps

### 1. Install Dependencies (2 minutes)

```bash
# Navigate to project directory
cd ta-chatbot

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all requirements
pip install -r requirements.txt
```

### 2. Configure Environment (30 seconds)

```bash
# Copy environment template
cp env.template .env  # On Windows: copy env.template .env

# Edit .env if needed (optional - defaults work)
# For local-only usage, no changes needed!
```

### 3. Add Your PDFs (2 minutes)

```bash
# Create the PDFs directory
mkdir -p data/pdfs

# Copy your course PDFs into this folder
# For example:
# cp ~/Downloads/syllabus.pdf data/pdfs/
# cp ~/Documents/lecture_notes.pdf data/pdfs/
```

**Note**: You need your own course PDFs. The system will work with any PDF documents (syllabi, lecture notes, course policies, etc.)

### 4. Index Documents (1-2 minutes)

```bash
# Ingest your PDFs into vector database
python -m src.ingestion --data_dir data/pdfs
```

You should see:
```
Found X PDF files in data/pdfs
Processing: your_syllabus.pdf
Created N chunks from M pages
...
INGESTION SUMMARY
PDFs processed: X/X
Total chunks added: N
```

### 5. Launch the App (30 seconds)

```bash
# Start Streamlit
streamlit run src/app.py
```

The app will open automatically at http://localhost:8501

## Using the App

1. **Ask a Question**: Type in the chat box, e.g., "What is the grading policy for Biology 101?"

2. **View Sources**: Expand the "Sources" section to see retrieved documents with page numbers

3. **Upload PDFs**: Use the sidebar to add your own course materials

4. **Adjust Settings**: Use sliders to tune Top-K and score threshold

## Try These Sample Questions

- "What is the grading policy for Biology 101?"
- "Who teaches Physics 201?"
- "What are the office hours for Biology?"
- "What is the policy on late work?"
- "What topics are covered in the physics course?"

## Using with OpenAI (Optional)

If you have an OpenAI API key:

1. Edit `.env`:
   ```bash
   LOCAL=0
   OPENAI_API_KEY=sk-your-key-here
   ```

2. Restart the app

## Using with Ollama (Recommended for Better Local Performance)

1. Install Ollama from https://ollama.ai

2. Pull a model:
   ```bash
   ollama pull llama3.1:8b
   ```

3. Ensure `.env` has:
   ```bash
   LOCAL=1
   LOCAL_MODEL=llama3.1:8b
   ```

4. Restart the app

## Troubleshooting

### "No module named X"

```bash
pip install -r requirements.txt
```

### "Vector database is empty"

```bash
# Make sure you have PDFs in data/pdfs/
ls data/pdfs/

# Then ingest them
python -m src.ingestion --data_dir data/pdfs
```

### App won't start

```bash
# Check if port 8501 is in use
streamlit run src/app.py --server.port 8502
```

### Ollama connection failed

The app will automatically fall back to a local transformers model (slower but works).

## One-Command Setup (Using Makefile)

If you have `make` installed:

```bash
make setup      # Install dependencies
make init-dirs  # Create data directories
# Now add your PDFs to data/pdfs/
make ingest     # Index documents
make run        # Start app
```

Or for initial setup:

```bash
make quickstart  # Setup + create directories
# Then add your PDFs to data/pdfs/
make ingest
make run
```

## Next Steps

- Add your own PDFs to `data/` and run ingestion
- Customize prompts in `src/rag_chain.py`
- Run evaluation: `python eval/run_eval.py`
- Run tests: `pytest tests/ -v`

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review logs in the terminal for error messages
- Ensure all dependencies are installed

---

**You're ready to go!** 🎉

The chatbot will answer questions based on the sample course materials, with citations and page numbers.

