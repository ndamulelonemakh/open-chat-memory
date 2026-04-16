# Analysis Tools Documentation

This directory contains documentation and example scripts for analyzing parsed chat history.

## Example Analysis Scripts

Located in `docs/examples/`, these scripts demonstrate what you can do with parsed conversations.

### 1. EDA Analysis (`examples/eda_analysis.py`)
**Purpose:** Statistical and visual exploratory data analysis of chat history

**Features:**
- Temporal patterns (usage by hour, day, month)
- Conversation metrics (length, duration, frequency)
- Message length distributions
- Word clouds by platform and year
- Platform comparison visualizations

**Output:** PNG visualizations in `data/figures/`

**Documentation:** [eda-analysis-guide.md](./eda-analysis-guide.md)

---

### 2. LLM Conversation Analysis (`examples/llm_conversation_analysis.py`)
**Purpose:** Advanced AI-powered semantic analysis using an LLM.

**Features:**
- Topic extraction and categorization
- Sentiment analysis
- Key insights identification
- Evolution patterns over time
- Conversation-level semantic understanding

**Output:** JSON results in `data/figures/llm_conversation_analysis.json`

**Documentation:** [llm-analysis-guide.md](./llm-analysis-guide.md)

**Requirements:** OpenAI API key (set `OPENAI_API_KEY` environment variable)

---

## Quick Start

```bash
# Run statistical EDA
python docs/examples/eda_analysis.py

# Run LLM-powered analysis (requires OpenAI API key)
export OPENAI_API_KEY="your-key-here"
python docs/examples/llm_conversation_analysis.py
```

## Scripts Overview

For detailed information about all analysis scripts and their capabilities, see:
[analysis-scripts-overview.md](./analysis-scripts-overview.md)

## Other Documentation

- [Adding New Parsers](./adding-parsers.md)
- [CLI Usage](./cli.md)
- [Main Project Documentation](./Index.md)
