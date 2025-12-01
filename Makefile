.PHONY: help setup pdfs ingest run test eval clean clean-db

# Default target
help:
	@echo "AU TA Chatbot - Makefile Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup       - Install dependencies and setup environment"
	@echo "  make init-dirs   - Create data directories"
	@echo ""
	@echo "Running:"
	@echo "  make ingest      - Ingest PDFs from data/pdfs into vector database"
	@echo "  make run         - Start Streamlit app (main chatbot)"
	@echo "  make compare     - Start RAG vs ChatGPT comparison UI"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make eval        - Run evaluation suite"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean-db    - Delete vector database"
	@echo "  make clean       - Clean all generated files"
	@echo ""

# Setup environment
setup:
	@echo "Setting up environment..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make init-dirs' to create data directories"
	@echo "  3. Add your PDFs to data/pdfs/"
	@echo "  4. Run 'make ingest' to index documents"
	@echo "  5. Run 'make run' to start the app"

# Create data directories
init-dirs:
	@echo "Creating data directories..."
	@mkdir -p data/pdfs
	@echo "Created data/pdfs/"
	@echo ""
	@echo "Now add your course PDFs to data/pdfs/ and run 'make ingest'"

# Ingest documents
ingest:
	@echo "Ingesting documents from data/pdfs/..."
	@if [ ! -d "data/pdfs" ] || [ -z "$$(ls -A data/pdfs 2>/dev/null)" ]; then \
		echo "Error: data/pdfs/ is empty or doesn't exist"; \
		echo "Run 'make init-dirs' and add your PDFs to data/pdfs/"; \
		exit 1; \
	fi
	python -m src.ingestion --data_dir data/pdfs
	@echo "Ingestion complete!"

# Run Streamlit app
run:
	@echo "Starting Streamlit app..."
	@echo "Open http://localhost:8501 in your browser"
	streamlit run src/app.py

# Run comparison app
compare:
	@echo "Starting RAG vs ChatGPT comparison app..."
	@echo "Open http://localhost:8501 in your browser"
	streamlit run src/compare_app.py

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --tb=short

# Run evaluation
eval:
	@echo "Running evaluation suite..."
	python eval/run_eval.py --verbose

# Clean vector database
clean-db:
	@echo "Cleaning vector database..."
	rm -rf chroma_db
	@echo "Vector database deleted. Run 'make ingest' to rebuild."

# Clean all generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf chroma_db
	rm -rf data/uploads
	rm -rf __pycache__ src/__pycache__ src/utils/__pycache__ tests/__pycache__
	rm -rf .pytest_cache
	rm -rf *.pyc src/*.pyc src/utils/*.pyc tests/*.pyc
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

# Quick start (setup + directories)
quickstart: setup init-dirs
	@echo ""
	@echo "Quick start complete!"
	@echo "Next: Add your PDFs to data/pdfs/, then run 'make ingest' and 'make run'"

# Development setup with all dependencies
dev-setup: setup
	@echo "Installing development dependencies..."
	pip install pytest black flake8 mypy
	@echo "Development setup complete!"

# Format code (requires black)
format:
	@echo "Formatting code..."
	black src/ tests/ --line-length 100
	@echo "Code formatted!"

# Lint code (requires flake8)
lint:
	@echo "Linting code..."
	flake8 src/ tests/ --max-line-length 100 --ignore E203,W503
	@echo "Linting complete!"

# Type check (requires mypy)
typecheck:
	@echo "Type checking..."
	mypy src/ --ignore-missing-imports
	@echo "Type checking complete!"

# Full quality check
quality: format lint typecheck test
	@echo "Quality checks complete!"

# Install Ollama (instructions only)
install-ollama:
	@echo "To install Ollama:"
	@echo ""
	@echo "macOS/Linux:"
	@echo "  curl -fsSL https://ollama.ai/install.sh | sh"
	@echo ""
	@echo "Or download from: https://ollama.ai"
	@echo ""
	@echo "Then pull a model:"
	@echo "  ollama pull llama3.1:8b"
	@echo ""
	@echo "Start Ollama:"
	@echo "  ollama serve"

# Show stats
stats:
	@echo "Project Statistics"
	@echo "=================="
	@echo ""
	@echo "Lines of code:"
	@find src -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Test files:"
	@find tests -name "test_*.py" | wc -l
	@echo ""
	@echo "Vector DB status:"
	@if [ -d "chroma_db" ]; then \
		echo "  Vector database exists"; \
	else \
		echo "  Vector database not created yet"; \
	fi
	@echo ""
	@echo "PDFs in data/pdfs:"
	@if [ -d "data/pdfs" ]; then \
		find data/pdfs -name "*.pdf" | wc -l; \
	else \
		echo "  data/pdfs/ not created yet (run 'make init-dirs')"; \
	fi

