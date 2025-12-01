# LLM Backend Configuration Guide

## ✅ Fixed Issues

The LLM backend has been fixed to properly handle OpenAI and local models:

1. **✓ OpenAI works reliably** - When `LOCAL=0`, only OpenAI is used (no fallback to transformers)
2. **✓ No more llama3.1:8b errors** - Fixed the bug where Ollama model names were passed to transformers
3. **✓ Clear error messages** - If OpenAI fails with `LOCAL=0`, you get a clear error (not silent fallback)
4. **✓ Better logging** - See exactly which backend is initialized at startup

---

## 🚀 Quick Setup for OpenAI/ChatGPT

### Step 1: Edit your `.env` file

```bash
# Use OpenAI (recommended)
LOCAL=0

# Add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-key-here

# Choose your model (gpt-4o-mini is fast and cheap)
OPENAI_MODEL=gpt-4o-mini
```

### Step 2: Verify it works

```bash
streamlit run src/app.py
```

**Look for this log message:**
```
✓ LLM backend initialized: backend=openai, model=gpt-4o-mini, local=False
```

**You should NOT see:**
- "Loading transformers model: llama3.1:8b"
- "Failed to initialize transformers"
- "No LLM backend available"

---

## 🔧 Configuration Options

### Option 1: OpenAI/ChatGPT (Recommended)

**When to use:** Production, reliable answers, fast responses

**.env settings:**
```bash
LOCAL=0
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

**Behavior:**
- ✅ Uses OpenAI API directly
- ✅ Fast, reliable, high-quality answers
- ❌ Requires API key and costs money (but cheap)
- ❌ No fallback to local models (intentional for reliability)

**Cost:** ~$0.15 per 1000 questions (gpt-4o-mini)

---

### Option 2: Local Models (Ollama)

**When to use:** Development, no internet, privacy concerns

**.env settings:**
```bash
LOCAL=1
LOCAL_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

**Prerequisites:**
1. Install Ollama: https://ollama.ai
2. Pull model: `ollama pull llama3.1:8b`
3. Start server: `ollama serve`

**Behavior:**
- ✅ Free, runs locally
- ✅ Good quality with llama3.1:8b
- ❌ Slower than OpenAI
- ❌ Requires ~8GB RAM
- ⚠️ Falls back to transformers if Ollama unavailable

---

### Option 3: Local Models (Transformers)

**When to use:** Last resort if Ollama doesn't work

**.env settings:**
```bash
LOCAL=1
# Ollama will fail, fallback to transformers
```

**Behavior:**
- ✅ Works on any machine
- ❌ Very slow on CPU
- ❌ Lower quality answers
- ⚠️ Auto-used only if Ollama unavailable

---

## 🐛 What Was Fixed

### Before (Broken):
```
LOCAL=0
OPENAI_API_KEY=sk-...

# App logs:
Loading transformers model: llama3.1:8b
Failed to initialize transformers: Repo id must use alphanumeric chars ... 'llama3.1:8b'
No LLM backend available.
```

**Problem:** Even with `LOCAL=0`, it tried local models and failed.

### After (Fixed):
```
LOCAL=0
OPENAI_API_KEY=sk-...

# App logs:
✓ LLM backend initialized: backend=openai, model=gpt-4o-mini, local=False
```

**Solution:** 
1. Changed default from `LOCAL=1` to `LOCAL=0`
2. When `LOCAL=0`, OpenAI is REQUIRED (no fallback)
3. Fixed transformers fallback to detect Ollama format names

---

## 📊 Backend Decision Logic

```
Start
  │
  ├─ LOCAL=0 + OPENAI_API_KEY set?
  │    YES → Use OpenAI ✓
  │    NO  → ERROR (no fallback)
  │
  └─ LOCAL=1?
       YES → Try Ollama
           ├─ Ollama available? → Use Ollama ✓
           └─ Ollama unavailable → Use Transformers ⚠️
```

---

## 🔍 Debugging

### Check Current Configuration

Look for this log line when the app starts:
```
Configuration loaded: LOCAL=False, Backend=OpenAI (gpt-4o-mini)
```

### Check LLM Initialization

Look for this log line:
```
✓ LLM backend initialized: backend=openai, model=gpt-4o-mini, local=False
```

### Common Errors

#### Error: "OpenAI selected but OPENAI_API_KEY not configured"

**Fix:** Add your API key to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

#### Error: "Failed to initialize OpenAI: Invalid API key"

**Fix:** Check your API key is correct and has credits

#### Error: "No LLM backend available"

**Only happens with LOCAL=1**
**Fix:** Install Ollama or check it's running

---

## 📝 Summary: What to Set in .env

### For ChatGPT (Recommended):
```bash
LOCAL=0
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
```

### For Local (Ollama):
```bash
LOCAL=1
LOCAL_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

---

## ✅ Verification Checklist

After setting up, verify:

- [ ] `.env` file exists with `LOCAL` and keys
- [ ] Log shows: `Configuration loaded: LOCAL=...`
- [ ] Log shows: `✓ LLM backend initialized: backend=...`
- [ ] No error: "llama3.1:8b"
- [ ] No error: "No LLM backend available"
- [ ] Streamlit app loads without LLM errors
- [ ] Can ask a question and get an answer

---

**All fixed! Your OpenAI/ChatGPT backend should work reliably now.** 🎉

