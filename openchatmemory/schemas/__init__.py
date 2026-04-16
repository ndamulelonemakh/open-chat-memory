"""Core data models and schemas for openchatmemory.

This module defines the canonical data structures used throughout the package,
including message models, validation, and serialization schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MessageModel(BaseModel):
    """Normalized message model for chat conversations.

    This model represents a single message from any chat provider in a standardized
    format, enabling consistent processing across different sources.

    Attributes:
        message_id: Unique identifier for the message
        conversation_id: Identifier for the conversation this message belongs to
        role: The role of the message author (e.g., 'user', 'assistant', 'system')
        content: The message content (can be text, dict, or list)
        message_create_time: Timestamp when the message was created
        title: Title of the conversation
        conversation_create_time: Timestamp when the conversation was created
        author: Author information (provider-specific)
        message_update_time: Timestamp when the message was last updated

    Example:
        >>> msg = MessageModel(
        ...     message_id="msg_123",
        ...     conversation_id="conv_456",
        ...     role="user",
        ...     content="Hello, world!",
        ... )
        >>> msg.role
        'user'
    """

    message_id: str = Field(..., min_length=1, description="Unique message identifier")
    conversation_id: str = Field(..., min_length=1, description="Conversation identifier")
    role: str = Field(..., min_length=1, description="Message author role")
    content: object = Field(..., description="Message content")
    message_create_time: float | int | str | None = Field(None, description="Message creation timestamp")
    title: str = Field("", description="Conversation title")
    conversation_create_time: str | None = Field(None, description="Conversation creation timestamp")
    author: str | None = Field(None, description="Author information")
    message_update_time: str | None = Field(None, description="Message update timestamp")

    @field_validator("content")
    @classmethod
    def _validate_content(cls, v):
        """Validate that content is not empty.

        Args:
            v: The content value to validate

        Returns:
            The validated content

        Raises:
            ValueError: If content is None, empty dict, empty list, or empty string
        """
        if v is None:
            raise ValueError("content cannot be None")
        if isinstance(v, dict) and not v:
            raise ValueError("content cannot be empty dict")
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("content cannot be empty list")
        if isinstance(v, str) and not v.strip():
            raise ValueError("content cannot be empty string")
        return v


__all__ = ["MessageModel"]
