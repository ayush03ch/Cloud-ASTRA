# 3-Tier Security Detection System

## Overview

Cloud-ASTRA now uses a **3-tier cascading detection system** for comprehensive security analysis:

```
TIER 1: Intent-Aware Rules (Fast, Deterministic)
    ↓ (if insufficient findings)
TIER 2: RAG Knowledge Base Search (Placeholder)
    ↓ (if no results)
TIER 3: LLM Analysis with Gemini API (Deep Analysis)
```

## Architecture

### Tier 1: Intent-Aware Rules ✅

- **Hardcoded Python rules** for each service (S3, Lambda, EC2, IAM)
- Fast execution (milliseconds)
- Deterministic results
- Intent-aware (adapts rules based on resource purpose)
- **Auto-safe flags** for safe automatic fixes

### Tier 2: RAG Security Search 🚧 (Placeholder)

- **Future**: Vector search through security knowledge base
- Will find similar vulnerability patterns from past incidents
- Currently returns empty list (triggers LLM fallback)
- Located in: `agents/utils/rag_security_search.py`

### Tier 3: LLM Analysis with Gemini ✅

- **Google Gemini 1.5 Flash** API integration
- Analyzes resources only when Tier 1/2 find < 3 issues
- Provides deep analysis of complex security patterns
- Returns structured JSON findings
- **Requires `GEMINI_API_KEY` environment variable**

## Setup

### 1. Install Dependencies

```bash
cd Cloud-ASTRA
pip install -r requirements.txt
```

This will install:

- `google-generativeai` - Gemini API client
- All existing dependencies (boto3, Flask, etc.)

### 2. Configure API Key

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
# Get key from: https://makersuite.google.com/app/apikey
```

Edit `.env`:

```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Load Environment Variables

Add to your Python code or use python-dotenv:

```bash
pip install python-dotenv
```

In your application entry point:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file
```

## Usage Example

```python
from agents.s3_agent.s3_agent import S3Agent

# Initialize agent (will auto-detect Gemini API key)
creds = {
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "aws_session_token": "...",
    "region": "us-east-1"
}

agent = S3Agent(creds)

# Run 3-tier scan
findings = agent.scan(user_intent_input={
    "my-website-bucket": "website hosting",
    "_global_intent": "data storage"
})

# Output will show:
# [S3Agent] TIER 1 (Rules): Found X issues
# [S3Agent] TIER 2 (RAG): Found 0 issues (placeholder)
# [S3Agent] TIER 3 (LLM): Found Y issues
# [S3Agent] Analysis Complete: Z unique findings
```

## Detection Logic

### When does each tier run?

**Tier 1 (Rules)**: Always runs for all resources

**Tier 2 (RAG)**: Always runs (currently returns empty, future implementation)

**Tier 3 (LLM)**: Only runs for resources with < 3 findings from previous tiers

### Example Flow

```
Bucket: "prod-data-encrypted"
├─ Tier 1 (Rules):
│   ✅ Public access blocked
│   ✅ Encryption enabled
│   ✅ Versioning enabled
│   → 3 findings, skip LLM
└─ Result: 3 findings (from rules only)

Bucket: "test-bucket-123"
├─ Tier 1 (Rules):
│   ❌ No encryption
│   → 1 finding, continue to LLM
├─ Tier 2 (RAG):
│   → 0 findings (placeholder)
└─ Tier 3 (LLM):
    🤖 Gemini analyzes full config
    ✅ Missing logging
    ✅ No lifecycle policy
    → 2 additional findings
Result: 3 total findings (1 rule + 2 LLM)
```

## Benefits

✅ **Fast**: Rules execute first, most issues caught immediately  
✅ **Comprehensive**: LLM finds issues rules miss  
✅ **Cost-efficient**: LLM only called when needed  
✅ **Deduplication**: Removes duplicate findings across tiers  
✅ **Extensible**: Easy to add RAG when knowledge base ready

## File Structure

```
agents/
├── utils/
│   ├── llm_security_analyzer.py   # Tier 3: Gemini integration
│   └── rag_security_search.py     # Tier 2: RAG placeholder
├── s3_agent/
│   └── s3_agent.py                # Updated with 3-tier detection
├── lambda_agents/
│   └── lambda_agent.py            # Updated with 3-tier detection
├── ec2_agent/
│   └── ec2_agent.py               # Updated with 3-tier detection
└── iam_agent/
    └── iam_agent.py               # Updated with 3-tier detection
```

## Configuration

### Without Gemini API Key

```bash
# LLM tier will be skipped
[S3Agent] ⚠️  LLM fallback disabled: GEMINI_API_KEY environment variable not set
[S3Agent] TIER 3 (LLM): Skipped - Gemini API not configured
```

### With Gemini API Key

```bash
# LLM tier will be enabled
[S3Agent] ✅ LLM fallback enabled (Gemini)
[LLM] Gemini API initialized successfully
[LLM] Analyzing s3://my-bucket with Gemini...
[LLM] Found 2 issues for my-bucket
```

## Deduplication

Findings are deduplicated across tiers with preference order:

1. **Tier 1 (Rules)** - highest priority
2. **Tier 2 (RAG)** - medium priority
3. **Tier 3 (LLM)** - lowest priority

If the same issue is found by multiple tiers, only the rule-based finding is kept.

## Future Enhancements

### RAG Implementation (Tier 2)

To complete Tier 2, implement `RAGSecuritySearch`:

1. Create security knowledge base (JSON/vector DB)
2. Load embeddings of known vulnerabilities
3. Implement similarity search
4. Return matching security patterns

See `agents/utils/rag_security_search.py` for the placeholder.

## Troubleshooting

### "Import google.generativeai could not be resolved"

**Solution**: Install the dependency

```bash
pip install google-generativeai
```

### "GEMINI_API_KEY environment variable not set"

**Solution**: Set the API key

```bash
export GEMINI_API_KEY="your_key_here"  # Linux/Mac
set GEMINI_API_KEY=your_key_here       # Windows CMD
$env:GEMINI_API_KEY="your_key_here"    # PowerShell
```

### LLM returns empty findings

**Check**:

1. API key is valid
2. Network connectivity to Google AI
3. Gemini API quota not exceeded
4. Check logs for error messages

## API Costs

Gemini 1.5 Flash pricing (as of 2024):

- **Free tier**: 15 requests/minute, 1M requests/day
- **Paid**: ~$0.00025 per 1K characters

For typical usage (10-50 buckets):

- Most findings from Tier 1 (rules) - **Free**
- LLM only for ambiguous cases - **~$0.01 per scan**

## Support

For issues or questions:

1. Check logs for detailed error messages
2. Verify API key is set correctly
3. Test Gemini API directly: https://ai.google.dev/tutorials/python_quickstart
