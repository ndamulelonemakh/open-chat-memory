import json
import pytest
from pathlib import Path
from openchatmemory.parsers.gemini import GeminiParser
from openchatmemory.schemas import MessageModel

class TestGeminiParser:
    @pytest.fixture
    def sample_gemini_data(self, tmp_path):
        data = [
            {
                "conversation_id": "gem-123",
                "title": "Gemini Test",
                "timestamp": 1704067200.0,
                "prompt": "Hello Gemini",
                "candidates": [
                    {"content": "Hello User"}
                ]
            }
        ]
        file_path = tmp_path / "conversations.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
        return file_path

    def test_parse_gemini(self, sample_gemini_data):
        parser = GeminiParser()
        messages = parser.parse(sample_gemini_data)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello Gemini"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hello User"
