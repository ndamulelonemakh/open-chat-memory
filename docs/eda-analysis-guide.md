# Chat History EDA Analysis

## Overview
This analysis provides deep insights into generative AI usage patterns from ChatGPT and Claude conversation history.

## Quick Start
```bash
# Install dependencies
pip install matplotlib seaborn pandas

# Run analysis
python analyze_chats.py
```

## Generated Outputs
All visualizations and stats are saved to `analysis_output/`:

### Visualizations
1. **Temporal Patterns** (`*_temporal.png`)
   - Daily message activity timeline
   - Hourly heatmap by day of week
   - Messages by hour distribution
   - Weekly activity patterns

2. **Conversation Metrics** (`*_conversations.png`)
   - Messages per conversation distribution
   - Conversation duration analysis
   - Message count vs duration scatter
   - Top 15 longest conversations

3. **Content Analysis** (`*_content.png`)
   - User message length distribution
   - AI response length distribution
   - Role distribution pie chart
   - Length comparison boxplots

4. **Topics** (`topics_comparison.png`)
   - Top 20 most discussed topics per platform

5. **Platform Comparison** (`platform_comparison.png`)
   - Total messages comparison
   - Conversation counts
   - Average messages per conversation
   - Median user message length

### Summary Statistics
`summary_stats.json` contains comprehensive metrics:
- Total messages and conversations
- Average/median messages per conversation
- Average conversation duration
- Peak usage hours and days
- Message length statistics

## Key Insights

### ChatGPT Usage
- **28,269 messages** across **2,122 conversations**
- Average **13.3 messages per conversation** (median: 8)
- Most active on **Mondays** at **midnight**
- Users write shorter queries (median: 90 chars)
- AI responses are detailed (median: 1,218 chars)

### Claude Usage
- **8,134 messages** across **762 conversations**  
- Average **10.7 messages per conversation** (median: 6)
- Most active on **Thursdays** at **11 PM**
- Users write longer queries (median: 116 chars)
- AI responses are very detailed (median: 2,209 chars)

### Platform Differences
- **ChatGPT** has ~3.5x more messages and conversations
- **ChatGPT** conversations are longer on average
- **Claude** users write more detailed queries
- **Claude** responses are significantly longer (1.8x)
- Different peak usage patterns suggest different use cases

## Script Features
- **Lean & efficient**: Minimal comments, high-impact analysis
- **Beautiful plots**: Professional visualizations with clear insights
- **Comprehensive metrics**: Temporal, conversational, and content analysis
- **Easy to extend**: Add custom analysis or integrate LLM insights

## Next Steps for LLM-Powered Insights
To add deeper text analysis using Claude API:

```python
import anthropic

def analyze_topics_with_llm(messages_sample):
    """Use Claude to extract themes from conversations"""
    client = anthropic.Anthropic(api_key="your-key")
    
    # Sample 50 representative messages
    sample = messages_sample.sample(min(50, len(messages_sample)))
    content = "\n\n".join(sample['content'].tolist())
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Analyze these user messages and identify:
1. Top 5 themes/topics
2. Common question types
3. Technical domains mentioned
4. User intent patterns

Messages:
{content[:10000]}"""
        }]
    )
    
    return response.content[0].text
```

## Data Privacy Note
Content normalization is minimal (basic string cleaning) since LLMs handle text variations well. No excessive preprocessing needed for analysis.
