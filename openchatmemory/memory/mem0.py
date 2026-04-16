from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict

from loguru import logger
from mem0 import Memory
from mem0.configs.base import MemoryConfig


def _get_default_mem0_config() -> dict:
    neo4j_url = os.getenv("NEO4J_URL")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_pass = os.getenv("NEO4J_PASSWORD")
    neo4j_db = os.getenv("NEO4J_DATABASE")

    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": os.getenv("MEMORY_LLM_MODEL", "gpt-5-nano"),
                "temperature": 0.7,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": os.getenv("MEMORY_EMBED_MODEL", "all-MiniLM-L6-v2"),
                "model_kwargs": {"device": "cpu", "trust_remote_code": True},
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": os.getenv("QDRANT_COLLECTION", "openchatmemory"),
                "path": None if os.getenv("QDRANT_URL") else "./data/qdrant_data",
                "host": os.getenv("QDRANT_HOST"),
                "port": int(os.getenv("QDRANT_PORT")) if os.getenv("QDRANT_PORT") else None,
                "embedding_model_dims": 384,  # all-MiniLM-L6-v2 dimension
            },
        },
        "version": "v1.1",
    }

    if neo4j_url:
        config["graph_store"] = {
            "provider": "neo4j",
            "config": {
                "url": neo4j_url,
                "username": neo4j_user,
                "password": neo4j_pass,
                "database": neo4j_db,
            },
        }

    return config


class MemoryMessage(TypedDict, total=False):
    """Type definition for memory messages sent to Mem0."""

    role: str
    content: str


def _iter_jsonl(path: Path):
    """Iterate over JSONL file line by line.

    Args:
        path: Path to the JSONL file

    Yields:
        Parsed JSON objects from each line
    """
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            if line.strip():
                yield json.loads(line)


def _prepare_memories(jsonl_path: Path) -> dict[str, list[MemoryMessage]]:
    """Group messages by conversation for memory storage.

    Args:
        jsonl_path: Path to JSONL file with messages

    Returns:
        Dictionary mapping conversation_id to list of memory messages
    """
    conversations: dict[str, list[MemoryMessage]] = {}
    for row in _iter_jsonl(jsonl_path):
        conv_id = str(row.get("conversation_id"))
        conversations.setdefault(conv_id, [])

        role = str(row.get("role") or "user")
        content = row.get("content")
        if isinstance(content, list):
            text = "\n".join(str(x) for x in content)
        elif isinstance(content, dict):
            text = "\n".join(f"{k}: {v}" for k, v in content.items())
        else:
            text = str(content or "")

        if not text.strip():
            continue
        conversations[conv_id].append({"role": role, "content": text})
    return conversations


def push_memories(jsonl_path: Path, user_id: str, provider: str = "chatgpt") -> int:
    """Push grouped conversation memories to Mem0.

    Reads messages from a JSONL file, groups them by conversation, and pushes
    each conversation as a memory to Mem0 with metadata for retrieval.

    Args:
        jsonl_path: Path to JSONL file containing messages
        user_id: User identifier for memory association
        provider: Chat provider name (default: "chatgpt")

    Returns:
        0 on success, 2 if mem0ai is not installed

    Example:
        >>> from pathlib import Path
        >>> result = push_memories(
        ...     Path("messages.jsonl"),
        ...     user_id="user123",
        ...     provider="chatgpt"
        ... )
        >>> result
        0
    """
    if Memory is None:
        logger.error("mem0ai is not installed. Install with: pip install .[mem0]")
        return 2

    config_dict = _get_default_mem0_config()
    mem = Memory(config=MemoryConfig(**config_dict))
    grouped = _prepare_memories(jsonl_path)
    total = 0
    for conv_id, messages in grouped.items():
        metadata = {
            "platform": provider,
            "conversation_id": conv_id,
        }
        try:
            result = mem.add(messages, user_id=user_id, metadata=metadata, infer=True)
            total += len(result)
            logger.info(f"Saved {len(result)} memories for conversation {conv_id}")
        except Exception as e:  # pragma: no cover - runtime error path
            logger.exception(f"Failed to save memories for {conv_id}: {e}")
    logger.success(f"Pushed {total} memories to Mem0")
    return 0
