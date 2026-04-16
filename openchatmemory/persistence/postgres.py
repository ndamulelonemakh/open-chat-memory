from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ChatHeading(Base):
    """SQLAlchemy model for conversation headings."""

    __tablename__ = "chat_headings"
    __table_args__ = {"schema": "chats"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    date = Column(String)


class Message(Base):
    """SQLAlchemy model for chat messages."""

    __tablename__ = "messages"
    __table_args__ = {"schema": "chats"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True, nullable=False)
    conversation_id = Column(String)
    role = Column(String)
    content = Column(Text)
    chatbot_type = Column(String)
    message_create_time = Column(String)
    meta = Column(JSONB)


def _iter_jsonl(jsonl_path: Path) -> Iterable[dict[str, Any]]:
    """Iterate over JSONL file line by line.

    Args:
        jsonl_path: Path to the JSONL file

    Yields:
        Parsed JSON objects from each line
    """
    with jsonl_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            if line.strip():
                yield json.loads(line)


def load_jsonl_to_postgres(
    jsonl_path: Path,
    db_url: str,
    chatbot_type: str = "chatgpt",
    batch_size: int = 1000,
) -> int:
    """Load messages from JSONL file into PostgreSQL database.

    Creates tables if they don't exist and performs batch inserts with
    automatic deduplication based on message_id.

    Args:
        jsonl_path: Path to the JSONL file containing messages
        db_url: PostgreSQL connection URL (e.g., postgresql://user:pass@host/db)
        chatbot_type: Provider type identifier (default: "chatgpt")

    Returns:
        Number of messages inserted (excluding duplicates)

    Example:
        >>> from pathlib import Path
        >>> count = load_jsonl_to_postgres(
        ...     Path("messages.jsonl"),
        ...     "postgresql://localhost/chatdb",
        ...     chatbot_type="chatgpt"
        ... )
        >>> print(f"Inserted {count} messages")
    """
    logger.info(f"Loading messages from {jsonl_path} into Postgres (batch_size={batch_size})")
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)

    inserted = 0
    with session_factory.begin() as session:
        headings_cache: dict[str, bool] = {}
        batch: list[dict[str, Any]] = []
        for msg in _iter_jsonl(jsonl_path):
            # Prepare row
            batch.append(
                {
                    "message_id": msg.get("message_id"),
                    "conversation_id": msg.get("conversation_id"),
                    "role": msg.get("role"),
                    "content": json.dumps(msg.get("content")),
                    "chatbot_type": chatbot_type,
                    "message_create_time": str(msg.get("message_create_time")),
                    "meta": {
                        "etlDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "activity": "CLI",
                    },
                }
            )

            conv_id = str(msg.get("conversation_id"))
            if conv_id and conv_id not in headings_cache:
                stmt_head = (
                    insert(ChatHeading)
                    .values(
                        {
                            "conversation_id": conv_id,
                            "title": str(msg.get("title") or ""),
                            "date": str(msg.get("conversation_create_time") or ""),
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["conversation_id"])
                )  # type: ignore[arg-type]
                session.execute(stmt_head)
                headings_cache[conv_id] = True

            if len(batch) >= batch_size:
                stmt = insert(Message).values(batch).on_conflict_do_nothing(index_elements=["message_id"])  # type: ignore[arg-type]
                session.execute(stmt)
                inserted += len(batch)
                batch = []

        if batch:
            stmt = insert(Message).values(batch).on_conflict_do_nothing(index_elements=["message_id"])  # type: ignore[arg-type]
            session.execute(stmt)
            inserted += len(batch)

    logger.success(f"Inserted up to {inserted} messages (duplicates ignored)")
    return inserted
