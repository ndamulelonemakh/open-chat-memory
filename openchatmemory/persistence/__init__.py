"""Database persistence layer for storing chat messages.

This module provides functionality to persist normalized chat messages
into various database backends with proper schema management.
"""

from .postgres import load_jsonl_to_postgres

__all__ = ["load_jsonl_to_postgres"]
