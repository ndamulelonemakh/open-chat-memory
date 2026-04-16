# Chat History Analysis Scripts - Summary

## 📁 Available Scripts

### 1. `analyze_chats.py` (30KB)
**Statistical & Visual Analysis**

✅ **What it does:**
- Comprehensive EDA (Exploratory Data Analysis)
- Temporal patterns (hourly, daily, monthly)
- Conversation metrics (duration, message counts)
- Content analysis (message lengths, distributions)
- Topic modeling with BERTopic
- Word clouds by platform and year
- Platform comparisons

📊 **Outputs:**
- 13+ PNG visualizations
- Summary statistics JSON
- Interactive HTML plots (BERTopic)

⚡ **Run time:** ~30 seconds
💰 **Cost:** Free

---

### 2. `analyze_chats_llm.py` (10KB)
**Message-Level LLM Analysis** (Chat Completions API)

✅ **What it does:**
- Samples top 100 messages per platform
- Extracts themes using GPT-4o-mini
- Analyzes question types and complexity
- Compares platform usage patterns

📊 **Outputs:**
- JSON with themes and insights
- Console-printed findings

⚡ **Run time:** ~2-3 minutes
💰 **Cost:** ~$0.20-0.40 per run

---

### 3. `analyze_chats_llm_v2.py` (7.6KB) ⭐ **RECOMMENDED**
**Conversation-Level LLM Analysis** (Responses API)

✅ **What it does:**
- Aggregates messages into conversations
- Analyzes top 30 conversations per platform
- Extracts themes, use cases, complexity
- Platform comparison with LLM insights
- **More token-efficient** than v1

📊 **Outputs:**
- `llm_conversation_analysis.json`
- Structured insights with themes, use cases, patterns

⚡ **Run time:** ~1-2 minutes
💰 **Cost:** ~$0.10-0.25 per run (50% cheaper than v1)

---

## 🎯 Which Script to Use?

### Use `analyze_chats.py` when:
- You want comprehensive visualizations
- Statistical analysis is sufficient
- You need word clouds and temporal patterns
- No API costs acceptable
- **Run this first!**

### Use `analyze_chats_llm_v2.py` when:
- You want semantic understanding of conversations
- Need theme extraction and categorization
- Want to understand HOW you use each platform
- Willing to spend ~$0.10-0.25
- **Run this after basic analysis**

### Use `analyze_chats_llm.py` when:
- You need message-level granularity
- Want to analyze specific message patterns
- Legacy option (v2 is better for most cases)

---

## 🚀 Complete Analysis Workflow

```bash
# Step 1: Statistical & Visual Analysis (free)
python analyze_chats.py

# Step 2: Review visualizations
open data/figures/

# Step 3: LLM-Powered Semantic Analysis ($0.10-0.25)
export OPENAI_API_KEY="your-key"
python analyze_chats_llm_v2.py

# Step 4: Review LLM insights
cat data/figures/llm_conversation_analysis.json
```

---

## 📊 Output Files Summary

### From `analyze_chats.py`:
```
data/figures/
├── chatgpt_content.png              # Message length distributions
├── chatgpt_conversations.png        # Conversation metrics
├── chatgpt_temporal.png             # Time-based patterns
├── claude_content.png
├── claude_conversations.png
├── claude_temporal.png
├── platform_comparison.png          # Side-by-side comparison
├── topics_comparison.png            # BERTopic analysis
├── wordcloud_by_platform.png        # ChatGPT vs Claude
├── wordcloud_by_year_chatgpt.png    # Evolution 2023-2025
├── wordcloud_by_year_claude.png     # Evolution 2023-2025
├── wordcloud_by_year.png            # Combined view
└── summary_stats.json               # Numeric summary
```

### From `analyze_chats_llm_v2.py`:
```
data/figures/
└── llm_conversation_analysis.json   # Themes, use cases, insights
```

---

## 🎨 Key Features by Script

| Feature | analyze_chats.py | analyze_chats_llm_v2.py |
|---------|-----------------|------------------------|
| **Word Clouds** | ✅ By platform & year | ❌ |
| **Temporal Patterns** | ✅ Hourly/daily/monthly | ❌ |
| **Topic Modeling** | ✅ BERTopic | ✅ LLM-based themes |
| **Conversation Metrics** | ✅ Duration, counts | ✅ Use case detection |
| **Complexity Analysis** | ❌ | ✅ Beginner/advanced |
| **Platform Comparison** | ✅ Statistical | ✅ Semantic insights |
| **Interactive Plots** | ✅ HTML | ❌ |
| **Cost** | Free | ~$0.10-0.25 |
| **Run Time** | 30 sec | 1-2 min |

---

## 💡 Pro Tips

1. **Always run `analyze_chats.py` first** - it's free and comprehensive
2. **Use `analyze_chats_llm_v2.py` for deeper insights** - worth the $0.10
3. **Exclude tool messages** - both scripts now filter `role='tool'`
4. **Adjust sample sizes** - reduce for faster/cheaper LLM runs
5. **Review together** - combine visual + semantic insights

---

## 🔧 Configuration

### Statistical Analysis (`analyze_chats.py`)
```python
# No configuration needed - runs automatically
# Outputs to: data/figures/
```

### LLM Analysis (`analyze_chats_llm_v2.py`)
```python
MODEL = "gpt-4o-mini"           # OpenAI model
sample_size = 30                # Conversations per platform
min_messages = 3                # Min messages per conversation
```

---

## 📈 Expected Insights

### From Statistical Analysis:
- Peak usage hours and days
- Conversation length distributions
- Message length patterns (user vs AI)
- Topic clusters and keywords
- Platform preference over time

### From LLM Analysis:
- **Themes**: "Python Development", "Azure Cloud", "Data Analysis"
- **Use Cases**: Coding (45%), Research (30%), Writing (25%)
- **Complexity**: Intermediate (60%), Advanced (30%), Beginner (10%)
- **Patterns**: "Heavy API integration questions", "Focus on performance"

---

## 🎓 Next Steps

After running both analyses:

1. ✅ Compare word clouds with LLM themes
2. ✅ Validate temporal patterns with use case evolution
3. ✅ Share insights with team/community
4. ✅ Optimize your AI usage based on findings
5. ✅ Track changes over time (re-run monthly)

---

## 📝 Notes

- All scripts exclude `role='tool'` messages for cleaner analysis
- Conversation-level analysis is more token-efficient than message-level
- Responses API is simpler than Chat Completions API
- Both visual and semantic analysis complement each other perfectly

---

**Created**: October 5, 2025
**Scripts Version**: 
- `analyze_chats.py`: v2.0 (with word clouds)
- `analyze_chats_llm_v2.py`: v1.0 (Responses API, conversation-level)
