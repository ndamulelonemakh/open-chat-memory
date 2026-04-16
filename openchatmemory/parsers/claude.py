from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from .base import BaseParser, MessageModel, ParserRegistry


class ClaudeParser(BaseParser):
    provider = "claude"

    def parse(self, input_path: Path) -> list[MessageModel]:
        df = pd.read_json(str(input_path))
        records: list[MessageModel] = []
        logger.info(f"Flattening {df.shape[0]} conversations for Claude")
        for _, row in df.iterrows():
            for message in row.chat_messages:
                if message.get("author", {}).get("role") == "system":
                    continue
                text = message.get("text")
                if not text:
                    logger.warning(f"Failed to get content from: {message}")
                    continue
                model = MessageModel(
                    message_id=message.get("uuid"),
                    role=message.get("sender"),
                    content=text,
                    conversation_id=row["uuid"],
                    title=row["name"],
                    message_create_time=message.get("created_at"),
                    message_update_time=message.get("updated_at"),
                    conversation_create_time=str(row["created_at"]),
                )
                records.append(model)
        return records


ParserRegistry.register(ClaudeParser.provider, ClaudeParser)
