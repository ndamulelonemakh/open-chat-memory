#!/usr/bin/env python3
"""
Chat History EDA: Analyze generative AI usage patterns
Generates beautiful visualizations and LLM-powered insights
"""

import json
import re
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from wordcloud import STOPWORDS, WordCloud

warnings.filterwarnings("ignore")

sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["font.size"] = 11

DATA_DIR = Path("data/staging")
OUTPUT_DIR = Path("data/figures")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_chats(filepath):
    """Load JSONL chat data"""
    data = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(data)


def parse_timestamps(df):
    """Convert timestamps to datetime"""
    df = df.copy()
    for col in ["message_create_time", "conversation_create_time", "message_update_time"]:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            else:
                df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
    return df


def extract_temporal_features(df):
    """Extract time-based features"""
    df = df.copy()
    df["hour"] = df["message_create_time"].dt.hour
    df["day_of_week"] = df["message_create_time"].dt.day_name()
    df["date"] = df["message_create_time"].dt.date
    df["month"] = df["message_create_time"].dt.to_period("M")
    return df


def analyze_conversations(df):
    """Compute conversation-level metrics"""
    conv_stats = (
        df.groupby("conversation_id")
        .agg(
            message_count=("message_id", "count"),
            start_time=("message_create_time", "min"),
            end_time=("message_create_time", "max"),
            title=("title", "first"),
        )
        .reset_index()
    )

    conv_stats["duration_minutes"] = (conv_stats["end_time"] - conv_stats["start_time"]).dt.total_seconds() / 60

    return conv_stats


def plot_temporal_patterns(df, platform):
    """Visualize usage over time"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Daily activity
    daily = df.groupby("date").size()
    axes[0, 0].plot(daily.index, daily.values, linewidth=2, color="#2E86AB")
    axes[0, 0].fill_between(daily.index, daily.values, alpha=0.3, color="#2E86AB")
    axes[0, 0].set_title(f"{platform}: Messages Over Time", fontsize=14, fontweight="bold")
    axes[0, 0].set_xlabel("Date")
    axes[0, 0].set_ylabel("Messages")
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Hourly heatmap
    hourly_dow = df.groupby(["day_of_week", "hour"]).size().unstack(fill_value=0)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hourly_dow = hourly_dow.reindex([d for d in day_order if d in hourly_dow.index])

    sns.heatmap(hourly_dow, cmap="YlOrRd", annot=False, fmt="d", ax=axes[0, 1], cbar_kws={"label": "Messages"})
    axes[0, 1].set_title(f"{platform}: Activity Heatmap", fontsize=14, fontweight="bold")
    axes[0, 1].set_xlabel("Hour of Day")
    axes[0, 1].set_ylabel("")

    # Hourly distribution
    hourly = df.groupby("hour").size()
    axes[1, 0].bar(hourly.index, hourly.values, color="#A23B72", alpha=0.8, edgecolor="black")
    axes[1, 0].set_title(f"{platform}: Messages by Hour", fontsize=14, fontweight="bold")
    axes[1, 0].set_xlabel("Hour of Day")
    axes[1, 0].set_ylabel("Messages")
    axes[1, 0].set_xticks(range(24))

    # Day of week
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_counts = df["day_of_week"].value_counts().reindex(dow_order, fill_value=0)
    axes[1, 1].bar(range(len(dow_counts)), dow_counts.values, color="#F18F01", alpha=0.8, edgecolor="black")
    axes[1, 1].set_title(f"{platform}: Messages by Day of Week", fontsize=14, fontweight="bold")
    axes[1, 1].set_xlabel("Day of Week")
    axes[1, 1].set_ylabel("Messages")
    axes[1, 1].set_xticks(range(len(dow_counts)))
    axes[1, 1].set_xticklabels(dow_counts.index, rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{platform.lower()}_temporal.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_conversation_metrics(conv_stats, platform):
    """Visualize conversation-level insights"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Message count distribution
    axes[0, 0].hist(conv_stats["message_count"], bins=50, color="#06A77D", alpha=0.7, edgecolor="black")
    axes[0, 0].set_title(f"{platform}: Messages per Conversation", fontsize=14, fontweight="bold")
    axes[0, 0].set_xlabel("Messages")
    axes[0, 0].set_ylabel("Conversations")
    axes[0, 0].axvline(conv_stats["message_count"].median(), color="red", linestyle="--", linewidth=2, label="Median")
    axes[0, 0].legend()

    # Duration distribution
    duration_filtered = conv_stats[conv_stats["duration_minutes"] > 0]
    axes[0, 1].hist(duration_filtered["duration_minutes"], bins=50, color="#D62828", alpha=0.7, edgecolor="black")
    axes[0, 1].set_title(f"{platform}: Conversation Duration", fontsize=14, fontweight="bold")
    axes[0, 1].set_xlabel("Duration (minutes)")
    axes[0, 1].set_ylabel("Conversations")
    axes[0, 1].set_xlim(0, duration_filtered["duration_minutes"].quantile(0.95))

    # Message count vs duration
    valid_conv = conv_stats[conv_stats["duration_minutes"] > 0]
    axes[1, 0].scatter(valid_conv["message_count"], valid_conv["duration_minutes"], alpha=0.5, s=30, color="#003049")
    axes[1, 0].set_title(f"{platform}: Messages vs Duration", fontsize=14, fontweight="bold")
    axes[1, 0].set_xlabel("Messages")
    axes[1, 0].set_ylabel("Duration (minutes)")
    axes[1, 0].set_ylim(0, valid_conv["duration_minutes"].quantile(0.95))

    # Top conversation lengths
    top_convs = conv_stats.nlargest(15, "message_count")
    axes[1, 1].barh(
        range(len(top_convs)), top_convs["message_count"].values, color="#8338EC", alpha=0.8, edgecolor="black"
    )
    axes[1, 1].set_title(f"{platform}: Top 15 Longest Conversations", fontsize=14, fontweight="bold")
    axes[1, 1].set_xlabel("Messages")
    axes[1, 1].set_ylabel("Conversation Rank")
    axes[1, 1].invert_yaxis()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{platform.lower()}_conversations.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_content_metrics(df, platform):
    """Analyze message content"""
    df = df.copy()
    df = df[df["role"] != "tool"]
    df["content_length"] = df["content"].fillna("").astype(str).str.len()
    user_msgs = df[df["role"].isin(["user", "human"])]
    ai_msgs = df[df["role"].isin(["assistant"])]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # User message length
    axes[0, 0].hist(user_msgs["content_length"], bins=50, color="#3A86FF", alpha=0.7, edgecolor="black", label="User")
    axes[0, 0].set_title(f"{platform}: User Message Length", fontsize=14, fontweight="bold")
    axes[0, 0].set_xlabel("Characters")
    axes[0, 0].set_ylabel("Messages")
    axes[0, 0].set_xlim(0, user_msgs["content_length"].quantile(0.95))
    axes[0, 0].axvline(user_msgs["content_length"].median(), color="red", linestyle="--", linewidth=2, label="Median")
    axes[0, 0].legend()

    # AI message length
    axes[0, 1].hist(ai_msgs["content_length"], bins=50, color="#FF006E", alpha=0.7, edgecolor="black", label="AI")
    axes[0, 1].set_title(f"{platform}: AI Response Length", fontsize=14, fontweight="bold")
    axes[0, 1].set_xlabel("Characters")
    axes[0, 1].set_ylabel("Messages")
    axes[0, 1].set_xlim(0, ai_msgs["content_length"].quantile(0.95))
    axes[0, 1].axvline(ai_msgs["content_length"].median(), color="red", linestyle="--", linewidth=2, label="Median")
    axes[0, 1].legend()

    # Role distribution
    role_counts = df["role"].value_counts()
    axes[1, 0].pie(
        role_counts.values,
        labels=role_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#06FFA5", "#FFBE0B", "#FB5607"],
    )
    axes[1, 0].set_title(f"{platform}: Message Role Distribution", fontsize=14, fontweight="bold")

    # Length comparison boxplot
    length_data = [user_msgs["content_length"].dropna(), ai_msgs["content_length"].dropna()]
    bp = axes[1, 1].boxplot(
        length_data, labels=["User", "AI"], patch_artist=True, medianprops={"color": "red", "linewidth": 2}
    )
    for patch, color in zip(bp["boxes"], ["#3A86FF", "#FF006E"], strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    axes[1, 1].set_title(f"{platform}: Message Length Comparison", fontsize=14, fontweight="bold")
    axes[1, 1].set_ylabel("Characters")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{platform.lower()}_content.png", dpi=300, bbox_inches="tight")
    plt.close()


def extract_topics(df, top_n=20):
    """Simple topic extraction from titles"""
    titles = df["title"].dropna().value_counts().head(top_n)
    return titles


def plot_topics(chatgpt_topics, claude_topics):
    """Visualize top topics"""
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # ChatGPT topics
    axes[0].barh(range(len(chatgpt_topics)), chatgpt_topics.values, color="#10B981", alpha=0.8, edgecolor="black")
    axes[0].set_yticks(range(len(chatgpt_topics)))
    axes[0].set_yticklabels([t[:50] for t in chatgpt_topics.index], fontsize=9)
    axes[0].set_title("ChatGPT: Top 20 Topics", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Occurrences")
    axes[0].invert_yaxis()

    # Claude topics
    axes[1].barh(range(len(claude_topics)), claude_topics.values, color="#8B5CF6", alpha=0.8, edgecolor="black")
    axes[1].set_yticks(range(len(claude_topics)))
    axes[1].set_yticklabels([t[:50] for t in claude_topics.index], fontsize=9)
    axes[1].set_title("Claude: Top 20 Topics", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Occurrences")
    axes[1].invert_yaxis()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "topics_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()


def clean_text_for_wordcloud(text):
    """Clean and normalize text for word cloud generation"""
    if pd.isna(text) or text is None:
        return ""

    text = str(text).lower()
    # Remove URLs
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)
    # Remove code blocks (markdown style)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", "", text)
    # Remove special characters but keep letters and spaces
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def create_wordcloud_by_platform(chatgpt_df, claude_df):
    """Generate side-by-side word clouds for ChatGPT vs Claude"""
    print("   - Generating word clouds by platform...")

    # Custom stopwords
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update(
        [
            "chatgpt",
            "claude",
            "ai",
            "assistant",
            "user",
            "please",
            "would",
            "could",
            "like",
            "want",
            "need",
            "help",
            "thanks",
            "thank",
            "yes",
            "no",
            "use",
            "using",
        ]
    )

    # Get user messages only (more interesting than AI responses)
    chatgpt_user = chatgpt_df[(chatgpt_df["role"] == "user") & (chatgpt_df["role"] != "tool")]["content"].dropna()
    claude_user = claude_df[(claude_df["role"] == "human") & (claude_df["role"] != "tool")]["content"].dropna()

    # Clean and combine text
    chatgpt_text = " ".join([clean_text_for_wordcloud(msg) for msg in chatgpt_user])
    claude_text = " ".join([clean_text_for_wordcloud(msg) for msg in claude_user])

    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    # ChatGPT word cloud
    if chatgpt_text.strip():
        wc_chatgpt = WordCloud(
            width=800,
            height=600,
            background_color="white",
            colormap="Greens",
            stopwords=custom_stopwords,
            max_words=150,
            relative_scaling=0.5,
            min_font_size=10,
        ).generate(chatgpt_text)

        axes[0].imshow(wc_chatgpt, interpolation="bilinear")
        axes[0].set_title("ChatGPT User Queries", fontsize=18, fontweight="bold", pad=20)
        axes[0].axis("off")

    # Claude word cloud
    if claude_text.strip():
        wc_claude = WordCloud(
            width=800,
            height=600,
            background_color="white",
            colormap="Purples",
            stopwords=custom_stopwords,
            max_words=150,
            relative_scaling=0.5,
            min_font_size=10,
        ).generate(claude_text)

        axes[1].imshow(wc_claude, interpolation="bilinear")
        axes[1].set_title("Claude User Queries", fontsize=18, fontweight="bold", pad=20)
        axes[1].axis("off")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "wordcloud_by_platform.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()


def create_wordcloud_by_year(chatgpt_df, claude_df):
    """Generate word clouds by year for each chatbot separately."""
    print("   - Generating word clouds by year for each platform...")

    # Custom stopwords
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update(
        [
            "chatgpt",
            "claude",
            "ai",
            "assistant",
            "user",
            "please",
            "would",
            "could",
            "like",
            "want",
            "need",
            "help",
            "thanks",
            "thank",
            "yes",
            "no",
            "use",
            "using",
        ]
    )

    # Process each platform separately
    for platform_name, df, role_filter in [("ChatGPT", chatgpt_df, "user"), ("Claude", claude_df, "human")]:
        platform_df = df[(df["role"] == role_filter) & (df["role"] != "tool")].copy()

        if len(platform_df) == 0:
            print(f"   ⚠️  No {platform_name} messages available for word clouds by year")
            continue

        # Use conversation_create_time which is already a datetime string
        if "conversation_create_time" not in platform_df.columns:
            print(f"   ⚠️  conversation_create_time column not found for {platform_name}")
            continue

        # Convert conversation_create_time to datetime
        platform_df["conversation_create_time"] = pd.to_datetime(
            platform_df["conversation_create_time"], errors="coerce"
        )

        # Filter out rows with invalid timestamps
        platform_df = platform_df[pd.notna(platform_df["conversation_create_time"])].copy()

        if len(platform_df) == 0:
            print(f"   ⚠️  No valid timestamps for {platform_name} word clouds by year")
            continue

        # Extract year from datetime column
        platform_df["year"] = platform_df["conversation_create_time"].dt.year

        # Get unique years and sort
        years = sorted(platform_df["year"].dropna().unique())

        if len(years) == 0:
            print(f"   ⚠️  No year data available for {platform_name} word clouds")
            continue

        # Create subplots based on number of years
        n_years = len(years)
        fig, axes = plt.subplots(1, n_years, figsize=(7 * n_years, 7))
        if n_years == 1:
            axes = [axes]

        # Color maps for different platforms
        colormap = "viridis" if platform_name == "ChatGPT" else "plasma"

        # Generate word cloud for each year
        for idx, year in enumerate(years):
            year_data = platform_df[platform_df["year"] == year]
            year_text = " ".join([clean_text_for_wordcloud(msg) for msg in year_data["content"].dropna()])

            if len(year_text.strip()) > 0:
                wordcloud = WordCloud(
                    width=800,
                    height=600,
                    background_color="white",
                    stopwords=custom_stopwords,
                    max_words=150,
                    colormap=colormap,
                    relative_scaling=0.5,
                    min_font_size=10,
                ).generate(year_text)

                axes[idx].imshow(wordcloud, interpolation="bilinear")
                axes[idx].set_title(
                    f"{int(year)}\n({len(year_data):,} messages)", fontsize=14, fontweight="bold", pad=15
                )
                axes[idx].axis("off")
            else:
                axes[idx].text(0.5, 0.5, f"No data for {int(year)}", ha="center", va="center", fontsize=12)
                axes[idx].axis("off")

        plt.suptitle(f"{platform_name} Word Clouds by Year", fontsize=18, fontweight="bold", y=0.98)
        plt.tight_layout()

        # Save figure
        output_path = OUTPUT_DIR / f"wordcloud_by_year_{platform_name.lower()}.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        print(f"      {platform_name}: {n_years} years ({', '.join(map(str, map(int, years)))})")


def create_topic_clusters(chatgpt_df, claude_df):
    """Generate BERTopic clustering with interactive visualizations."""
    print("   - Generating BERTopic clusters...")

    try:
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer
    except ImportError:
        print("   ⚠️  BERTopic not installed. Run: pip install bertopic[visualization]")
        return

    for platform_name, df, role_filter in [("ChatGPT", chatgpt_df, "user"), ("Claude", claude_df, "human")]:
        user_msgs = df[(df["role"] == role_filter) & (df["role"] != "tool")].copy()

        if len(user_msgs) < 10:
            print(f"   ⚠️  Not enough {platform_name} messages for topic modeling")
            continue

        docs = user_msgs["content"].dropna().astype(str).tolist()

        if len(docs) < 10:
            print(f"   ⚠️  Not enough valid {platform_name} documents for topic modeling")
            continue

        print(f"      {platform_name}: Processing {len(docs):,} messages...")

        vectorizer_model = CountVectorizer(stop_words="english", min_df=5, max_df=0.8)

        topic_model = BERTopic(
            vectorizer_model=vectorizer_model,
            min_topic_size=30,
            nr_topics="auto",
            calculate_probabilities=False,
            verbose=False,
        )

        try:
            topics, _ = topic_model.fit_transform(docs)

            n_topics = len(set(topics)) - (1 if -1 in topics else 0)
            print(f"      {platform_name}: Found {n_topics} topics")

            fig = topic_model.visualize_topics()
            fig.write_html(str(OUTPUT_DIR / f"topic_clusters_{platform_name.lower()}.html"))

            fig_docs = topic_model.visualize_documents(docs, hide_document_hover=True, hide_annotations=True)
            fig_docs.write_html(str(OUTPUT_DIR / f"topic_documents_{platform_name.lower()}.html"))

            fig_hierarchy = topic_model.visualize_hierarchy()
            fig_hierarchy.write_html(str(OUTPUT_DIR / f"topic_hierarchy_{platform_name.lower()}.html"))

            topic_info = topic_model.get_topic_info()
            topic_info.to_csv(OUTPUT_DIR / f"topic_info_{platform_name.lower()}.csv", index=False)

            print(f"      {platform_name}: Saved interactive HTML visualizations")

        except Exception as e:
            print(f"   ⚠️  Error creating {platform_name} topics: {e}")
            continue


def plot_platform_comparison(chatgpt_df, claude_df, chatgpt_conv, claude_conv):
    """Compare ChatGPT vs Claude usage"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Total messages
    platforms = ["ChatGPT", "Claude"]
    msg_counts = [len(chatgpt_df), len(claude_df)]
    axes[0, 0].bar(platforms, msg_counts, color=["#10B981", "#8B5CF6"], alpha=0.8, edgecolor="black")
    axes[0, 0].set_title("Total Messages", fontsize=14, fontweight="bold")
    axes[0, 0].set_ylabel("Count")
    for i, v in enumerate(msg_counts):
        axes[0, 0].text(i, v + max(msg_counts) * 0.02, f"{v:,}", ha="center", fontweight="bold")

    # Conversations
    conv_counts = [len(chatgpt_conv), len(claude_conv)]
    axes[0, 1].bar(platforms, conv_counts, color=["#10B981", "#8B5CF6"], alpha=0.8, edgecolor="black")
    axes[0, 1].set_title("Total Conversations", fontsize=14, fontweight="bold")
    axes[0, 1].set_ylabel("Count")
    for i, v in enumerate(conv_counts):
        axes[0, 1].text(i, v + max(conv_counts) * 0.02, f"{v:,}", ha="center", fontweight="bold")

    # Avg messages per conversation
    avg_msgs = [chatgpt_conv["message_count"].mean(), claude_conv["message_count"].mean()]
    axes[1, 0].bar(platforms, avg_msgs, color=["#10B981", "#8B5CF6"], alpha=0.8, edgecolor="black")
    axes[1, 0].set_title("Avg Messages per Conversation", fontsize=14, fontweight="bold")
    axes[1, 0].set_ylabel("Messages")
    for i, v in enumerate(avg_msgs):
        axes[1, 0].text(i, v + max(avg_msgs) * 0.02, f"{v:.1f}", ha="center", fontweight="bold")

    # User message length
    chatgpt_user_len = chatgpt_df[chatgpt_df["role"] == "user"]["content"].str.len().median()
    claude_user_len = claude_df[claude_df["role"] == "human"]["content"].str.len().median()
    user_lens = [chatgpt_user_len, claude_user_len]
    axes[1, 1].bar(platforms, user_lens, color=["#10B981", "#8B5CF6"], alpha=0.8, edgecolor="black")
    axes[1, 1].set_title("Median User Message Length", fontsize=14, fontweight="bold")
    axes[1, 1].set_ylabel("Characters")
    for i, v in enumerate(user_lens):
        axes[1, 1].text(i, v + max(user_lens) * 0.02, f"{v:.0f}", ha="center", fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "platform_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()


def generate_summary_stats(chatgpt_df, claude_df, chatgpt_conv, claude_conv):
    """Generate comprehensive summary statistics"""
    # Calculate total time spent
    chatgpt_total_hours = chatgpt_conv["duration_minutes"].sum() / 60
    claude_total_hours = claude_conv["duration_minutes"].sum() / 60

    # Get top 3 longest conversations
    chatgpt_top3 = chatgpt_conv.nlargest(3, "message_count")[["title", "message_count", "start_time"]]
    claude_top3 = claude_conv.nlargest(3, "message_count")[["title", "message_count", "start_time"]]

    # Get bottom 3 shortest conversations (with at least 2 messages)
    chatgpt_bottom3 = chatgpt_conv[chatgpt_conv["message_count"] >= 2].nsmallest(3, "message_count")[
        ["title", "message_count", "start_time"]
    ]
    claude_bottom3 = claude_conv[claude_conv["message_count"] >= 2].nsmallest(3, "message_count")[
        ["title", "message_count", "start_time"]
    ]

    # Get oldest and most recent conversations
    chatgpt_oldest = chatgpt_conv.nsmallest(1, "start_time")[["title", "message_count", "start_time"]].iloc[0]
    chatgpt_newest = chatgpt_conv.nlargest(1, "start_time")[["title", "message_count", "start_time"]].iloc[0]
    claude_oldest = claude_conv.nsmallest(1, "start_time")[["title", "message_count", "start_time"]].iloc[0]
    claude_newest = claude_conv.nlargest(1, "start_time")[["title", "message_count", "start_time"]].iloc[0]

    stats = {
        "ChatGPT": {
            "total_messages": len(chatgpt_df),
            "total_conversations": len(chatgpt_conv),
            "total_hours_spent": round(chatgpt_total_hours, 2),
            "avg_messages_per_conv": chatgpt_conv["message_count"].mean(),
            "median_messages_per_conv": chatgpt_conv["message_count"].median(),
            "avg_conversation_duration_min": chatgpt_conv["duration_minutes"].mean(),
            "most_active_hour": chatgpt_df["hour"].mode().iloc[0],
            "most_active_day": chatgpt_df["day_of_week"].mode().iloc[0],
            "user_msg_median_length": chatgpt_df[chatgpt_df["role"] == "user"]["content"].str.len().median(),
            "ai_msg_median_length": chatgpt_df[chatgpt_df["role"] == "assistant"]["content"].str.len().median(),
            "oldest_conversation": {
                "title": chatgpt_oldest["title"],
                "messages": int(chatgpt_oldest["message_count"]),
                "date": chatgpt_oldest["start_time"].strftime("%Y-%m-%d"),
            },
            "most_recent_conversation": {
                "title": chatgpt_newest["title"],
                "messages": int(chatgpt_newest["message_count"]),
                "date": chatgpt_newest["start_time"].strftime("%Y-%m-%d"),
            },
            "top_3_longest_conversations": [
                {
                    "title": row["title"],
                    "messages": int(row["message_count"]),
                    "date": row["start_time"].strftime("%Y-%m-%d"),
                }
                for _, row in chatgpt_top3.iterrows()
            ],
            "bottom_3_shortest_conversations": [
                {
                    "title": row["title"],
                    "messages": int(row["message_count"]),
                    "date": row["start_time"].strftime("%Y-%m-%d"),
                }
                for _, row in chatgpt_bottom3.iterrows()
            ],
        },
        "Claude": {
            "total_messages": len(claude_df),
            "total_conversations": len(claude_conv),
            "total_hours_spent": round(claude_total_hours, 2),
            "avg_messages_per_conv": claude_conv["message_count"].mean(),
            "median_messages_per_conv": claude_conv["message_count"].median(),
            "avg_conversation_duration_min": claude_conv["duration_minutes"].mean(),
            "most_active_hour": claude_df["hour"].mode().iloc[0] if len(claude_df) > 0 else None,
            "most_active_day": claude_df["day_of_week"].mode().iloc[0] if len(claude_df) > 0 else None,
            "user_msg_median_length": claude_df[claude_df["role"] == "human"]["content"].str.len().median(),
            "ai_msg_median_length": claude_df[claude_df["role"] == "assistant"]["content"].str.len().median(),
            "oldest_conversation": {
                "title": claude_oldest["title"],
                "messages": int(claude_oldest["message_count"]),
                "date": claude_oldest["start_time"].strftime("%Y-%m-%d"),
            },
            "most_recent_conversation": {
                "title": claude_newest["title"],
                "messages": int(claude_newest["message_count"]),
                "date": claude_newest["start_time"].strftime("%Y-%m-%d"),
            },
            "top_3_longest_conversations": [
                {
                    "title": row["title"],
                    "messages": int(row["message_count"]),
                    "date": row["start_time"].strftime("%Y-%m-%d"),
                }
                for _, row in claude_top3.iterrows()
            ],
            "bottom_3_shortest_conversations": [
                {
                    "title": row["title"],
                    "messages": int(row["message_count"]),
                    "date": row["start_time"].strftime("%Y-%m-%d"),
                }
                for _, row in claude_bottom3.iterrows()
            ],
        },
    }

    with open(OUTPUT_DIR / "summary_stats.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    return stats


def main():
    print("🚀 Starting Chat History EDA...")

    # Load data
    print("\n📥 Loading chat data...")
    chatgpt_df = load_chats(DATA_DIR / "chatgpt_messages.jsonl")
    claude_df = load_chats(DATA_DIR / "claude_messages.jsonl")
    print(f"   ChatGPT: {len(chatgpt_df):,} messages")
    print(f"   Claude: {len(claude_df):,} messages")

    # Parse timestamps
    print("\n⏰ Parsing timestamps...")
    chatgpt_df = parse_timestamps(chatgpt_df)
    claude_df = parse_timestamps(claude_df)

    # Extract temporal features
    print("\n📅 Extracting temporal features...")
    chatgpt_df = extract_temporal_features(chatgpt_df)
    claude_df = extract_temporal_features(claude_df)

    # Analyze conversations
    print("\n💬 Analyzing conversations...")
    chatgpt_conv = analyze_conversations(chatgpt_df)
    claude_conv = analyze_conversations(claude_df)

    # Generate visualizations
    print("\n📊 Generating visualizations...")
    print("   - Temporal patterns...")
    plot_temporal_patterns(chatgpt_df, "ChatGPT")
    plot_temporal_patterns(claude_df, "Claude")

    print("   - Conversation metrics...")
    plot_conversation_metrics(chatgpt_conv, "ChatGPT")
    plot_conversation_metrics(claude_conv, "Claude")

    print("   - Content analysis...")
    plot_content_metrics(chatgpt_df, "ChatGPT")
    plot_content_metrics(claude_df, "Claude")

    print("   - Topic analysis...")
    chatgpt_topics = extract_topics(chatgpt_df)
    claude_topics = extract_topics(claude_df)
    plot_topics(chatgpt_topics, claude_topics)

    print("   - Platform comparison...")
    plot_platform_comparison(chatgpt_df, claude_df, chatgpt_conv, claude_conv)

    print("   - Word clouds...")
    create_wordcloud_by_platform(chatgpt_df, claude_df)
    create_wordcloud_by_year(chatgpt_df, claude_df)

    print("   - Topic clustering...")
    create_topic_clusters(chatgpt_df, claude_df)

    # Generate summary stats
    print("\n📈 Generating summary statistics...")
    stats = generate_summary_stats(chatgpt_df, claude_df, chatgpt_conv, claude_conv)

    print("\n" + "=" * 60)
    print("KEY INSIGHTS")
    print("=" * 60)
    for platform, metrics in stats.items():
        print(f"\n{platform}:")
        for key, value in metrics.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

    print(f"\n✅ Analysis complete! Check '{OUTPUT_DIR}' for visualizations")
    print("📁 Generated files:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"   - {file.name}")


if __name__ == "__main__":
    main()
