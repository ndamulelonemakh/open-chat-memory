from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger
from pydantic import ValidationError

from .base import BaseParser, MessageModel, ParserRegistry


class ChatGPTParser(BaseParser):
    provider = "chatgpt"

    def _clean_content(self, value):
        if not value:
            return ""
        if isinstance(value, list):
            return "\n".join([self._clean_content(item) for item in value])
        if isinstance(value, dict):
            return "\n".join([f"{k}: {v}" for k, v in value.items()])
        return str(value).strip().replace("[", "").replace("]", "")

    def parse(self, input_path: Path) -> list[MessageModel]:
        df = pd.read_json(str(input_path))
        records: list[MessageModel] = []
        logger.info(f"Flattening {df.shape[0]} conversations for ChatGPT")
        for _, row in df.iterrows():
            for message_id in row.mapping:
                try:
                    message_details = row.mapping[message_id]
                    message = message_details.get("message")
                    if not message:
                        logger.warning(f"Failed to get message from: {message_id}")
                        continue
                    cleaned_content = self._clean_content(message.get("content", {}).get("parts", []))
                    model = MessageModel(
                        message_id=message.get("id"),
                        role=message.get("author", {}).get("role"),
                        content=cleaned_content,
                        conversation_id=row["conversation_id"],
                        title=row["title"],
                        message_create_time=message.get("create_time"),
                        conversation_create_time=str(row["create_time"]),
                        message_update_time=str(row["update_time"]),
                    )
                    records.append(model)
                except ValidationError:
                    logger.warning(
                        f"Validation error for message_id {message_id} in conversation {row['conversation_id']}"
                    )
                    continue
        return records


ParserRegistry.register(ChatGPTParser.provider, ChatGPTParser)
