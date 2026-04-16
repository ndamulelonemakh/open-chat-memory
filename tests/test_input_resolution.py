"""Tests for input path resolution in CLI."""

import json
import zipfile

import pytest

from openchatmemory.cli import _resolve_conversations_json


class TestInputResolution:
    """Test _resolve_conversations_json handles all input formats."""

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations.json content."""
        return [
            {
                "conversation_id": "test-123",
                "title": "Test",
                "create_time": 1704067200.0,
                "update_time": 1704067200.0,
                "mapping": {},
            }
        ]

    def test_direct_conversations_json_path(self, tmp_path, sample_conversations):
        """Test with direct path to conversations.json."""
        conv_file = tmp_path / "conversations.json"
        with open(conv_file, "w") as f:
            json.dump(sample_conversations, f)

        result = _resolve_conversations_json(conv_file)
        assert result == conv_file
        assert result.exists()

    def test_directory_containing_conversations_json(self, tmp_path, sample_conversations):
        """Test with directory containing conversations.json."""
        export_dir = tmp_path / "export"
        export_dir.mkdir()
        conv_file = export_dir / "conversations.json"
        with open(conv_file, "w") as f:
            json.dump(sample_conversations, f)

        result = _resolve_conversations_json(export_dir)
        assert result == conv_file
        assert result.exists()

    def test_zip_file_containing_conversations_json(self, tmp_path, sample_conversations):
        """Test with zip file containing conversations.json."""
        # Create temp conversations.json
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        conv_file = temp_dir / "conversations.json"
        with open(conv_file, "w") as f:
            json.dump(sample_conversations, f)

        # Create zip file
        zip_path = tmp_path / "export.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.write(conv_file, arcname="conversations.json")

        result = _resolve_conversations_json(zip_path)
        assert result.name == "conversations.json"
        assert result.exists()

    def test_directory_without_conversations_json(self, tmp_path):
        """Test directory without conversations.json raises error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="conversations.json not found in directory"):
            _resolve_conversations_json(empty_dir)

    def test_zip_without_conversations_json(self, tmp_path):
        """Test zip without conversations.json raises error."""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr("other.json", "{}")

        with pytest.raises(FileNotFoundError, match="conversations.json not found in zip"):
            _resolve_conversations_json(zip_path)

    def test_nonexistent_path(self, tmp_path):
        """Test nonexistent path raises error."""
        nonexistent = tmp_path / "does_not_exist.json"

        with pytest.raises(FileNotFoundError, match="Input path does not exist"):
            _resolve_conversations_json(nonexistent)

    def test_unsupported_file_type(self, tmp_path):
        """Test unsupported file type raises error."""
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("test")

        with pytest.raises(ValueError, match="Unsupported input format"):
            _resolve_conversations_json(txt_file)
