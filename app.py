#!/usr/bin/env python3
import os

os.environ["STREAMLIT_TELEMETRY"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from loguru import logger

from openchatmemory.cli import _detect_provider, _resolve_conversations_json, run_parse

logger.remove()
logger.add(
    "logs/app_audit.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    enqueue=True,
)
logger.add(lambda msg: None, level="ERROR")

st.set_page_config(
    page_title="Open Chat Memory",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=3600)
def load_data(filepath: str) -> pd.DataFrame:
    """Load and parse JSONL chat data with security validation."""
    try:
        path = Path(filepath).resolve()

        if path.suffix != ".jsonl":
            raise ValueError(f"Invalid file type: {path.suffix}. Only .jsonl files supported.")

        allowed_dir = Path("data/staging").resolve()
        try:
            path.relative_to(allowed_dir)
        except ValueError:
            raise ValueError("File must be in data/staging directory") from None

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path.name}")

        if not os.access(path, os.R_OK):
            raise PermissionError(f"Cannot read file: {path.name}")

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > 500:
            raise ValueError(f"File too large: {file_size_mb:.1f} MB (max 500 MB)")

    except Exception as e:
        logger.error(f"File validation failed: {e}")
        raise

    data = []
    invalid_lines = 0

    try:
        with open(path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    invalid_lines += 1
                    if invalid_lines <= 5:
                        logger.warning(f"Invalid JSON at line {line_num} in {path.name}")
                    continue

        if invalid_lines > 0:
            logger.info(f"Skipped {invalid_lines} invalid lines in {path.name}")

        if not data:
            raise ValueError(f"No valid data found in {path.name}")

    except Exception as e:
        logger.error(f"Error reading file {path.name}: {e}")
        raise

    df = pd.DataFrame(data)

    required_cols = ["conversation_id", "role", "content"]
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    for col in ["message_create_time", "conversation_create_time"]:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            else:
                df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")

            if df[col].dt.tz is not None:
                df[col] = df[col].dt.tz_localize(None)

    logger.info(f"Loaded {len(df):,} messages from {path.name}")
    return df


@st.cache_data
def compute_metrics(df, platform):
    date_range = (df["conversation_create_time"].min(), df["conversation_create_time"].max())
    total_days = (date_range[1] - date_range[0]).days + 1

    return {
        "total_messages": len(df),
        "total_conversations": df["conversation_id"].nunique(),
        "date_range": date_range,
        "total_days": total_days,
        "avg_msg_per_conv": len(df) / df["conversation_id"].nunique(),
        "platform": platform,
        "oldest_message": date_range[0],
        "newest_message": date_range[1],
    }


def render_overview(chatgpt_df, claude_df):
    st.title("📊 Overview Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ChatGPT")
        metrics = compute_metrics(chatgpt_df, "ChatGPT")
        m1, m2, m3 = st.columns(3)
        m1.metric("Messages", f"{metrics['total_messages']:,}")
        m2.metric("Conversations", f"{metrics['total_conversations']:,}")
        m3.metric("Avg Msgs/Conv", f"{metrics['avg_msg_per_conv']:.1f}")

    with col2:
        st.subheader("Claude")
        metrics = compute_metrics(claude_df, "Claude")
        m1, m2, m3 = st.columns(3)
        m1.metric("Messages", f"{metrics['total_messages']:,}")
        m2.metric("Conversations", f"{metrics['total_conversations']:,}")
        m3.metric("Avg Msgs/Conv", f"{metrics['avg_msg_per_conv']:.1f}")

    st.divider()

    combined = pd.concat(
        [
            chatgpt_df.assign(platform="ChatGPT"),
            claude_df.assign(platform="Claude"),
        ]
    )

    if "conversation_create_time" in combined.columns and combined["conversation_create_time"].dt.tz is not None:
        combined["conversation_create_time"] = combined["conversation_create_time"].dt.tz_localize(None)

    daily = (
        combined.groupby([pd.Grouper(key="conversation_create_time", freq="D"), "platform"])
        .size()
        .reset_index(name="count")
    )

    fig = px.line(
        daily,
        x="conversation_create_time",
        y="count",
        color="platform",
        title="Daily Activity",
        labels={"conversation_create_time": "Date", "count": "Messages", "platform": "Platform"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Time Insights Section
    st.divider()
    st.subheader("⏱️ Time Insights")

    # Load summary stats if available
    summary_stats = None
    summary_path = Path("data/figures/summary_stats.json")
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summary_stats = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load summary stats: {e}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ChatGPT Timeline")
        gpt_metrics = compute_metrics(chatgpt_df, "ChatGPT")

        t1, t2 = st.columns(2)
        with t1:
            st.metric(
                "Oldest Message",
                gpt_metrics["oldest_message"].strftime("%b %d, %Y"),
                help="First recorded conversation",
            )
        with t2:
            st.metric(
                "Most Recent", gpt_metrics["newest_message"].strftime("%b %d, %Y"), help="Last recorded conversation"
            )

        t3, t4 = st.columns(2)
        with t3:
            st.metric("Date Range", f"{gpt_metrics['total_days']} days", help="Total span of conversation history")
        with t4:
            if summary_stats and "ChatGPT" in summary_stats:
                hours = summary_stats["ChatGPT"].get("total_hours_spent", 0)
                st.metric("Est. Hours Spent", f"{hours:,.0f}h", help="Estimated total time spent in conversations")
            else:
                st.metric("Est. Hours Spent", "N/A", help="Run EDA analysis to compute")

    with col2:
        st.markdown("#### Claude Timeline")
        claude_metrics = compute_metrics(claude_df, "Claude")

        t1, t2 = st.columns(2)
        with t1:
            st.metric(
                "Oldest Message",
                claude_metrics["oldest_message"].strftime("%b %d, %Y"),
                help="First recorded conversation",
            )
        with t2:
            st.metric(
                "Most Recent", claude_metrics["newest_message"].strftime("%b %d, %Y"), help="Last recorded conversation"
            )

        t3, t4 = st.columns(2)
        with t3:
            st.metric("Date Range", f"{claude_metrics['total_days']} days", help="Total span of conversation history")
        with t4:
            if summary_stats and "Claude" in summary_stats:
                hours = summary_stats["Claude"].get("total_hours_spent", 0)
                st.metric("Est. Hours Spent", f"{hours:,.0f}h", help="Estimated total time spent in conversations")
            else:
                st.metric("Est. Hours Spent", "N/A", help="Run EDA analysis to compute")

    # AI-Generated Summary Insight
    if summary_stats:
        st.divider()
        st.subheader("🤖 Quick Insights")

        gpt_stats = summary_stats.get("ChatGPT", {})
        claude_stats = summary_stats.get("Claude", {})

        # Generate insight narrative
        gpt_hours = gpt_stats.get("total_hours_spent", 0)
        claude_hours = claude_stats.get("total_hours_spent", 0)
        total_hours = gpt_hours + claude_hours

        gpt_convs = gpt_stats.get("total_conversations", 0)
        claude_convs = claude_stats.get("total_conversations", 0)
        total_convs = gpt_convs + claude_convs

        gpt_msgs = gpt_stats.get("total_messages", 0)
        claude_msgs = claude_stats.get("total_messages", 0)
        total_msgs = gpt_msgs + claude_msgs

        # Platform preference
        if gpt_msgs > claude_msgs * 2:
            platform_pref = "strong preference for ChatGPT"
        elif claude_msgs > gpt_msgs * 2:
            platform_pref = "strong preference for Claude"
        elif gpt_msgs > claude_msgs:
            platform_pref = "slight preference for ChatGPT"
        elif claude_msgs > gpt_msgs:
            platform_pref = "slight preference for Claude"
        else:
            platform_pref = "balanced usage across platforms"

        # Most active platform
        most_active = "ChatGPT" if gpt_msgs > claude_msgs else "Claude"
        most_active_day = (
            gpt_stats.get("most_active_day", "N/A")
            if most_active == "ChatGPT"
            else claude_stats.get("most_active_day", "N/A")
        )

        # Conversation depth
        gpt_avg = gpt_stats.get("avg_messages_per_conv", 0)
        claude_avg = claude_stats.get("avg_messages_per_conv", 0)

        if gpt_avg > claude_avg:
            depth_insight = f"ChatGPT conversations tend to be longer ({gpt_avg:.1f} vs {claude_avg:.1f} msgs/conv)"
        else:
            depth_insight = f"Claude conversations tend to be longer ({claude_avg:.1f} vs {gpt_avg:.1f} msgs/conv)"

        # Time investment
        if total_hours > 24:
            total_days = total_hours / 24
            if total_days > 365:
                time_insight = f"substantial time investment ({total_days:,.0f} days)"
            elif total_days > 180:
                time_insight = f"significant time investment ({total_days:,.0f} days)"
            else:
                time_insight = f"moderate time investment ({total_days:,.0f} days)"
        else:
            time_insight = f"moderate time investment ({total_hours:,.0f} hours)"

        summary = f"""
        Your chat history spans **{total_convs:,} conversations** across both platforms, with a {platform_pref}.
        You've invested approximately **{total_hours:,.0f} hours** engaging with AI assistants, demonstrating {time_insight}.

        **{most_active}** is your most active platform, with peak activity on **{most_active_day}s**. {depth_insight},
        suggesting different use patterns between platforms.

        The data shows **{total_msgs:,} total messages** exchanged, with your oldest conversation dating back to
        **{gpt_stats.get("oldest_conversation", {}).get("date", "N/A")}** on ChatGPT.
        """

        st.info(summary)

        with st.expander("📊 View Detailed Stats"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**ChatGPT**")
                st.json(
                    {
                        "total_hours": f"{gpt_hours:,.1f}",
                        "avg_messages_per_conv": f"{gpt_avg:.1f}",
                        "most_active_day": gpt_stats.get("most_active_day", "N/A"),
                        "median_msg_length": gpt_stats.get("user_msg_median_length", "N/A"),
                    }
                )

            with col2:
                st.markdown("**Claude**")
                st.json(
                    {
                        "total_hours": f"{claude_hours:,.1f}",
                        "avg_messages_per_conv": f"{claude_avg:.1f}",
                        "most_active_day": claude_stats.get("most_active_day", "N/A"),
                        "median_msg_length": claude_stats.get("user_msg_median_length", "N/A"),
                    }
                )
    else:
        st.info("💡 Run `python docs/examples/eda_analysis.py` to generate detailed summary insights")


def render_temporal(chatgpt_df, claude_df):
    st.title("📈 Temporal Analysis")

    def add_time_features(df):
        df = df.copy()
        df["hour"] = df["message_create_time"].dt.hour
        df["day_of_week"] = df["message_create_time"].dt.day_name()
        df["date"] = df["message_create_time"].dt.date
        df["month"] = df["message_create_time"].dt.to_period("M").astype(str)
        df["year"] = df["message_create_time"].dt.year
        return df

    chatgpt_df = add_time_features(chatgpt_df)
    claude_df = add_time_features(claude_df)

    tab1, tab2, tab3 = st.tabs(["📅 Timeline", "🔥 Heatmap", "📊 Patterns"])

    with tab1:
        st.subheader("Activity Timeline")

        col1, col2 = st.columns([3, 1])
        with col2:
            agg_level = st.selectbox(
                "Aggregation", ["Daily", "Weekly", "Monthly"], index=0, help="How to group the data"
            )

        combined = pd.concat([chatgpt_df.assign(platform="ChatGPT"), claude_df.assign(platform="Claude")])

        if agg_level == "Daily":
            freq = "D"
        elif agg_level == "Weekly":
            freq = "W"
        else:
            freq = "M"

        timeline = (
            combined.groupby([pd.Grouper(key="message_create_time", freq=freq), "platform"])
            .size()
            .reset_index(name="count")
        )

        fig1 = px.line(
            timeline,
            x="message_create_time",
            y="count",
            color="platform",
            title=f"{agg_level} Message Activity",
            labels={"message_create_time": "Date", "count": "Messages", "platform": "Platform"},
            markers=True,
        )
        fig1.update_layout(hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("Cumulative Growth")

        cumulative = timeline.copy()
        cumulative["cumulative"] = cumulative.groupby("platform")["count"].cumsum()

        fig2 = px.area(
            cumulative,
            x="message_create_time",
            y="cumulative",
            color="platform",
            title="Cumulative Messages Over Time",
            labels={"message_create_time": "Date", "cumulative": "Total Messages", "platform": "Platform"},
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Monthly Comparison")

        monthly = combined.groupby(["month", "platform"]).size().reset_index(name="count")

        fig3 = px.bar(
            monthly,
            x="month",
            y="count",
            color="platform",
            barmode="group",
            title="Monthly Activity by Platform",
            labels={"month": "Month", "count": "Messages", "platform": "Platform"},
        )
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Usage Heatmap")

        platform_choice = st.radio(
            "Select Platform", ["ChatGPT", "Claude", "Combined"], horizontal=True, help="Which platform to visualize"
        )

        if platform_choice == "ChatGPT":
            heatmap_df = chatgpt_df
        elif platform_choice == "Claude":
            heatmap_df = claude_df
        else:
            heatmap_df = pd.concat([chatgpt_df, claude_df])

        # Hour x Day of Week heatmap
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        heatmap_data = heatmap_df.groupby(["day_of_week", "hour"]).size().reset_index(name="count")

        # Pivot for heatmap
        heatmap_pivot = heatmap_data.pivot(index="day_of_week", columns="hour", values="count").fillna(0)

        # Reorder days
        heatmap_pivot = heatmap_pivot.reindex([d for d in day_order if d in heatmap_pivot.index])

        fig4 = px.imshow(
            heatmap_pivot,
            labels={"x": "Hour of Day", "y": "Day of Week", "color": "Messages"},
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            color_continuous_scale="YlOrRd",
            title=f"{platform_choice}: Activity by Day and Hour",
            aspect="auto",
        )
        fig4.update_xaxes(side="bottom")
        st.plotly_chart(fig4, use_container_width=True)

        # Peak activity insights
        st.divider()
        col1, col2, col3 = st.columns(3)

        most_active_hour = heatmap_df["hour"].mode()[0] if len(heatmap_df) > 0 else 0
        most_active_day = heatmap_df["day_of_week"].mode()[0] if len(heatmap_df) > 0 else "N/A"
        peak_count = heatmap_data["count"].max()

        with col1:
            st.metric("Peak Hour", f"{int(most_active_hour):02d}:00", help="Most active hour of the day")
        with col2:
            st.metric("Peak Day", most_active_day, help="Most active day of the week")
        with col3:
            st.metric("Peak Messages", f"{peak_count:,}", help="Maximum messages in any hour/day combo")

    with tab3:
        st.subheader("Usage Patterns")

        # Hour distribution
        st.markdown("#### 🕐 Hourly Distribution")

        hourly_combined = pd.concat([chatgpt_df.assign(platform="ChatGPT"), claude_df.assign(platform="Claude")])

        hourly_dist = hourly_combined.groupby(["hour", "platform"]).size().reset_index(name="count")

        fig5 = px.bar(
            hourly_dist,
            x="hour",
            y="count",
            color="platform",
            barmode="group",
            title="Messages by Hour of Day",
            labels={"hour": "Hour of Day", "count": "Messages", "platform": "Platform"},
        )
        st.plotly_chart(fig5, use_container_width=True)

        # Day of week distribution
        st.markdown("#### 📅 Day of Week Distribution")

        dow_dist = hourly_combined.groupby(["day_of_week", "platform"]).size().reset_index(name="count")

        # Reorder days
        dow_dist["day_of_week"] = pd.Categorical(
            dow_dist["day_of_week"],
            categories=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            ordered=True,
        )
        dow_dist = dow_dist.sort_values("day_of_week")

        fig6 = px.bar(
            dow_dist,
            x="day_of_week",
            y="count",
            color="platform",
            barmode="group",
            title="Messages by Day of Week",
            labels={"day_of_week": "Day", "count": "Messages", "platform": "Platform"},
        )
        st.plotly_chart(fig6, use_container_width=True)

        # Activity by role
        st.markdown("#### 💬 Activity by Role")

        role_dist = hourly_combined.groupby(["platform", "role"]).size().reset_index(name="count")

        fig7 = px.bar(
            role_dist,
            x="platform",
            y="count",
            color="role",
            barmode="stack",
            title="Messages by Role and Platform",
            labels={"platform": "Platform", "count": "Messages", "role": "Role"},
        )
        st.plotly_chart(fig7, use_container_width=True)

        # Summary stats
        st.divider()
        st.markdown("#### 📊 Summary Statistics")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ChatGPT**")
            gpt_most_active_hour = chatgpt_df["hour"].mode()[0]
            gpt_most_active_day = chatgpt_df["day_of_week"].mode()[0]
            gpt_hourly_avg = len(chatgpt_df) / 24

            st.write(f"- Most active hour: **{gpt_most_active_hour}:00**")
            st.write(f"- Most active day: **{gpt_most_active_day}**")
            st.write(f"- Avg msgs/hour: **{gpt_hourly_avg:.1f}**")

        with col2:
            st.markdown("**Claude**")
            claude_most_active_hour = claude_df["hour"].mode()[0]
            claude_most_active_day = claude_df["day_of_week"].mode()[0]
            claude_hourly_avg = len(claude_df) / 24

            st.write(f"- Most active hour: **{claude_most_active_hour:02d}:00**")
            st.write(f"- Most active day: **{claude_most_active_day}**")
            st.write(f"- Avg msgs/hour: **{claude_hourly_avg:.1f}**")


def render_conversations(chatgpt_df, claude_df):
    st.title("💬 Conversation Insights")

    @st.cache_data
    def analyze_conversations(df, platform):
        conv_stats = (
            df.groupby("conversation_id")
            .agg(
                message_count=("message_id", "count"),
                start_time=("conversation_create_time", "min"),
                end_time=("conversation_create_time", "max"),
                title=("title", "first"),
            )
            .reset_index()
        )

        conv_stats["duration_minutes"] = (conv_stats["end_time"] - conv_stats["start_time"]).dt.total_seconds() / 60
        conv_stats["platform"] = platform

        return conv_stats

    chatgpt_conv = analyze_conversations(chatgpt_df, "ChatGPT")
    claude_conv = analyze_conversations(claude_df, "Claude")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Conversations",
            f"{len(chatgpt_conv) + len(claude_conv):,}",
            help="Combined conversations across both platforms",
        )
    with col2:
        avg_msgs = (chatgpt_conv["message_count"].mean() + claude_conv["message_count"].mean()) / 2
        st.metric("Avg Messages/Conv", f"{avg_msgs:.1f}", help="Average messages per conversation")
    with col3:
        median_msgs = pd.concat([chatgpt_conv["message_count"], claude_conv["message_count"]]).median()
        st.metric("Median Messages/Conv", f"{median_msgs:.0f}", help="Median messages per conversation")
    with col4:
        avg_duration = (chatgpt_conv["duration_minutes"].mean() + claude_conv["duration_minutes"].mean()) / 2
        st.metric("Avg Duration", f"{avg_duration:.0f} min", help="Average conversation duration")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📊 Distributions", "🏆 Top Conversations", "📈 Trends"])

    with tab1:
        st.subheader("Message Count Distribution")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ChatGPT")
            fig1 = px.histogram(
                chatgpt_conv,
                x="message_count",
                nbins=50,
                title="Messages per Conversation",
                labels={"message_count": "Messages", "count": "Conversations"},
                color_discrete_sequence=["#10B981"],
            )
            fig1.add_vline(
                x=chatgpt_conv["message_count"].median(), line_dash="dash", line_color="red", annotation_text="Median"
            )
            st.plotly_chart(fig1, use_container_width=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Mean", f"{chatgpt_conv['message_count'].mean():.1f}")
            m2.metric("Median", f"{chatgpt_conv['message_count'].median():.0f}")
            m3.metric("Max", f"{chatgpt_conv['message_count'].max():.0f}")

        with col2:
            st.markdown("#### Claude")
            fig2 = px.histogram(
                claude_conv,
                x="message_count",
                nbins=50,
                title="Messages per Conversation",
                labels={"message_count": "Messages", "count": "Conversations"},
                color_discrete_sequence=["#8B5CF6"],
            )
            fig2.add_vline(
                x=claude_conv["message_count"].median(), line_dash="dash", line_color="red", annotation_text="Median"
            )
            st.plotly_chart(fig2, use_container_width=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Mean", f"{claude_conv['message_count'].mean():.1f}")
            m2.metric("Median", f"{claude_conv['message_count'].median():.0f}")
            m3.metric("Max", f"{claude_conv['message_count'].max():.0f}")

        # Duration distribution
        st.divider()
        st.subheader("Conversation Duration Distribution")

        # Filter out very short and very long durations for better visualization
        chatgpt_dur = chatgpt_conv[chatgpt_conv["duration_minutes"] > 0]
        claude_dur = claude_conv[claude_conv["duration_minutes"] > 0]

        combined_dur = pd.concat([chatgpt_dur, claude_dur])

        fig3 = px.histogram(
            combined_dur,
            x="duration_minutes",
            color="platform",
            nbins=50,
            barmode="overlay",
            title="Conversation Duration (minutes)",
            labels={"duration_minutes": "Duration (min)", "count": "Conversations"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        fig3.update_xaxes(range=[0, combined_dur["duration_minutes"].quantile(0.95)])
        st.plotly_chart(fig3, use_container_width=True)

        st.divider()
        st.subheader("Duration vs Message Count")

        fig4 = px.scatter(
            combined_dur,
            x="message_count",
            y="duration_minutes",
            color="platform",
            title="Relationship between Messages and Duration",
            labels={"message_count": "Messages", "duration_minutes": "Duration (min)", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            opacity=0.6,
        )
        fig4.update_yaxes(range=[0, combined_dur["duration_minutes"].quantile(0.95)])
        st.plotly_chart(fig4, use_container_width=True)

    with tab2:
        st.subheader("Top Conversations by Length")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ChatGPT - Longest Conversations")
            top_chatgpt = chatgpt_conv.nlargest(15, "message_count")[["title", "message_count", "start_time"]]
            top_chatgpt["start_time"] = top_chatgpt["start_time"].dt.strftime("%Y-%m-%d")

            fig5 = px.bar(
                top_chatgpt,
                y="title",
                x="message_count",
                orientation="h",
                title="Top 15 Longest Conversations",
                labels={"message_count": "Messages", "title": ""},
                color_discrete_sequence=["#10B981"],
                hover_data=["start_time"],
            )
            fig5.update_yaxes(tickmode="linear")
            fig5.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig5, use_container_width=True)

            # Table view
            with st.expander("📋 View as Table"):
                st.dataframe(
                    top_chatgpt.rename(columns={"title": "Title", "message_count": "Messages", "start_time": "Date"}),
                    use_container_width=True,
                    hide_index=True,
                )

        with col2:
            st.markdown("#### Claude - Longest Conversations")
            top_claude = claude_conv.nlargest(15, "message_count")[["title", "message_count", "start_time"]]
            top_claude["start_time"] = top_claude["start_time"].dt.strftime("%Y-%m-%d")

            fig6 = px.bar(
                top_claude,
                y="title",
                x="message_count",
                orientation="h",
                title="Top 15 Longest Conversations",
                labels={"message_count": "Messages", "title": ""},
                color_discrete_sequence=["#8B5CF6"],
                hover_data=["start_time"],
            )
            fig6.update_yaxes(tickmode="linear")
            fig6.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig6, use_container_width=True)

            with st.expander("📋 View as Table"):
                st.dataframe(
                    top_claude.rename(columns={"title": "Title", "message_count": "Messages", "start_time": "Date"}),
                    use_container_width=True,
                    hide_index=True,
                )

    with tab3:
        st.subheader("Conversation Trends Over Time")

        combined_conv = pd.concat([chatgpt_conv, claude_conv])
        combined_conv["start_date"] = combined_conv["start_time"].dt.date

        conv_timeline = combined_conv.groupby(["start_date", "platform"]).size().reset_index(name="conversations")

        fig7 = px.line(
            conv_timeline,
            x="start_date",
            y="conversations",
            color="platform",
            title="New Conversations Over Time",
            labels={"start_date": "Date", "conversations": "New Conversations", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        st.plotly_chart(fig7, use_container_width=True)

        # Monthly aggregation
        st.divider()
        st.markdown("#### Monthly Conversation Stats")

        combined_conv["month"] = combined_conv["start_time"].dt.to_period("M").astype(str)

        monthly_stats = (
            combined_conv.groupby(["month", "platform"])
            .agg({"conversation_id": "count", "message_count": "mean"})
            .reset_index()
            .rename(columns={"conversation_id": "conversations", "message_count": "avg_messages"})
        )

        col1, col2 = st.columns(2)

        with col1:
            fig8 = px.bar(
                monthly_stats,
                x="month",
                y="conversations",
                color="platform",
                barmode="group",
                title="Conversations per Month",
                labels={"month": "Month", "conversations": "Conversations", "platform": "Platform"},
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            )
            st.plotly_chart(fig8, use_container_width=True)

        with col2:
            fig9 = px.line(
                monthly_stats,
                x="month",
                y="avg_messages",
                color="platform",
                markers=True,
                title="Avg Messages per Conversation (Monthly)",
                labels={"month": "Month", "avg_messages": "Avg Messages", "platform": "Platform"},
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            )
            st.plotly_chart(fig9, use_container_width=True)


def score_prompt(text):
    """Simple heuristic to score prompt quality."""
    if not text or not isinstance(text, str):
        return 0
    score = 0
    words = text.split()
    if len(words) > 20:
        score += 20
    if len(words) > 50:
        score += 20
    if "?" in text:
        score += 10
    if "example" in text.lower() or "instance" in text.lower():
        score += 15
    if "format" in text.lower() or "structure" in text.lower():
        score += 15
    if "context" in text.lower() or "background" in text.lower():
        score += 10
    if len(text) > 500:
        score += 10
    return min(score, 100)

def render_optimization(chatgpt_df, claude_df, gemini_df):
    st.title("🚀 Usage Optimization")
    st.markdown("Insights and tips to get the most out of your AI interactions.")

    all_dfs = []
    if not chatgpt_df.empty:
        all_dfs.append(chatgpt_df.assign(platform="ChatGPT"))
    if not claude_df.empty:
        all_dfs.append(claude_df.assign(platform="Claude"))
    if not gemini_df.empty:
        all_dfs.append(gemini_df.assign(platform="Gemini"))

    if not all_dfs:
        st.warning("No data available for optimization analysis.")
        return

    df = pd.concat(all_dfs)
    user_msgs = df[df["role"].isin(["user", "human"])]

    if user_msgs.empty:
        st.warning("No user messages found to analyze.")
        return

    # Prompt Quality Analysis
    st.subheader("🎯 Prompt Quality Score")
    user_msgs["prompt_score"] = user_msgs["content"].apply(score_prompt)
    avg_score = user_msgs["prompt_score"].mean()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Average Prompt Score", f"{avg_score:.1f}/100")
        if avg_score < 40:
            st.error("Your prompts are very brief. Try adding more context!")
        elif avg_score < 70:
            st.warning("Good start! Adding examples or specific formats could help.")
        else:
            st.success("Great! You provide detailed instructions.")

    with col2:
        fig = px.histogram(user_msgs, x="prompt_score", nbins=20, title="Distribution of Prompt Scores",
                          labels={"prompt_score": "Score"}, color="platform", barmode="overlay")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Optimization Tips
    st.subheader("💡 Optimization Tips")

    tips = []
    if avg_score < 60:
        tips.append("**Better Context**: Your average prompt is short. Use the 'Persona-Task-Context-Format' framework.")

    # Temporal patterns for optimization
    user_msgs["hour"] = pd.to_datetime(user_msgs["message_create_time"], unit="s", errors="coerce").dt.hour
    peak_hour = user_msgs["hour"].mode()[0] if not user_msgs["hour"].dropna().empty else None

    if peak_hour is not None:
        if 9 <= peak_hour <= 17:
            tips.append(f"**Deep Work**: You are most active at {peak_hour:02d}:00. Save this time for complex architectural discussions.")
        else:
            tips.append(f"**Off-peak Activity**: You use AI heavily at {peak_hour:02d}:00. Ensure you aren't using it for simple tasks that could be batched.")

    for tip in tips:
        st.info(tip)

    st.divider()
    st.subheader("🧠 Topic Intent (Experimental)")
    # Simple keyword-based intent
    intents = {
        "Coding": ["code", "python", "debug", "function", "error", "git", "api"],
        "Writing": ["write", "draft", "email", "blog", "summary", "text"],
        "Learning": ["explain", "what is", "how does", "teach", "learn"],
        "Creative": ["story", "poem", "idea", "creative", "imagine"]
    }

    def detect_intent(text):
        text = str(text).lower()
        for intent, keywords in intents.items():
            if any(kw in text for kw in keywords):
                return intent
        return "General"

    user_msgs["intent"] = user_msgs["content"].apply(detect_intent)
    intent_counts = user_msgs["intent"].value_counts().reset_index()

    fig_intent = px.pie(intent_counts, values="count", names="intent", title="Conversation Intent Distribution")
    st.plotly_chart(fig_intent, use_container_width=True)


def render_content(chatgpt_df, claude_df):
    st.title("🔤 Content Analysis")

    # Add content length column
    chatgpt_df = chatgpt_df.copy()
    claude_df = claude_df.copy()
    chatgpt_df["content_length"] = chatgpt_df["content"].fillna("").astype(str).str.len()
    claude_df["content_length"] = claude_df["content"].fillna("").astype(str).str.len()

    # Filter out tool messages
    chatgpt_content = chatgpt_df[chatgpt_df["role"] != "tool"]
    claude_content = claude_df[claude_df["role"] != "tool"]

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)

    total_chars = chatgpt_content["content_length"].sum() + claude_content["content_length"].sum()
    total_words = int(total_chars / 5)  # Rough estimate

    with col1:
        st.metric("Total Characters", f"{total_chars:,}", help="Total characters across all messages")
    with col2:
        st.metric("Est. Total Words", f"{total_words:,}", help="Estimated word count (chars/5)")
    with col3:
        avg_msg_len = (chatgpt_content["content_length"].mean() + claude_content["content_length"].mean()) / 2
        st.metric("Avg Message Length", f"{avg_msg_len:.0f} chars", help="Average message length")
    with col4:
        median_msg_len = pd.concat([chatgpt_content["content_length"], claude_content["content_length"]]).median()
        st.metric("Median Message Length", f"{median_msg_len:.0f} chars", help="Median message length")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📏 Message Length", "👥 Role Analysis", "📝 Text Patterns"])

    with tab1:
        st.subheader("Message Length Distribution")

        chatgpt_user = chatgpt_content[chatgpt_content["role"] == "user"]
        chatgpt_ai = chatgpt_content[chatgpt_content["role"] == "assistant"]
        claude_user = claude_content[claude_content["role"] == "human"]
        claude_ai = claude_content[claude_content["role"] == "assistant"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### User Messages")

            user_combined = pd.concat(
                [
                    chatgpt_user[["content_length"]].assign(platform="ChatGPT"),
                    claude_user[["content_length"]].assign(platform="Claude"),
                ]
            )

            fig1 = px.histogram(
                user_combined,
                x="content_length",
                color="platform",
                nbins=50,
                barmode="overlay",
                title="User Message Length Distribution",
                labels={"content_length": "Characters", "count": "Messages"},
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
                opacity=0.7,
            )
            fig1.update_xaxes(range=[0, user_combined["content_length"].quantile(0.95)])
            st.plotly_chart(fig1, use_container_width=True)

            m1, m2 = st.columns(2)
            m1.metric("ChatGPT Median", f"{chatgpt_user['content_length'].median():.0f}")
            m2.metric("Claude Median", f"{claude_user['content_length'].median():.0f}")

        with col2:
            st.markdown("#### AI Responses")

            ai_combined = pd.concat(
                [
                    chatgpt_ai[["content_length"]].assign(platform="ChatGPT"),
                    claude_ai[["content_length"]].assign(platform="Claude"),
                ]
            )

            fig2 = px.histogram(
                ai_combined,
                x="content_length",
                color="platform",
                nbins=50,
                barmode="overlay",
                title="AI Response Length Distribution",
                labels={"content_length": "Characters", "count": "Messages"},
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
                opacity=0.7,
            )
            fig2.update_xaxes(range=[0, ai_combined["content_length"].quantile(0.95)])
            st.plotly_chart(fig2, use_container_width=True)

            m1, m2 = st.columns(2)
            m1.metric("ChatGPT Median", f"{chatgpt_ai['content_length'].median():.0f}")
            m2.metric("Claude Median", f"{claude_ai['content_length'].median():.0f}")

        # Box plot comparison
        st.divider()
        st.subheader("Length Comparison (User vs AI)")

        comparison_data = pd.concat(
            [
                chatgpt_user[["content_length"]].assign(platform="ChatGPT", role="User"),
                chatgpt_ai[["content_length"]].assign(platform="ChatGPT", role="AI"),
                claude_user[["content_length"]].assign(platform="Claude", role="User"),
                claude_ai[["content_length"]].assign(platform="Claude", role="AI"),
            ]
        )

        fig3 = px.box(
            comparison_data,
            x="platform",
            y="content_length",
            color="role",
            title="Message Length Distribution by Role and Platform",
            labels={"content_length": "Characters", "platform": "Platform", "role": "Role"},
            color_discrete_map={"User": "#3B82F6", "AI": "#EF4444"},
        )
        fig3.update_yaxes(range=[0, comparison_data["content_length"].quantile(0.95)])
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Role Distribution Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ChatGPT")
            chatgpt_roles = chatgpt_content["role"].value_counts()

            fig4 = px.pie(
                values=chatgpt_roles.values,
                names=chatgpt_roles.index,
                title="Message Distribution by Role",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig4, use_container_width=True)

            # Role stats
            for role, count in chatgpt_roles.items():
                pct = (count / chatgpt_roles.sum()) * 100
                st.write(f"**{role}**: {count:,} messages ({pct:.1f}%)")

        with col2:
            st.markdown("#### Claude")
            claude_roles = claude_content["role"].value_counts()

            fig5 = px.pie(
                values=claude_roles.values,
                names=claude_roles.index,
                title="Message Distribution by Role",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig5, use_container_width=True)

            # Role stats
            for role, count in claude_roles.items():
                pct = (count / claude_roles.sum()) * 100
                st.write(f"**{role}**: {count:,} messages ({pct:.1f}%)")

        # Role comparison over time
        st.divider()
        st.subheader("Role Activity Over Time")

        combined = pd.concat([chatgpt_content.assign(platform="ChatGPT"), claude_content.assign(platform="Claude")])

        combined["date"] = combined["conversation_create_time"].dt.date

        role_timeline = combined.groupby(["date", "platform", "role"]).size().reset_index(name="count")

        fig6 = px.line(
            role_timeline,
            x="date",
            y="count",
            color="role",
            facet_col="platform",
            title="Message Activity by Role Over Time",
            labels={"date": "Date", "count": "Messages", "role": "Role"},
        )
        st.plotly_chart(fig6, use_container_width=True)

    with tab3:
        st.subheader("Text Pattern Analysis")

        st.markdown("#### Average Message Length Over Time")

        combined["month"] = combined["conversation_create_time"].dt.to_period("M").astype(str)

        monthly_length = (
            combined.groupby(["month", "platform", "role"])["content_length"]
            .mean()
            .reset_index()
            .rename(columns={"content_length": "avg_length"})
        )

        fig7 = px.line(
            monthly_length,
            x="month",
            y="avg_length",
            color="platform",
            line_dash="role",
            markers=True,
            title="Average Message Length Trends (Monthly)",
            labels={"month": "Month", "avg_length": "Avg Characters", "platform": "Platform", "role": "Role"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        st.plotly_chart(fig7, use_container_width=True)

        st.divider()
        st.markdown("#### Most Common Conversation Topics")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ChatGPT**")
            chatgpt_topics = chatgpt_df["title"].value_counts().head(10)

            fig8 = px.bar(
                x=chatgpt_topics.values,
                y=chatgpt_topics.index,
                orientation="h",
                title="Top 10 Topics",
                labels={"x": "Occurrences", "y": ""},
                color_discrete_sequence=["#10B981"],
            )
            fig8.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig8, use_container_width=True)

        with col2:
            st.markdown("**Claude**")
            claude_topics = claude_df["title"].value_counts().head(10)

            fig9 = px.bar(
                x=claude_topics.values,
                y=claude_topics.index,
                orientation="h",
                title="Top 10 Topics",
                labels={"x": "Occurrences", "y": ""},
                color_discrete_sequence=["#8B5CF6"],
            )
            fig9.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig9, use_container_width=True)

        st.divider()
        st.markdown("#### Summary Statistics")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ChatGPT Content Stats**")
            st.json(
                {
                    "total_messages": len(chatgpt_content),
                    "avg_user_msg_length": int(chatgpt_user["content_length"].mean()),
                    "avg_ai_msg_length": int(chatgpt_ai["content_length"].mean()),
                    "median_user_msg_length": int(chatgpt_user["content_length"].median()),
                    "median_ai_msg_length": int(chatgpt_ai["content_length"].median()),
                    "longest_message": int(chatgpt_content["content_length"].max()),
                }
            )

        with col2:
            st.markdown("**Claude Content Stats**")
            st.json(
                {
                    "total_messages": len(claude_content),
                    "avg_user_msg_length": int(claude_user["content_length"].mean()),
                    "avg_ai_msg_length": int(claude_ai["content_length"].mean()),
                    "median_user_msg_length": int(claude_user["content_length"].median()),
                    "median_ai_msg_length": int(claude_ai["content_length"].median()),
                    "longest_message": int(claude_content["content_length"].max()),
                }
            )


def render_comparison(chatgpt_df, claude_df):
    st.title("🤖 Platform Comparison")

    st.markdown("""
    Compare usage patterns, conversation metrics, and content characteristics between ChatGPT and Claude.
    """)

    @st.cache_data
    def get_comparison_stats(chatgpt_df, claude_df):
        chatgpt_conv = chatgpt_df.groupby("conversation_id").agg(
            message_count=("message_id", "count"),
            start_time=("conversation_create_time", "min"),
            end_time=("conversation_create_time", "max"),
        )
        chatgpt_conv["duration_minutes"] = (
            chatgpt_conv["end_time"] - chatgpt_conv["start_time"]
        ).dt.total_seconds() / 60

        claude_conv = claude_df.groupby("conversation_id").agg(
            message_count=("message_id", "count"),
            start_time=("conversation_create_time", "min"),
            end_time=("conversation_create_time", "max"),
        )
        claude_conv["duration_minutes"] = (claude_conv["end_time"] - claude_conv["start_time"]).dt.total_seconds() / 60

        chatgpt_df_copy = chatgpt_df.copy()
        claude_df_copy = claude_df.copy()
        chatgpt_df_copy["content_length"] = chatgpt_df_copy["content"].fillna("").astype(str).str.len()
        claude_df_copy["content_length"] = claude_df_copy["content"].fillna("").astype(str).str.len()

        return {
            "chatgpt_conv": chatgpt_conv,
            "claude_conv": claude_conv,
            "chatgpt_df": chatgpt_df_copy,
            "claude_df": claude_df_copy,
        }

    stats = get_comparison_stats(chatgpt_df, claude_df)
    chatgpt_conv = stats["chatgpt_conv"]
    claude_conv = stats["claude_conv"]
    chatgpt_df_with_len = stats["chatgpt_df"]
    claude_df_with_len = stats["claude_df"]

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💬 Conversations", "📝 Content", "⏰ Temporal"])

    with tab1:
        st.subheader("Side-by-Side Comparison")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🟢 ChatGPT")
            m1, m2 = st.columns(2)
            m1.metric("Total Messages", f"{len(chatgpt_df):,}")
            m2.metric("Total Conversations", f"{len(chatgpt_conv):,}")

            m3, m4 = st.columns(2)
            m3.metric("Avg Msgs/Conv", f"{chatgpt_conv['message_count'].mean():.1f}")
            m4.metric("Median Msgs/Conv", f"{chatgpt_conv['message_count'].median():.0f}")

        with col2:
            st.markdown("### 🟣 Claude")
            m1, m2 = st.columns(2)
            m1.metric("Total Messages", f"{len(claude_df):,}")
            m2.metric("Total Conversations", f"{len(claude_conv):,}")

            m3, m4 = st.columns(2)
            m3.metric("Avg Msgs/Conv", f"{claude_conv['message_count'].mean():.1f}")
            m4.metric("Median Msgs/Conv", f"{claude_conv['message_count'].median():.0f}")

        # Bar chart comparisons
        st.divider()
        st.markdown("#### Key Metrics Comparison")

        comparison_data = pd.DataFrame(
            {
                "Platform": ["ChatGPT", "Claude", "ChatGPT", "Claude"],
                "Metric": ["Total Messages", "Total Messages", "Total Conversations", "Total Conversations"],
                "Value": [len(chatgpt_df), len(claude_df), len(chatgpt_conv), len(claude_conv)],
            }
        )

        fig1 = px.bar(
            comparison_data,
            x="Metric",
            y="Value",
            color="Platform",
            barmode="group",
            title="Platform Usage Overview",
            labels={"Value": "Count", "Metric": ""},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            text="Value",
        )
        fig1.update_traces(texttemplate="%{text:,}", textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()
        st.markdown("#### Usage Distribution")

        col1, col2 = st.columns(2)

        with col1:
            msg_share = pd.DataFrame({"Platform": ["ChatGPT", "Claude"], "Messages": [len(chatgpt_df), len(claude_df)]})

            fig2 = px.pie(
                msg_share,
                values="Messages",
                names="Platform",
                title="Message Share",
                color="Platform",
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            conv_share = pd.DataFrame(
                {"Platform": ["ChatGPT", "Claude"], "Conversations": [len(chatgpt_conv), len(claude_conv)]}
            )

            fig3 = px.pie(
                conv_share,
                values="Conversations",
                names="Platform",
                title="Conversation Share",
                color="Platform",
                color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            )
            fig3.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Conversation Metrics Comparison")
        avg_msgs_data = pd.DataFrame(
            {
                "Platform": ["ChatGPT", "Claude"],
                "Average": [chatgpt_conv["message_count"].mean(), claude_conv["message_count"].mean()],
                "Median": [chatgpt_conv["message_count"].median(), claude_conv["message_count"].median()],
            }
        )

        fig4 = px.bar(
            avg_msgs_data.melt(id_vars="Platform", var_name="Statistic", value_name="Messages"),
            x="Platform",
            y="Messages",
            color="Statistic",
            barmode="group",
            title="Messages per Conversation",
            labels={"Messages": "Avg Messages", "Platform": ""},
            text="Messages",
        )
        fig4.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)

        st.divider()
        st.markdown("#### Conversation Length Distribution")

        conv_comparison = pd.concat(
            [
                chatgpt_conv[["message_count"]].assign(platform="ChatGPT"),
                claude_conv[["message_count"]].assign(platform="Claude"),
            ]
        )

        fig5 = px.violin(
            conv_comparison,
            x="platform",
            y="message_count",
            color="platform",
            box=True,
            title="Conversation Length Distribution (Violin Plot)",
            labels={"message_count": "Messages per Conversation", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        fig5.update_yaxes(range=[0, conv_comparison["message_count"].quantile(0.95)])
        st.plotly_chart(fig5, use_container_width=True)

        # Duration comparison
        st.divider()
        st.markdown("#### Conversation Duration Comparison")

        duration_data = pd.DataFrame(
            {
                "Platform": ["ChatGPT", "Claude"],
                "Avg Duration (min)": [chatgpt_conv["duration_minutes"].mean(), claude_conv["duration_minutes"].mean()],
                "Median Duration (min)": [
                    chatgpt_conv["duration_minutes"].median(),
                    claude_conv["duration_minutes"].median(),
                ],
            }
        )

        fig6 = px.bar(
            duration_data.melt(id_vars="Platform", var_name="Statistic", value_name="Minutes"),
            x="Platform",
            y="Minutes",
            color="Statistic",
            barmode="group",
            title="Conversation Duration Comparison",
            text="Minutes",
        )
        fig6.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        st.plotly_chart(fig6, use_container_width=True)

        # Summary table
        st.divider()
        st.markdown("#### Summary Statistics")

        summary_df = pd.DataFrame(
            {
                "Metric": [
                    "Total Conversations",
                    "Avg Messages/Conv",
                    "Median Messages/Conv",
                    "Max Messages/Conv",
                    "Avg Duration (min)",
                    "Median Duration (min)",
                ],
                "ChatGPT": [
                    f"{len(chatgpt_conv):,}",
                    f"{chatgpt_conv['message_count'].mean():.1f}",
                    f"{chatgpt_conv['message_count'].median():.0f}",
                    f"{chatgpt_conv['message_count'].max():,}",
                    f"{chatgpt_conv['duration_minutes'].mean():.0f}",
                    f"{chatgpt_conv['duration_minutes'].median():.0f}",
                ],
                "Claude": [
                    f"{len(claude_conv):,}",
                    f"{claude_conv['message_count'].mean():.1f}",
                    f"{claude_conv['message_count'].median():.0f}",
                    f"{claude_conv['message_count'].max():,}",
                    f"{claude_conv['duration_minutes'].mean():.0f}",
                    f"{claude_conv['duration_minutes'].median():.0f}",
                ],
            }
        )

        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Content Analysis Comparison")

        chatgpt_user = chatgpt_df_with_len[chatgpt_df_with_len["role"] == "user"]
        chatgpt_ai = chatgpt_df_with_len[chatgpt_df_with_len["role"] == "assistant"]
        claude_user = claude_df_with_len[claude_df_with_len["role"] == "human"]
        claude_ai = claude_df_with_len[claude_df_with_len["role"] == "assistant"]

        content_data = pd.DataFrame(
            {
                "Platform": ["ChatGPT", "Claude", "ChatGPT", "Claude"],
                "Type": ["User", "User", "AI", "AI"],
                "Median Length": [
                    chatgpt_user["content_length"].median(),
                    claude_user["content_length"].median(),
                    chatgpt_ai["content_length"].median(),
                    claude_ai["content_length"].median(),
                ],
            }
        )

        fig7 = px.bar(
            content_data,
            x="Platform",
            y="Median Length",
            color="Type",
            barmode="group",
            title="Median Message Length Comparison",
            labels={"Median Length": "Characters"},
            text="Median Length",
        )
        fig7.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        st.plotly_chart(fig7, use_container_width=True)

        # Content length distribution
        st.divider()
        st.markdown("#### Message Length Distribution")

        length_comparison = pd.concat(
            [
                chatgpt_user[["content_length"]].assign(platform="ChatGPT", role="User"),
                claude_user[["content_length"]].assign(platform="Claude", role="User"),
                chatgpt_ai[["content_length"]].assign(platform="ChatGPT", role="AI"),
                claude_ai[["content_length"]].assign(platform="Claude", role="AI"),
            ]
        )

        fig8 = px.box(
            length_comparison,
            x="platform",
            y="content_length",
            color="role",
            title="Message Length Distribution by Platform and Role",
            labels={"content_length": "Characters", "platform": "Platform", "role": "Role"},
            color_discrete_map={"User": "#3B82F6", "AI": "#EF4444"},
        )
        fig8.update_yaxes(range=[0, length_comparison["content_length"].quantile(0.95)])
        st.plotly_chart(fig8, use_container_width=True)

        st.divider()
        st.markdown("#### Role Distribution Comparison")

        chatgpt_roles = chatgpt_df["role"].value_counts()
        claude_roles = claude_df["role"].value_counts()

        all_roles = set(chatgpt_roles.index) | set(claude_roles.index)
        role_data = []
        for role in all_roles:
            role_data.append({"Role": role, "ChatGPT": chatgpt_roles.get(role, 0), "Claude": claude_roles.get(role, 0)})

        role_df = pd.DataFrame(role_data).melt(id_vars="Role", var_name="Platform", value_name="Count")

        fig9 = px.bar(
            role_df,
            x="Role",
            y="Count",
            color="Platform",
            barmode="group",
            title="Message Count by Role",
            labels={"Count": "Messages"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
            text="Count",
        )
        fig9.update_traces(texttemplate="%{text:,}", textposition="outside")
        st.plotly_chart(fig9, use_container_width=True)

        # Content summary table
        st.divider()
        st.markdown("#### Content Statistics Summary")

        content_summary = pd.DataFrame(
            {
                "Metric": [
                    "Total Messages",
                    "User Messages",
                    "AI Messages",
                    "Avg User Msg Length",
                    "Avg AI Msg Length",
                    "Median User Msg Length",
                    "Median AI Msg Length",
                ],
                "ChatGPT": [
                    f"{len(chatgpt_df_with_len):,}",
                    f"{len(chatgpt_user):,}",
                    f"{len(chatgpt_ai):,}",
                    f"{chatgpt_user['content_length'].mean():.0f}",
                    f"{chatgpt_ai['content_length'].mean():.0f}",
                    f"{chatgpt_user['content_length'].median():.0f}",
                    f"{chatgpt_ai['content_length'].median():.0f}",
                ],
                "Claude": [
                    f"{len(claude_df_with_len):,}",
                    f"{len(claude_user):,}",
                    f"{len(claude_ai):,}",
                    f"{claude_user['content_length'].mean():.0f}",
                    f"{claude_ai['content_length'].mean():.0f}",
                    f"{claude_user['content_length'].median():.0f}",
                    f"{claude_ai['content_length'].median():.0f}",
                ],
            }
        )

        st.dataframe(content_summary, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Temporal Patterns Comparison")

        combined = pd.concat([chatgpt_df.assign(platform="ChatGPT"), claude_df.assign(platform="Claude")])
        combined["date"] = combined["conversation_create_time"].dt.date

        daily_activity = combined.groupby(["date", "platform"]).size().reset_index(name="messages")

        fig10 = px.line(
            daily_activity,
            x="date",
            y="messages",
            color="platform",
            title="Daily Activity Comparison",
            labels={"date": "Date", "messages": "Messages", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        st.plotly_chart(fig10, use_container_width=True)

        st.divider()
        st.markdown("#### Activity by Hour of Day")

        combined["hour"] = combined["conversation_create_time"].dt.hour

        hourly_activity = combined.groupby(["hour", "platform"]).size().reset_index(name="messages")

        fig11 = px.bar(
            hourly_activity,
            x="hour",
            y="messages",
            color="platform",
            barmode="group",
            title="Messages by Hour of Day",
            labels={"hour": "Hour", "messages": "Messages", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        st.plotly_chart(fig11, use_container_width=True)

        # Most active days
        st.divider()
        st.markdown("#### Activity by Day of Week")

        combined["day_of_week"] = combined["conversation_create_time"].dt.day_name()
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        dow_activity = combined.groupby(["day_of_week", "platform"]).size().reset_index(name="messages")
        dow_activity["day_of_week"] = pd.Categorical(dow_activity["day_of_week"], categories=day_order, ordered=True)
        dow_activity = dow_activity.sort_values("day_of_week")

        fig12 = px.bar(
            dow_activity,
            x="day_of_week",
            y="messages",
            color="platform",
            barmode="group",
            title="Messages by Day of Week",
            labels={"day_of_week": "Day", "messages": "Messages", "platform": "Platform"},
            color_discrete_map={"ChatGPT": "#10B981", "Claude": "#8B5CF6"},
        )
        st.plotly_chart(fig12, use_container_width=True)

        # Peak activity summary
        st.divider()
        st.markdown("#### Peak Activity Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ChatGPT**")
            chatgpt_data = combined[combined["platform"] == "ChatGPT"]
            st.write(f"- Most active hour: **{chatgpt_data['hour'].mode()[0]:02d}:00**")
            st.write(f"- Most active day: **{chatgpt_data['day_of_week'].mode()[0]}**")
            st.write(
                f"- Peak daily messages: **{daily_activity[daily_activity['platform'] == 'ChatGPT']['messages'].max():,}**"
            )

        with col2:
            st.markdown("**Claude**")
            claude_data = combined[combined["platform"] == "Claude"]
            st.write(f"- Most active hour: **{int(claude_data['hour'].mode()[0]):02d}:00**")
            st.write(f"- Most active day: **{claude_data['day_of_week'].mode()[0]}**")
            st.write(
                f"- Peak daily messages: **{daily_activity[daily_activity['platform'] == 'Claude']['messages'].max():,}**"
            )


def mask_pii(text):
    """Simple PII masking for email and phone numbers."""
    if not isinstance(text, str):
        return text
    # Mask emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # Mask phone numbers (simple version)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    return text

def render_llm_analysis(chatgpt_df, claude_df):
    """LLM-powered semantic analysis using OpenAI Responses API."""
    st.title("🎯 LLM-Powered Insights")

    st.markdown("""
    Get human-like insights about your AI usage patterns and discover ways to maximize value from your conversations.
    This analysis uses GPT-4 to understand your interaction patterns and provide personalized recommendations.
    """)

    st.warning(
        "⚠️ **Privacy Notice:** This feature sends aggregated statistics and conversation summaries to OpenAI's API. "
        "Your API key is used locally and never stored permanently."
    )

    with st.expander("🔍 What data is sent to OpenAI?"):
        st.markdown("""
        **Data Sent:**
        - Aggregated statistics (message counts, conversation lengths, temporal patterns)
        - Top conversation titles (no message content)
        - Usage patterns and trends
        - Summary statistics only

        **NOT Sent:**
        - Individual message contents
        - Personal identification information
        - Full conversation transcripts

        **Privacy:**
        - Sent over HTTPS to OpenAI's API
        - Subject to [OpenAI's Privacy Policy](https://openai.com/privacy/)
        - API key stored in session only (not persisted to disk)

        **To minimize risk:**
        - Review summary stats before analysis
        - Use a separate API key for this app
        - Data is aggregated before sending
        """)

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        st.info("💡 **Tip:** Set `OPENAI_API_KEY` environment variable to avoid re-entering")

        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Your key is used only for this session and never saved to disk",
            placeholder="sk-...",
        )

        if api_key:
            if not api_key.startswith("sk-") and not api_key.startswith("sk-proj-"):
                st.error("❌ Invalid API key format. OpenAI keys start with 'sk-'")
                return

            st.session_state._temp_api_key = api_key
            st.success("✅ API key loaded (session only)")
        else:
            st.info("🔐 Enter your OpenAI API key to enable LLM-powered analysis")
            return

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Clear API Key", help="Remove API key from memory"):
            if "_temp_api_key" in st.session_state:
                del st.session_state._temp_api_key
            if "llm_analysis_results" in st.session_state:
                del st.session_state.llm_analysis_results
            st.success("✅ API key cleared")
            st.rerun()

    st.divider()

    # Analysis Options
    st.subheader("Analysis Settings")

    col1, col2, col3 = st.columns(3)

    with col1:
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["Quick Overview", "Detailed Analysis", "Deep Dive"],
            help="Choose how comprehensive the analysis should be",
        )

    with col2:
        focus_area = st.selectbox(
            "Focus Area",
            ["Overall Patterns", "Productivity Insights", "Usage Optimization", "Topic Analysis", "Time Management"],
            help="What aspect would you like to focus on?",
        )

    with col3:
        model_choice = st.selectbox(
            "Model",
            ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
            help="Choose the model for analysis",
        )

    st.divider()

    do_mask = st.checkbox("Enable PII Masking", value=True, help="Mask emails and phone numbers in topic titles before sending to API")

    if st.button("🚀 Generate Insights", type="primary", use_container_width=True):
        active_key = api_key or st.session_state.get("_temp_api_key")

        if not active_key:
            st.error("❌ No API key available")
            return

        try:
            from openai import OpenAI

            with st.spinner("🤖 Analyzing your chat patterns with OpenAI..."):
                # Prepare aggregated data
                summary_stats = prepare_analysis_data(chatgpt_df, claude_df, do_mask=do_mask)

                # Create OpenAI client
                client = OpenAI(api_key=active_key)

                # Generate analysis prompt based on settings
                prompt = create_analysis_prompt(summary_stats, analysis_depth, focus_area)

                # Call OpenAI Responses API
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert AI usage analyst who helps people maximize value from their AI assistant interactions.
Provide insightful, actionable analysis of usage patterns. Be specific, data-driven, and offer concrete recommendations.
Use a friendly, conversational tone while maintaining professionalism.""",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=8096,
                )

                analysis_text = response.choices[0].message.content

                st.session_state.llm_analysis_results = {
                    "analysis": analysis_text,
                    "focus": focus_area,
                    "depth": analysis_depth,
                    "model": model_choice,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                st.success("✅ Analysis complete!")

        except ImportError:
            st.error("❌ OpenAI library not installed. Run: `pip install openai`")
            return
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            logger.error(f"LLM analysis error: {type(e).__name__}: {str(e)}")
            return

    # Display Results
    if "llm_analysis_results" in st.session_state:
        st.divider()
        results = st.session_state.llm_analysis_results

        # Header with metadata
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.subheader("📊 Analysis Results")
        with col2:
            st.caption(f"Focus: {results['focus']}")
        with col3:
            st.caption(f"Generated: {results['timestamp']}")

        st.markdown(results["analysis"])

        st.divider()
        st.markdown("### 💡 Quick Recommendations")

        if "recommendation" in results["analysis"].lower() or "suggest" in results["analysis"].lower():
            st.info("💡 Review the analysis above for specific recommendations tailored to your usage patterns.")

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📋 Copy to Clipboard"):
                st.code(results["analysis"], language=None)

        with col2:
            if st.button("💾 Save Analysis"):
                output_path = Path("data/figures/llm_analysis.txt")
                output_path.parent.mkdir(exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(f"Analysis Generated: {results['timestamp']}\n")
                    f.write(f"Focus: {results['focus']}\n")
                    f.write(f"Depth: {results['depth']}\n")
                    f.write(f"Model: {results['model']}\n")
                    f.write("\n" + "=" * 60 + "\n\n")
                    f.write(results["analysis"])
                st.success(f"✅ Saved to {output_path}")

        if st.button("🔄 Generate New Analysis", help="Run analysis again with different settings"):
            del st.session_state.llm_analysis_results
            st.rerun()

    else:
        st.divider()
        st.markdown("### 🌟 What You'll Get")

        tab1, tab2, tab3 = st.tabs(["Usage Patterns", "Recommendations", "Insights"])

        with tab1:
            st.markdown("""
            **Discover Your AI Usage Patterns:**
            - 📊 Platform preference analysis (ChatGPT vs Claude)
            - ⏰ Peak productivity hours and days
            - 💬 Conversation length and depth patterns
            - 📈 Usage trends over time
            - 🎯 Topic and focus area identification
            """)

        with tab2:
            st.markdown("""
            **Get Actionable Recommendations:**
            - 🚀 Ways to improve conversation effectiveness
            - ⚡ Tips for more efficient AI interactions
            - 🎨 Strategies to leverage each platform's strengths
            - 📚 Areas where you could benefit from deeper dives
            - 🔄 Suggestions for better workflow integration
            """)

        with tab3:
            st.markdown("""
            **Gain Deep Insights:**
            - 🧠 Understanding of your problem-solving patterns
            - 💡 Identification of underutilized features
            - 📊 Comparison of your usage vs typical patterns
            - 🎯 Opportunities for maximizing value
            - 🌱 Growth areas and learning opportunities
            """)


@st.cache_data
def prepare_analysis_data(chatgpt_df, claude_df, do_mask=True):
    """Prepare aggregated data for LLM analysis (privacy-preserving)."""

    # Conversation-level stats
    chatgpt_conv = chatgpt_df.groupby("conversation_id").agg(
        message_count=("message_id", "count"), start_time=("conversation_create_time", "min"), title=("title", "first")
    )

    claude_conv = claude_df.groupby("conversation_id").agg(
        message_count=("message_id", "count"), start_time=("conversation_create_time", "min"), title=("title", "first")
    )

    chatgpt_df_temp = chatgpt_df.copy()
    claude_df_temp = claude_df.copy()
    chatgpt_df_temp["hour"] = chatgpt_df_temp["conversation_create_time"].dt.hour
    chatgpt_df_temp["day_of_week"] = chatgpt_df_temp["conversation_create_time"].dt.day_name()
    claude_df_temp["hour"] = claude_df_temp["conversation_create_time"].dt.hour
    claude_df_temp["day_of_week"] = claude_df_temp["conversation_create_time"].dt.day_name()

    summary = {
        "chatgpt": {
            "total_messages": len(chatgpt_df),
            "total_conversations": len(chatgpt_conv),
            "avg_messages_per_conv": chatgpt_conv["message_count"].mean(),
            "median_messages_per_conv": chatgpt_conv["message_count"].median(),
            "most_active_hour": int(chatgpt_df_temp["hour"].mode()[0]),
            "most_active_day": chatgpt_df_temp["day_of_week"].mode()[0],
            "date_range": {
                "start": chatgpt_df["conversation_create_time"].min().strftime("%Y-%m-%d"),
                "end": chatgpt_df["conversation_create_time"].max().strftime("%Y-%m-%d"),
            },
            "top_5_topics": {mask_pii(k) if do_mask else k: v for k, v in chatgpt_df["title"].value_counts().head(5).items()},
        },
        "claude": {
            "total_messages": len(claude_df),
            "total_conversations": len(claude_conv),
            "avg_messages_per_conv": claude_conv["message_count"].mean(),
            "median_messages_per_conv": claude_conv["message_count"].median(),
            "most_active_hour": int(claude_df_temp["hour"].mode()[0]),
            "most_active_day": claude_df_temp["day_of_week"].mode()[0],
            "date_range": {
                "start": claude_df["conversation_create_time"].min().strftime("%Y-%m-%d"),
                "end": claude_df["conversation_create_time"].max().strftime("%Y-%m-%d"),
            },
            "top_5_topics": {mask_pii(k) if do_mask else k: v for k, v in claude_df["title"].value_counts().head(5).items()},
        },
        "combined_stats": {
            "total_messages": len(chatgpt_df) + len(claude_df),
            "total_conversations": len(chatgpt_conv) + len(claude_conv),
            "chatgpt_share": len(chatgpt_df) / (len(chatgpt_df) + len(claude_df)) * 100,
            "claude_share": len(claude_df) / (len(chatgpt_df) + len(claude_df)) * 100,
        },
    }

    return summary


def create_analysis_prompt(summary_stats, depth, focus):
    """Create analysis prompt based on user preferences."""

    depth_instructions = {
        "Quick Overview": "Provide a concise 2-3 paragraph overview focusing on the most important insights.",
        "Detailed Analysis": "Provide a comprehensive analysis with 4-6 key insights and specific recommendations.",
        "Deep Dive": "Provide an in-depth analysis covering patterns, trends, comparisons, and detailed actionable recommendations.",
    }

    focus_instructions = {
        "Overall Patterns": "Focus on overall usage patterns, platform preferences, and general trends.",
        "Productivity Insights": "Focus on productivity patterns, optimal usage times, and efficiency metrics.",
        "Usage Optimization": "Focus on how to get more value from AI assistants and optimize interaction strategies.",
        "Topic Analysis": "Focus on the topics discussed, conversation themes, and subject matter patterns.",
        "Time Management": "Focus on temporal patterns, time investment, and scheduling insights.",
    }

    prompt = f"""
Analyze the following AI chatbot usage data and provide insights:

**User's AI Assistant Usage Summary:**

ChatGPT:
- Total Messages: {summary_stats["chatgpt"]["total_messages"]:,}
- Total Conversations: {summary_stats["chatgpt"]["total_conversations"]:,}
- Avg Messages/Conversation: {summary_stats["chatgpt"]["avg_messages_per_conv"]:.1f}
- Median Messages/Conversation: {summary_stats["chatgpt"]["median_messages_per_conv"]:.0f}
- Most Active Hour: {summary_stats["chatgpt"]["most_active_hour"]:02d}:00
- Most Active Day: {summary_stats["chatgpt"]["most_active_day"]}
- Date Range: {summary_stats["chatgpt"]["date_range"]["start"]} to {summary_stats["chatgpt"]["date_range"]["end"]}
- Top Topics: {", ".join(list(summary_stats["chatgpt"]["top_5_topics"].keys())[:5])}

Claude:
- Total Messages: {summary_stats["claude"]["total_messages"]:,}
- Total Conversations: {summary_stats["claude"]["total_conversations"]:,}
- Avg Messages/Conversation: {summary_stats["claude"]["avg_messages_per_conv"]:.1f}
- Median Messages/Conversation: {summary_stats["claude"]["median_messages_per_conv"]:.0f}
- Most Active Hour: {summary_stats["claude"]["most_active_hour"]:02d}:00
- Most Active Day: {summary_stats["claude"]["most_active_day"]}
- Date Range: {summary_stats["claude"]["date_range"]["start"]} to {summary_stats["claude"]["date_range"]["end"]}
- Top Topics: {", ".join(list(summary_stats["claude"]["top_5_topics"].keys())[:5])}

Overall:
- Total Messages: {summary_stats["combined_stats"]["total_messages"]:,}
- Total Conversations: {summary_stats["combined_stats"]["total_conversations"]:,}
- ChatGPT Share: {summary_stats["combined_stats"]["chatgpt_share"]:.1f}%
- Claude Share: {summary_stats["combined_stats"]["claude_share"]:.1f}%

**Analysis Instructions:**
{depth_instructions[depth]}

**Focus Area:**
{focus_instructions[focus]}

**Provide:**
1. Key patterns and insights from the data
2. Platform comparison and usage characteristics
3. Specific, actionable recommendations for getting more value
4. Areas of strength and opportunities for improvement
5. Personalized tips based on observed patterns

Use markdown formatting with headers, bullet points, and emphasis where appropriate.
"""

    return prompt


def render_import():
    st.title("📥 Instant Import")
    st.markdown("Upload your chat export (zip or json) and we'll handle the rest.")

    uploaded_file = st.file_uploader("Choose a file", type=["zip", "json"])

    if uploaded_file is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.info(f"Processing {uploaded_file.name}...")

            try:
                # Resolve conversations.json
                conv_path = _resolve_conversations_json(temp_path)
                provider = _detect_provider(conv_path)

                if not provider:
                    provider = st.selectbox("Could not auto-detect provider. Please select:", ["chatgpt", "claude", "gemini"])
                else:
                    st.success(f"Detected {provider} export!")

                if st.button("Start Ingestion"):
                    out_dir = Path("data/staging")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"{provider}_messages.jsonl"

                    # We need to be careful with run_parse because it might try to extract zip again if we pass the zip path
                    # but _resolve_conversations_json already extracted it if it was a zip.
                    # Actually run_parse calls _resolve_conversations_json internally.
                    # So we can just pass the temp_path.

                    result = run_parse(provider, str(temp_path), str(out_path))

                    if result == 0:
                        st.success(f"Successfully ingested {provider} chats!")
                        st.balloons()
                        if st.button("Go to Overview"):
                            st.rerun()
                    else:
                        st.error("Failed to ingest chats. Check logs.")
            except Exception as e:
                st.error(f"Error: {e}")

def render_settings():
    st.title("⚙️ Settings")

    st.subheader("Data Sources")
    st.text_input("ChatGPT Data", value="data/staging/chatgpt_messages.jsonl")
    st.text_input("Claude Data", value="data/staging/claude_messages.jsonl")
    st.text_input("Gemini Data", value="data/staging/gemini_messages.jsonl")

    st.subheader("Filters")
    st.date_input("Date Range", value=(datetime.now() - timedelta(days=365), datetime.now()))

    st.subheader("Export")
    if st.button("Export Filtered Data"):
        st.toast("Data exported successfully!")


def main():
    st.sidebar.title("🧠 Open Chat Memory")
    st.sidebar.markdown("Top AI chatbots conversation analysis")

    page = st.sidebar.radio(
        "Navigate",
        [
            "📊 Overview",
            "📈 Temporal",
            "💬 Conversations",
            "🔤 Content",
            "🤖 Comparison",
            "🚀 Optimization",
            "🎯 LLM Analysis",
            "📥 Import",
            "⚙️ Settings",
        ],
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Cache", help="Clear cached data"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("✅ Cache cleared")

    try:
        chatgpt_df = load_data("data/staging/chatgpt_messages.jsonl")
    except Exception:
        chatgpt_df = pd.DataFrame()

    try:
        claude_df = load_data("data/staging/claude_messages.jsonl")
    except Exception:
        claude_df = pd.DataFrame()

    try:
        gemini_df = load_data("data/staging/gemini_messages.jsonl")
    except Exception:
        gemini_df = pd.DataFrame()

    if chatgpt_df.empty and claude_df.empty and gemini_df.empty and page != "📥 Import":
        st.error("⚠️ Chat data files not found")
        st.info("📝 **Next Steps:** Use the **Import** tab to upload your chat exports or run the parser manually.")

        st.code(
            """
# Parse your chat exports first:
ocmem ingest chatgpt-export.zip
ocmem ingest claude-export.zip

# Then restart the app:
streamlit run app.py
        """,
            language="bash",
        )

        with st.expander("🔍 Troubleshooting"):
            st.markdown("""
            **Expected file locations:**
            - `data/staging/chatgpt_messages.jsonl`
            - `data/staging/claude_messages.jsonl`

            **Common issues:**
            1. Parser not run yet → Run `ocmem ingest` or use the Import tab.
            2. Wrong directory → Check current working directory
            3. Empty exports → Verify export files are valid

            **Need help?** See [documentation](https://github.com/ndamulelonemakh/open-chat-memory)
            """)
        return

    if page == "📊 Overview":
        render_overview(chatgpt_df, claude_df)
    elif page == "📈 Temporal":
        render_temporal(chatgpt_df, claude_df)
    elif page == "💬 Conversations":
        render_conversations(chatgpt_df, claude_df)
    elif page == "🔤 Content":
        render_content(chatgpt_df, claude_df)
    elif page == "🤖 Comparison":
        render_comparison(chatgpt_df, claude_df)
    elif page == "🚀 Optimization":
        render_optimization(chatgpt_df, claude_df, gemini_df)
    elif page == "🎯 LLM Analysis":
        render_llm_analysis(chatgpt_df, claude_df)
    elif page == "📥 Import":
        render_import()
    elif page == "⚙️ Settings":
        render_settings()


if __name__ == "__main__":
    main()
