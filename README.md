# 🎓 Multi-Source RAG Teaching Assistant

A prototype Retrieval-Augmented Generation (RAG) chatbot that answers course-related questions using multiple file types (PDFs, SRT transcripts, text files, markdown documents, etc). Designed for clarity, transparency, and demonstration - ideal for teaching, and RAG engineering practice.

> **Status:** Prototype – not a production system.

---

## Key Features

- **Multi-file-type support** – PDFs, SRT transcripts, TXT, and Markdown
- **Smart citations** – PDF page numbers and source labels
- **Advanced retrieval** – Similarity search with optional MMR reranking for diversity
- **Two UI modes** – Main chatbot and RAG-vs-ChatGPT comparison view
- **File-type-aware display** – Icons and proper formatting for each source type
- **Intelligent chitchat detection** – Recognizes greetings and casual conversation without triggering retrieval
- **Flexible backend** – Currently OpenAI; architecture ready for extension
- **Extensible loader system** – Add new file types by registering loaders

---

## Quick Start

### 1. Installation

```bash
# Clone and navigate to the project
cd ta-chatbot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
# Copy the environment template
cp env.template .env

# Edit .env and add your OpenAI API key
# Example: OPENAI_API_KEY=sk-your-key-here
```

**Important:** Never commit `.env` to version control. The template (`env.template`) shows required variables without exposing secrets.

### 3. Organize Your Data

Create a `data/` folder with your course materials. The folder structure is flexible:

```
data/
├── pdfs/
│   ├── lecture1.pdf
│   └── syllabus.pdf
├── srt/
│   ├── lecture1-transcript.srt
│   └── lecture2-transcript.srt
└── notes/
    ├── summary.txt
    └── overview.md
```

**Privacy Note:** The `data/` folder is git-ignored. Do not upload private or sensitive course materials to public repositories.

### 4. Ingest Documents

```bash
# Index all supported files from the data directory
python -m src.ingestion --data_dir data
```

This scans recursively for PDFs, SRT files, TXT, and MD files, chunks them intelligently, and stores them in the vector database with metadata.

### 5. Launch the Application

**Main Chatbot (Recommended):**

```bash
streamlit run src/app.py
```

Open http://localhost:8501 and start asking questions.

**Comparison Mode (RAG vs ChatGPT):**

```bash
streamlit run src/compare_app.py
```

View side-by-side answers from plain ChatGPT vs. your RAG-powered assistant.

---

## Supported File Types

| File Type   | Extensions         | Features                                  |
|-------------|--------------------|-------------------------------------------|
| **PDF**     | `.pdf`             | Page-aware chunking, citations with pages|
| **SRT**     | `.srt`             | Video transcript extraction               |
| **Text**    | `.txt`             | Plain text documents                      |
| **Markdown**| `.md`, `.markdown` | Markdown formatting preserved             |

### Citation Examples

- **PDFs:** `[Lecture Notes (PDF), pp. 12-14]`
- **SRTs:** `[Intro Video Transcript]`
- **Text/Markdown:** `[Course Summary (TXT)]`

---

## User Interface

### Main Chatbot (`src/app.py`)

- Chat interface for asking course-related questions
- Answers with inline citations
- Expandable sources section showing:
  - File type icons (📄 PDF, 🎬 SRT, 📝 TXT)
  - Page numbers (for PDFs)
  - Relevance scores
  - Text snippets from sources

### Comparison Mode (`src/compare_app.py`)

**Left:** Plain ChatGPT (no course context)
- Generic answers
- May hallucinate course details
- No citations

**Right:** RAG-powered TA Bot (with your documents)
- Grounded in actual course materials
- Citations with page numbers
- File-type icons and labels

-----

## Architecture

```
┌─────────────────────────────────────────┐
│  Data Sources (data/)                   │
│  ├── PDFs                               │
│  ├── SRT Transcripts                    │
│  └── TXT/MD Files                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Document Loaders                       │
│  (src/document_loaders.py)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Ingestion & Chunking                   │
│  (src/ingestion.py)                     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Vector Database (ChromaDB)             │
│  Embeddings + Metadata                  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Retrieval (src/retriever.py)           │
│  Similarity + Optional MMR              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  RAG Chain (src/rag_chain.py)           │
│  Context + LLM + Citations              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  UI (Streamlit)                         │
│  app.py / compare_app.py                │
└─────────────────────────────────────────┘
```

---

## Configuration

Edit `.env` to customize behavior:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini

# Retrieval Settings
TOP_K=4                    # Number of chunks to retrieve
SCORE_THRESHOLD=0.3        # Minimum similarity score (0.0-1.0)
USE_MMR=true              # Enable MMR reranking
MMR_DIVERSITY=0.3         # Diversity factor (0.0-1.0)

# Chunking
CHUNK_SIZE=1000           # Tokens per chunk
CHUNK_OVERLAP=150         # Overlap between chunks

# Logging
LOG_LEVEL=INFO            # DEBUG | INFO | WARNING | ERROR
```

---

## Chitchat Detection

The system recognizes casual conversation and responds naturally **without** triggering document retrieval, saving time and API costs.

**Detected patterns:**
- Greetings: "hi", "hello", "hey"
- Farewells: "bye", "goodbye"
- Thanks: "thanks", "thank you"
- Casual: "how are you", "what's up"

**Example:**
```
User: "Hi!"
Bot: "Hello! I'm your course assistant. How can I help you today?"
     [No retrieval, no citations]

User: "What is lambda calculus?"
Bot: [Normal RAG with sources and citations]
```

---

## Troubleshooting

### No documents retrieved

**Lower the score threshold:**
```bash
# In .env
SCORE_THRESHOLD=0.2
```

**Verify database has content:**
```bash
python -c "
from src.vectordb import get_vectordb
stats = get_vectordb().get_stats()
print(f'Total chunks: {stats[\"total_chunks\"]}')
"
```

### Port already in use

```bash
# Kill existing Streamlit process
pkill -f streamlit

# Or use a different port
streamlit run src/app.py --server.port 8502
```

### Re-index documents

```bash
# Delete existing database and re-ingest
rm -rf chroma_db
python -m src.ingestion --data_dir data --force
```

---

## Project Structure

```
ta-chatbot/
├── src/
│   ├── document_loaders.py    # Multi-file-type loaders
│   ├── ingestion.py           # Document ingestion pipeline
│   ├── retriever.py           # Similarity search + MMR
│   ├── rag_chain.py           # RAG orchestration
│   ├── app.py                 # Main chatbot UI
│   ├── compare_app.py         # Comparison UI
│   ├── splitter.py            # Token-aware chunking
│   ├── embedder.py            # Embedding generation
│   ├── vectordb.py            # ChromaDB interface
│   ├── llm.py                 # LLM backend
│   ├── config.py              # Configuration management
│   └── utils/
│       ├── citations.py       # File-type-aware citations
│       ├── logging_setup.py   # Logging configuration
│       └── text_normalize.py  # Text cleaning utilities
├── data/                      # Your course materials (git-ignored)
│   ├── pdfs/
│   ├── srt/
│   └── notes/
├── chroma_db/                # Vector database (auto-created)
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── .env                      # Your config (git-ignored, create from template)
├── env.template             # Environment template
└── README.md                # This file
```

---

## Requirements

- **Python:** 3.9 or higher
- **RAM:** 4GB minimum (8GB+ recommended)
- **API:** OpenAI API key
- **Disk:** ~500MB for models and vector database

----

## License

MIT License. See `LICENSE` file for details.

This project is provided as-is for educational and demonstration purposes.

----

## Acknowledgments

Built as a prototype for university Teaching Assistants to demonstrate:
- Multi-source RAG with diverse file types
- Citation transparency and grounding
- Comparison with baseline LLM responses
- Extensible architecture for RAG systems

---

## Additional Documentation

- **`MULTI_FILE_TYPE_GUIDE.md`** – Detailed architecture documentation
- **`CHITCHAT_FEATURE.md`** – Chitchat detection implementation
- **`FALLBACK_MODE_IMPLEMENTATION.md`** – Grounding and fallback behavior

---

**Questions or feedback?** This is a prototype project for demonstration and learning. Contributions and suggestions welcome!

