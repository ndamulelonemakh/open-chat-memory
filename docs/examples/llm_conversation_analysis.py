#!/usr/bin/env python3
"""
Advanced LLM-Powered Chat Analysis (Conversation-Level)
Uses OpenAI Responses API (GPT-4o-mini) for efficient conversation-level semantic analysis
"""

import json
import os
from pathlib import Path

import pandas as pd
from openai import OpenAI

DATA_DIR = Path("data/staging")
OUTPUT_DIR = Path("data/figures")
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "gpt-5-mini"


def get_openai_client():
    """Initialize OpenAI client with API key check"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def load_chats(filepath: Path) -> pd.DataFrame:
    """Load JSONL chat data"""
    data = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(data)


def get_conversation_summaries(df: pd.DataFrame, platform: str) -> pd.DataFrame:
    """Aggregate messages into conversation-level summaries"""
    user_role = "user" if platform == "chatgpt" else "human"

    conversations = (
        df[df["role"] == user_role]
        .groupby("conversation_id")
        .agg(
            {
                "content": lambda x: " | ".join(x.astype(str).tolist()[:10]),
                "title": "first",
                "conversation_create_time": "first",
                "message_id": "count",
            }
        )
        .rename(columns={"message_id": "message_count", "content": "user_queries"})
        .reset_index()
    )

    conversations = conversations[conversations["message_count"] >= 3]
    conversations = conversations.sort_values("message_count", ascending=False)

    return conversations


def analyze_conversation_with_llm(client, title: str, queries: str, platform: str) -> dict:
    """Analyze a single conversation using Responses API"""

    input_text = f"""Platform: {platform.upper()}
Conversation Title: {title}
User Queries (first 10): {queries[:2000]}

Analyze this conversation and identify:
1. Primary topic/domain (1-3 words)
2. Use case category (e.g., coding, writing, research, learning, debugging, design)
3. Complexity level (beginner/intermediate/advanced)
4. Key intent (what was the user trying to achieve?)
"""

    try:
        response = client.responses.create(model=MODEL, input=input_text)

        return {
            "analysis": response.output_text if hasattr(response, "output_text") else str(response),
            "platform": platform,
            "title": title,
        }
    except Exception as e:
        print(f"   ⚠️  Error analyzing conversation '{title}': {e}")
        return {"analysis": f"Error: {str(e)}", "platform": platform, "title": title}


def extract_platform_themes(client, conversations: pd.DataFrame, platform: str, sample_size: int = 50) -> dict:
    """Extract themes from top conversations per platform"""
    print(f"\n   📊 Analyzing {platform.upper()} conversations...")

    sampled_convs = conversations.head(sample_size)

    all_summaries = []
    for idx, row in sampled_convs.iterrows():
        print(f"      Processing {idx + 1}/{len(sampled_convs)}...", end="\r")
        analysis = analyze_conversation_with_llm(client, row["title"], row["user_queries"], platform)
        all_summaries.append(
            {
                "title": row["title"],
                "message_count": row["message_count"],
                "analysis": analysis["analysis"],
                "date": row["conversation_create_time"],
            }
        )

    print(f"\n      ✅ Analyzed {len(all_summaries)} conversations")

    aggregate_prompt = f"""Based on these {len(all_summaries)} conversation analyses for {platform.upper()},
provide an aggregate summary with:

1. Top 5 themes/topics (with frequency %)
2. Primary use cases (ranked)
3. Complexity distribution (beginner/intermediate/advanced %)
4. Key insights about how this platform is used

Conversation Analyses:
{json.dumps(all_summaries[:30], indent=2)}

Respond in JSON format with keys: themes, use_cases, complexity, insights
"""

    try:
        response = client.responses.create(model=MODEL, input=aggregate_prompt)

        result = response.output_text if hasattr(response, "output_text") else str(response)

        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError:
            return {
                "raw_response": result,
                "themes": "See raw_response",
                "use_cases": "See raw_response",
                "complexity": "See raw_response",
                "insights": result,
            }
    except Exception as e:
        print(f"   ⚠️  Error creating aggregate summary: {e}")
        return {"error": str(e)}


def compare_platforms(client, chatgpt_themes: dict, claude_themes: dict) -> dict:
    """Compare usage patterns across platforms"""
    print("\n   🔍 Comparing platforms...")

    comparison_prompt = f"""Compare ChatGPT vs Claude usage based on these analyses:

ChatGPT Summary:
{json.dumps(chatgpt_themes, indent=2)}

Claude Summary:
{json.dumps(claude_themes, indent=2)}

Provide a comparison highlighting:
1. Unique strengths of each platform
2. Different use case preferences
3. Complexity differences
4. Notable patterns or trends

Respond in JSON format with keys: chatgpt_strengths, claude_strengths, use_case_differences,
complexity_comparison, key_findings
"""

    try:
        response = client.responses.create(model=MODEL, input=comparison_prompt)

        result = response.output_text if hasattr(response, "output_text") else str(response)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"comparison": result}
    except Exception as e:
        print(f"   ⚠️  Error comparing platforms: {e}")
        return {"error": str(e)}


def main():
    """Main analysis pipeline"""
    print("🤖 Starting LLM-Powered Conversation Analysis...")

    try:
        client = get_openai_client()
    except ValueError as e:
        print(f"❌ Error: {e}")
        return

    print("\n📥 Loading chat data...")
    chatgpt_df = load_chats(DATA_DIR / "chatgpt_messages.jsonl")
    claude_df = load_chats(DATA_DIR / "claude_messages.jsonl")
    print(f"   ChatGPT: {len(chatgpt_df):,} messages")
    print(f"   Claude: {len(claude_df):,} messages")

    print("\n📋 Preparing conversation summaries...")
    chatgpt_convs = get_conversation_summaries(chatgpt_df, "chatgpt")
    claude_convs = get_conversation_summaries(claude_df, "claude")
    print(f"   ChatGPT: {len(chatgpt_convs)} conversations (3+ messages)")
    print(f"   Claude: {len(claude_convs)} conversations (3+ messages)")

    chatgpt_themes = extract_platform_themes(client, chatgpt_convs, "chatgpt", sample_size=30)
    claude_themes = extract_platform_themes(client, claude_convs, "claude", sample_size=30)

    comparison = compare_platforms(client, chatgpt_themes, claude_themes)

    results = {
        "chatgpt_analysis": chatgpt_themes,
        "claude_analysis": claude_themes,
        "platform_comparison": comparison,
        "metadata": {
            "model": MODEL,
            "chatgpt_conversations_analyzed": len(chatgpt_convs),
            "claude_conversations_analyzed": len(claude_convs),
        },
    }

    output_file = OUTPUT_DIR / "llm_conversation_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Analysis complete! Results saved to: {output_file}")
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    print("\n📊 ChatGPT Analysis:")
    print(json.dumps(chatgpt_themes, indent=2))

    print("\n📊 Claude Analysis:")
    print(json.dumps(claude_themes, indent=2))

    print("\n🔄 Platform Comparison:")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    from dotenv import load_dotenv

    if not load_dotenv():
        print("❌ Error loading .env file")
        exit(1)
    main()
