"""Tests for parser functionality."""

import json

import pytest

from openchatmemory.parsers import ChatGPTParser, ClaudeParser, ParserRegistry
from openchatmemory.schemas import MessageModel


class TestParserRegistry:
    """Test parser registry functionality."""

    def test_registry_has_chatgpt(self):
        assert "chatgpt" in ParserRegistry.available()

    def test_registry_has_claude(self):
        assert "claude" in ParserRegistry.available()

    def test_get_parser_chatgpt(self):
        parser_cls = ParserRegistry.get("chatgpt")
        assert parser_cls is not None
        assert parser_cls == ChatGPTParser

    def test_get_parser_claude(self):
        parser_cls = ParserRegistry.get("claude")
        assert parser_cls is not None
        assert parser_cls == ClaudeParser

    def test_get_parser_invalid(self):
        result = ParserRegistry.get("unknown")
        assert result is None


class TestChatGPTParser:
    """Test ChatGPT parser."""

    @pytest.fixture
    def sample_chatgpt_data(self, tmp_path):
        """Create sample ChatGPT conversation export."""
        data = [
            {
                "conversation_id": "conv-123",
                "title": "Test Conversation",
                "create_time": 1704067200.0,
                "update_time": 1704067200.0,
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "message": {
                            "id": "msg-1",
                            "author": {"role": "user", "name": None, "metadata": {}},
                            "content": {"content_type": "text", "parts": ["Hello"]},
                            "create_time": 1704067200.0,
                            "status": "finished_successfully",
                        },
                        "parent": None,
                        "children": [],
                    }
                },
            }
        ]
        file_path = tmp_path / "conversations.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
        return file_path

    def test_parse_conversation(self, sample_chatgpt_data):
        parser = ChatGPTParser()
        messages = list(parser.parse(sample_chatgpt_data))
        assert len(messages) >= 1
        # Find user messages (skip system messages)
        user_messages = [m for m in messages if m.role == "user"]
        assert len(user_messages) == 1
        assert isinstance(user_messages[0], MessageModel)
        assert user_messages[0].content == "Hello"
        assert user_messages[0].conversation_id == "conv-123"


class TestClaudeParser:
    """Test Claude parser."""

    @pytest.fixture
    def sample_claude_data(self, tmp_path):
        """Create sample Claude conversation export."""
        data = [
            {
                "uuid": "conv-456",
                "name": "Test Chat",
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z",
                "account": {"uuid": "user-123"},
                "chat_messages": [
                    {
                        "uuid": "msg-1",
                        "sender": "human",
                        "text": "Hi there",
                        "content": [
                            {
                                "type": "text",
                                "text": "Hi there",
                            }
                        ],
                        "created_at": "2024-01-01T00:00:00.000000Z",
                        "updated_at": "2024-01-01T00:00:00.000000Z",
                    }
                ],
            }
        ]
        file_path = tmp_path / "conversations.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
        return file_path

    def test_parse_conversation(self, sample_claude_data):
        parser = ClaudeParser()
        messages = list(parser.parse(sample_claude_data))
        assert len(messages) == 1
        assert isinstance(messages[0], MessageModel)
        assert messages[0].role == "human"
        assert messages[0].content == "Hi there"
        assert messages[0].conversation_id == "conv-456"


class TestMessageModel:
    """Test MessageModel validation with current schema fields."""

    def test_valid_message(self):
        msg = MessageModel(
            conversation_id="conv-1",
            message_id="msg-1",
            role="user",
            content="Hello",
            title="Test Conversation",
            message_create_time=1704067200.0,
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.title == "Test Conversation"

    def test_custom_role(self):
        msg = MessageModel(
            conversation_id="conv-1",
            message_id="msg-1",
            role="custom_role",
            content="Hello",
        )
        assert msg.role == "custom_role"

    def test_empty_content_fails(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="content cannot be empty"):
            MessageModel(
                conversation_id="conv-1",
                message_id="msg-1",
                role="user",
                content=" ",
            )

    def test_none_content_fails(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MessageModel(
                conversation_id="conv-1",
                message_id="msg-1",
                role="user",
                content=None,  # type: ignore[arg-type]
            )
