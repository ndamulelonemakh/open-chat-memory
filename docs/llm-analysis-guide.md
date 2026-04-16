# LLM-Powered Chat Analysis

Advanced conversation-level analysis using OpenAI's Responses API with GPT-4o-mini.

## Overview

This script provides deep semantic analysis of your chat history by:
- Analyzing conversations (not individual messages) for token efficiency
- Extracting themes, use cases, and complexity patterns
- Comparing ChatGPT vs Claude usage patterns
- Generating actionable insights about how you use each platform

## Features

### Conversation-Level Analysis
- Aggregates messages into conversations (3+ messages minimum)
- Samples top conversations by message count
- Efficient token usage by analyzing summaries

### LLM-Powered Insights
- **Theme Extraction**: Top 5 themes per platform with frequency
- **Use Case Detection**: Identifies coding, writing, research, debugging, etc.
- **Complexity Assessment**: Beginner/intermediate/advanced distribution
- **Platform Comparison**: Unique strengths and preferences

### Output
- JSON file with structured analysis: `data/figures/llm_conversation_analysis.json`
- Console output with key findings

## Usage

### Prerequisites

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Install required packages
pip install openai pandas
```

### Run Analysis

```bash
python analyze_chats_llm_v2.py
```

### Expected Output

```
🤖 Starting LLM-Powered Conversation Analysis...

📥 Loading chat data...
   ChatGPT: 28,269 messages
   Claude: 8,134 messages

📋 Preparing conversation summaries...
   ChatGPT: 1,234 conversations (3+ messages)
   Claude: 567 conversations (3+ messages)

   📊 Analyzing CHATGPT conversations...
      Processing 30/30...
      ✅ Analyzed 30 conversations

   📊 Analyzing CLAUDE conversations...
      Processing 30/30...
      ✅ Analyzed 30 conversations

   🔍 Comparing platforms...

✅ Analysis complete! Results saved to: data/figures/llm_conversation_analysis.json
```

## Configuration

Edit these constants in the script:

```python
MODEL = "gpt-4o-mini"  # OpenAI model to use
sample_size = 30       # Number of conversations to analyze per platform
```

## Token Efficiency

The script is designed for efficiency:
- Analyzes **conversations** instead of individual messages
- Samples top conversations by message count
- Limits query text to first 10 messages per conversation
- Truncates long content to 2000 characters
- Uses GPT-4o-mini for cost efficiency

**Estimated cost per run**: ~$0.10 - $0.50 (depends on conversation length)

## Output Structure

```json
{
  "chatgpt_analysis": {
    "themes": [...],
    "use_cases": [...],
    "complexity": {...},
    "insights": "..."
  },
  "claude_analysis": {
    "themes": [...],
    "use_cases": [...],
    "complexity": {...},
    "insights": "..."
  },
  "platform_comparison": {
    "chatgpt_strengths": [...],
    "claude_strengths": [...],
    "use_case_differences": {...},
    "key_findings": "..."
  },
  "metadata": {
    "model": "gpt-4o-mini",
    "chatgpt_conversations_analyzed": 30,
    "claude_conversations_analyzed": 30
  }
}
```

## Differences from `analyze_chats_llm.py`

| Feature | analyze_chats_llm.py | analyze_chats_llm_v2.py |
|---------|---------------------|------------------------|
| API | Chat Completions API | **Responses API** |
| Granularity | Message-level | **Conversation-level** |
| Token Efficiency | Lower | **Higher** |
| Model | gpt-4o-mini | **gpt-4o-mini** |
| Sample Size | 100 messages | **30 conversations** |
| Output Format | JSON | **JSON** |

## Tips

1. **Start Small**: Use `sample_size=10` for testing
2. **Monitor Costs**: Check OpenAI usage dashboard
3. **Adjust Filters**: Modify `message_count >= 3` threshold
4. **Custom Analysis**: Edit prompts in `analyze_conversation_with_llm()` and `extract_platform_themes()`

## Troubleshooting

**Error: OPENAI_API_KEY not set**
```bash
export OPENAI_API_KEY="sk-..."
```

**Error: No conversations found**
- Check that your data files exist in `data/staging/`
- Verify conversations have 3+ messages
- Lower the `message_count` threshold

**Rate Limit Errors**
- Reduce `sample_size`
- Add delays between API calls
- Check your OpenAI tier limits

## Next Steps

After running the analysis:
1. Review `data/figures/llm_conversation_analysis.json`
2. Compare insights with visual analysis from `analyze_chats.py`
3. Use findings to optimize your AI usage patterns
4. Share insights with your team

## License

Same as main project.
