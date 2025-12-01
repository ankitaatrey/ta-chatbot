# SRT Transcript Support - Implementation Guide

## Overview

The TA Chatbot now supports ingesting `.srt` (SubRip subtitle) transcript files in addition to PDF documents. This allows you to index lecture transcripts, video captions, and other subtitle-based content into your RAG system.

## What's New

### 1. New File: `src/utils/srt_parser.py`

A dedicated SRT parser that:
- ✅ Parses standard SRT format files
- ✅ Removes timestamps (e.g., `00:00:00,000 --> 00:00:02,000`)
- ✅ Removes sequence numbers
- ✅ Cleans HTML tags (`<i>`, `<b>`, `<font>`, etc.)
- ✅ Removes speaker labels (`[John:]`, `(Speaker:)`)
- ✅ Removes sound effects (`[music]`, `(applause)`, etc.)
- ✅ Handles UTF-8 and latin-1 encodings
- ✅ Validates SRT format before parsing

**Key Functions:**
```python
parse_srt(srt_path: Path) -> Optional[str]
    # Extracts clean text from SRT file

clean_subtitle_text(text: str) -> str
    # Removes common subtitle artifacts

is_valid_srt(srt_path: Path) -> bool
    # Validates SRT format
```

### 2. Updated: `src/ingestion.py`

Extended to handle both PDFs and SRTs:

**New Functions:**
```python
find_srts(directory: Path) -> List[Path]
    # Find all .srt files in directory

find_documents(directory: Path) -> Dict[str, List[Path]]
    # Find both PDFs and SRTs

ingest_srt(srt_path: Path, vectordb, ...) -> int
    # Ingest a single SRT file
```

**Updated Functions:**
- `ingest_directory()` - Now processes both PDFs and SRTs
- Command help text updated to mention SRT support

### 3. Updated: `debug_index.py`

- Renamed `inspect_specific_pdf()` to `inspect_specific_document()`
- Shows file type (pdf/srt) in chunk metadata
- Updated usage instructions to include SRT examples

## How It Works

### SRT Processing Pipeline

```
1. SRT File Input
   └─> data/pdfs/sample_lecture.srt

2. Validation
   └─> Check for timestamp pattern (00:00:00,000 --> 00:00:00,000)

3. Parsing
   ├─> Split by double newlines (subtitle blocks)
   ├─> Extract text (skip sequence numbers and timestamps)
   ├─> Clean artifacts (HTML, sound effects, speaker labels)
   └─> Join into continuous text

4. Chunking
   └─> Use same TokenAwareChunker as PDFs
       └─> Splits based on token count with overlap

5. Metadata Generation
   ├─> chunk_id: "{filename}_srt_c{index}"
   ├─> source_path: Full path to .srt file
   ├─> title: Extracted from filename
   ├─> file_type: "srt"
   ├─> page_start: 0 (SRTs don't have pages)
   └─> page_end: 0

6. Storage
   └─> Vector database (same collection as PDFs)
       ├─> Text content
       ├─> Embeddings (auto-generated)
       └─> Metadata
```

## Usage Examples

### 1. Ingest Both PDFs and SRTs

```bash
# Place files in data/pdfs/ directory
# - my_lecture.pdf
# - lecture_transcript.srt
# - course_intro.srt

# Run ingestion (processes all supported file types)
python -m src.ingestion --data_dir data/pdfs

# Output:
# Found 1 PDF files and 2 SRT files in data/pdfs
# Processing 1 PDF files...
# Ingesting PDFs: 100%|████████| 1/1 [00:05<00:00, 5.23s/it]
# Processing 2 SRT files...
# Ingesting SRTs: 100%|████████| 2/2 [00:02<00:00, 1.11s/it]
#
# INGESTION SUMMARY
# PDFs processed: 1/1
# SRTs processed: 2/2
# Total files processed: 3/3
# Total chunks added: 42
```

### 2. Ingest Only SRTs from a Directory

```bash
# If you have a directory with only SRT files
python -m src.ingestion --data_dir data/transcripts
```

### 3. Force Re-index

```bash
# Re-process all files (including already indexed ones)
python -m src.ingestion --data_dir data/pdfs --force
```

### 4. Debug SRT Chunks

```bash
# Test SRT parsing
python test_srt_parsing.py

# View all chunks from an SRT file
python debug_index.py doc sample_lecture.srt

# View database overview
python debug_index.py inspect
```

### 5. Query SRT Content

```bash
# Query both PDFs and SRTs
python debug_index.py query "What is functional programming?"

# The retrieval will search across both PDFs and SRTs
# Citations will show the source type in metadata
```

## Example SRT Format

```srt
1
00:00:00,000 --> 00:00:03,500
Welcome to today's lecture on functional programming.

2
00:00:03,500 --> 00:00:07,000
Functional programming is a programming paradigm.

3
00:00:07,500 --> 00:00:11,200
It emphasizes immutability and pure functions.
```

**After Parsing:**
```
Welcome to today's lecture on functional programming. Functional programming is a programming paradigm. It emphasizes immutability and pure functions.
```

## Metadata Stored

For each SRT chunk, the following metadata is stored:

```python
{
    "chunk_id": "sample_lecture_srt_c0",
    "source_path": "/path/to/sample_lecture.srt",
    "title": "Sample Lecture",
    "file_type": "srt",           # NEW: Indicates this is from an SRT
    "page_start": 0,              # SRTs don't have pages
    "page_end": 0
}
```

For PDF chunks (unchanged):
```python
{
    "chunk_id": "intro_p1_c0",
    "source_path": "/path/to/intro.pdf",
    "title": "Intro",
    # file_type not set (defaults to pdf)
    "page_start": 1,
    "page_end": 1
}
```

## Benefits

### 1. **Multi-Modal Knowledge Base**
- Combine lecture slides (PDFs) with lecture transcripts (SRTs)
- Better coverage: slides often lack context that transcripts provide

### 2. **Accessibility**
- Make video/audio content searchable
- Students can search lecture transcripts easily

### 3. **Unified Search**
- Query returns results from both PDFs and transcripts
- RAG system handles both sources seamlessly

### 4. **Time Efficiency**
- Auto-transcribe lectures to SRT (using Whisper, YouTube, etc.)
- Index instantly without manual note-taking

## Testing

### Test SRT Parsing

```bash
python test_srt_parsing.py
```

Expected output:
```
================================================================================
SRT PARSING TEST
================================================================================

1. Validating SRT file: sample_lecture.srt
   Valid SRT: ✅ Yes

2. Parsing SRT file...
   ✅ Successfully parsed!
   Text length: 1414 characters

3. Extracted text preview (first 500 chars):
   ────────────────────────────────────────────────────────────────────────────
   Welcome to today's lecture on functional programming. Functional programming...
   ────────────────────────────────────────────────────────────────────────────

4. Verification:
   Timestamps removed: ✅ Yes
   Sequence numbers removed: ✅ Yes
   HTML tags removed: ✅ Yes
   Sound effects removed: ✅ Yes

================================================================================
```

### Test Full Ingestion

```bash
# Ingest the sample SRT file
python -m src.ingestion --data_dir data/pdfs --force

# Verify in database
python debug_index.py inspect

# Query the content
python debug_index.py query "What is functional programming?"
```

## Advanced Features

### Custom Chunking for SRTs

```bash
# Use smaller chunks for transcripts (they're often continuous)
python -m src.ingestion --data_dir data/pdfs --chunk_size 500 --chunk_overlap 100
```

### Filtering by File Type

You can filter retrieval results by file type:

```python
# In your custom code
results = vectordb.collection.get(
    where={"file_type": "srt"},  # Only SRT files
    limit=10
)
```

## Troubleshooting

### Problem: "File does not appear to be a valid SRT"

**Solution:**
- Check that the file has proper SRT format
- Timestamps must be: `00:00:00,000 --> 00:00:00,000`
- Ensure UTF-8 encoding

### Problem: "No text extracted from SRT"

**Solution:**
- Check that subtitle blocks have at least 3 lines (number, timestamp, text)
- Verify file isn't empty or corrupted
- Try opening in a text editor to inspect format

### Problem: Special characters garbled

**Solution:**
- The parser tries UTF-8 first, then latin-1
- If still issues, convert file to UTF-8:
  ```bash
  iconv -f ISO-8859-1 -t UTF-8 input.srt > output.srt
  ```

## File Compatibility

✅ **Supported:**
- Standard SRT format (SubRip)
- UTF-8 and latin-1 encodings
- HTML tags (will be removed)
- Sound effects in brackets (will be removed)
- Multiple speakers

❌ **Not Supported:**
- WebVTT format (`.vtt`) - convert to SRT first
- ASS/SSA formats - convert to SRT first
- SRT files without timestamps

## Future Enhancements

Potential improvements:
- [ ] Support for WebVTT (`.vtt`) files
- [ ] Timestamp preservation in metadata (for video linking)
- [ ] Speaker diarization (identify different speakers)
- [ ] Auto-detect language
- [ ] Chunk by speaker turns instead of token count

## Summary

✅ **What's Working:**
- SRT file detection in data directories
- Parsing and cleaning of subtitle text
- Token-based chunking (same as PDFs)
- Storage in vector database with appropriate metadata
- Retrieval and querying alongside PDFs
- Debug tools updated for SRT support

✅ **Backward Compatibility:**
- Existing PDF ingestion unchanged
- No breaking changes to API or CLI
- Database schema compatible (SRT adds optional `file_type` field)

✅ **Ready to Use:**
```bash
# Add your .srt files to data/pdfs/
# Run ingestion
python -m src.ingestion --data_dir data/pdfs

# Done! Both PDFs and SRTs are now searchable
```

