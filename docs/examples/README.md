# Analysis Examples

This folder contains example scripts demonstrating what you can do with parsed chat conversations.

## Available Examples

### 1. `eda_analysis.py` - Statistical EDA
Exploratory Data Analysis with visualizations:
- Temporal patterns (hourly, daily, monthly usage)
- Conversation metrics and distributions
- Message length analysis
- Word clouds by platform and year
- Platform comparison charts

**Run:**
```bash
python docs/examples/eda_analysis.py
```

**Output:** PNG visualizations saved to `data/figures/`

**Requirements:** pandas, matplotlib, seaborn, wordcloud

---

### 2. `llm_conversation_analysis.py` - LLM-Powered Insights
Advanced semantic analysis using GPT-4o-mini:
- Automatic topic extraction
- Sentiment analysis
- Key insights identification
- Conversation evolution patterns
- Semantic understanding at conversation level

**Run:**
```bash
export OPENAI_API_KEY="your-key-here"
python docs/examples/llm_conversation_analysis.py
```

**Output:** JSON results saved to `data/figures/llm_conversation_analysis.json`

**Requirements:** openai library, valid OpenAI API key

---

## Prerequisites

Both scripts expect parsed chat data in JSONL format at:
- `data/staging/chatgpt_messages.jsonl`
- `data/staging/claude_messages.jsonl`

Use the main CLI to parse your exports first:
```bash
ocmem parse --provider chatgpt --input path/to/export.zip --out data/staging/chatgpt_messages.jsonl
ocmem parse --provider claude --input path/to/export.zip --out data/staging/claude_messages.jsonl
```

## Documentation

For detailed guides and configuration options:
- [EDA Analysis Guide](../eda-analysis-guide.md)
- [LLM Analysis Guide](../llm-analysis-guide.md)
- [Analysis Tools Index](../analysis-tools-index.md)
