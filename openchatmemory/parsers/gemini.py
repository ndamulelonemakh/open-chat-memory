from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from .base import BaseParser, MessageModel, ParserRegistry


class GeminiParser(BaseParser):
    provider = "gemini"

    def parse(self, input_path: Path) -> list[MessageModel]:
        # Gemini Takeout is often a folder with many JSON files,
        # but sometimes it's consolidated. Let's support a basic JSON structure.
        # This is a placeholder for actual Gemini parsing logic.
        try:
            df = pd.read_json(str(input_path))
        except Exception:
            logger.warning(f"Could not read {input_path} as JSON")
            return []

        records: list[MessageModel] = []
        logger.info(f"Flattening conversations for Gemini from {input_path}")

        # Expected Gemini structure (hypothetical/simplified)
        # [ { "prompt": "...", "candidates": [ { "content": "..." } ], "metadata": { "timestamp": ... } } ]

        for idx, row in df.iterrows():
            # Handle prompt (user)
            timestamp = row.get("timestamp")
            if hasattr(timestamp, "timestamp"):
                timestamp = timestamp.timestamp()

            if "prompt" in row:
                records.append(MessageModel(
                    message_id=f"gem-prompt-{idx}",
                    role="user",
                    content=row["prompt"],
                    conversation_id=str(row.get("conversation_id", idx)),
                    title=row.get("title", f"Gemini Chat {idx}"),
                    message_create_time=timestamp,
                ))

            # Handle candidates (assistant)
            if "candidates" in row and isinstance(row["candidates"], list):
                for c_idx, candidate in enumerate(row["candidates"]):
                    content = candidate.get("content")
                    if content:
                        records.append(MessageModel(
                            message_id=f"gem-cand-{idx}-{c_idx}",
                            role="assistant",
                            content=content,
                            conversation_id=str(row.get("conversation_id", idx)),
                            title=row.get("title", f"Gemini Chat {idx}"),
                            message_create_time=timestamp,
                        ))
        return records


ParserRegistry.register(GeminiParser.provider, GeminiParser)
