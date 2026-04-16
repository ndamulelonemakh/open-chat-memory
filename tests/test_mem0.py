"""Pure unit tests for mem0 module functions without external dependencies."""

import json
import os
from unittest.mock import patch

from openchatmemory.memory.mem0 import _get_default_mem0_config, _iter_jsonl, _prepare_memories


class TestIterJsonl:
    """Unit tests for _iter_jsonl function."""

    def test_iter_jsonl_basic(self, tmp_path):
        """Test basic JSONL iteration."""
        jsonl_file = tmp_path / "test.jsonl"
        data = [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"},
        ]
        with jsonl_file.open("w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        result = list(_iter_jsonl(jsonl_file))
        assert len(result) == 2
        assert result[0] == {"id": 1, "value": "first"}
        assert result[1] == {"id": 2, "value": "second"}

    def test_iter_jsonl_empty_lines(self, tmp_path):
        """Test that empty lines are skipped."""
        jsonl_file = tmp_path / "test.jsonl"
        with jsonl_file.open("w") as f:
            f.write('{"id": 1}\n')
            f.write("\n")
            f.write("   \n")
            f.write('{"id": 2}\n')

        result = list(_iter_jsonl(jsonl_file))
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_iter_jsonl_empty_file(self, tmp_path):
        """Test empty JSONL file."""
        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.touch()

        result = list(_iter_jsonl(jsonl_file))
        assert result == []

    def test_iter_jsonl_unicode(self, tmp_path):
        """Test Unicode content handling."""
        jsonl_file = tmp_path / "unicode.jsonl"
        data = {"text": "Hello 世界 🌍"}
        with jsonl_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

        result = list(_iter_jsonl(jsonl_file))
        assert len(result) == 1
        assert result[0]["text"] == "Hello 世界 🌍"


class TestPrepareMemories:
    """Unit tests for _prepare_memories function."""

    def test_prepare_memories_basic(self, tmp_path):
        """Test basic message preparation."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": "Hello"},
            {"conversation_id": "conv1", "role": "assistant", "content": "Hi there"},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        assert "conv1" in result
        assert len(result["conv1"]) == 2
        assert result["conv1"][0]["role"] == "user"
        assert result["conv1"][0]["content"] == "Hello"
        assert result["conv1"][1]["role"] == "assistant"

    def test_prepare_memories_multiple_conversations(self, tmp_path):
        """Test grouping by conversation_id."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": "First"},
            {"conversation_id": "conv2", "role": "user", "content": "Second"},
            {"conversation_id": "conv1", "role": "assistant", "content": "Reply"},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        assert len(result) == 2
        assert len(result["conv1"]) == 2
        assert len(result["conv2"]) == 1

    def test_prepare_memories_list_content(self, tmp_path):
        """Test content as list is joined with newlines."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": ["Line 1", "Line 2", "Line 3"]},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        assert result["conv1"][0]["content"] == "Line 1\nLine 2\nLine 3"

    def test_prepare_memories_dict_content(self, tmp_path):
        """Test content as dict is formatted as key: value pairs."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": {"key1": "value1", "key2": "value2"}},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        content = result["conv1"][0]["content"]
        assert "key1: value1" in content
        assert "key2: value2" in content

    def test_prepare_memories_empty_content(self, tmp_path):
        """Test that empty content is skipped."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": "Valid"},
            {"conversation_id": "conv1", "role": "user", "content": ""},
            {"conversation_id": "conv1", "role": "user", "content": "   "},
            {"conversation_id": "conv1", "role": "assistant", "content": "Response"},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        assert len(result["conv1"]) == 2
        assert result["conv1"][0]["content"] == "Valid"
        assert result["conv1"][1]["content"] == "Response"

    def test_prepare_memories_missing_role(self, tmp_path):
        """Test default role when missing."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "content": "No role specified"},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        assert result["conv1"][0]["role"] == "user"

    def test_prepare_memories_null_content(self, tmp_path):
        """Test handling of null/None content."""
        jsonl_file = tmp_path / "messages.jsonl"
        messages = [
            {"conversation_id": "conv1", "role": "user", "content": None},
            {"conversation_id": "conv1", "role": "user", "content": "Valid"},
        ]
        with jsonl_file.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = _prepare_memories(jsonl_file)
        # None content should be skipped
        assert len(result["conv1"]) == 1
        assert result["conv1"][0]["content"] == "Valid"


class TestGetDefaultMem0Config:
    """Unit tests for _get_default_mem0_config function."""

    def test_default_config_structure(self):
        """Test config has required structure without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()

            assert "llm" in config
            assert "embedder" in config
            assert "vector_store" in config
            assert "version" in config
            assert config["version"] == "v1.1"

    def test_default_llm_config(self):
        """Test default LLM configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()

            assert config["llm"]["provider"] == "openai"
            assert config["llm"]["config"]["model"] == "gpt-5-nano"
            assert config["llm"]["config"]["temperature"] == 0.7

    def test_default_embedder_config(self):
        """Test default embedder configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()

            assert config["embedder"]["provider"] == "huggingface"
            assert config["embedder"]["config"]["model"] == "all-MiniLM-L6-v2"
            assert "model_kwargs" in config["embedder"]["config"]

    def test_default_vector_store_config(self):
        """Test default vector store configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()

            vs_config = config["vector_store"]["config"]
            assert config["vector_store"]["provider"] == "qdrant"
            assert vs_config["collection_name"] == "openchatmemory"
            assert vs_config["embedding_model_dims"] == 384
            assert vs_config["path"] == "./data/qdrant_data"

    def test_vector_store_path_none_when_url_set(self):
        """Test path is None when QDRANT_URL is set."""
        with patch.dict(os.environ, {"QDRANT_URL": "http://remote:6333"}, clear=True):
            config = _get_default_mem0_config()
            assert config["vector_store"]["config"]["path"] is None

    def test_vector_store_path_set_when_no_url(self):
        """Test path is set when QDRANT_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()
            assert config["vector_store"]["config"]["path"] == "./data/qdrant_data"

    def test_neo4j_not_included_without_url(self):
        """Test Neo4j graph_store is not included when NEO4J_URL not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = _get_default_mem0_config()
            assert "graph_store" not in config

    def test_neo4j_included_with_url(self):
        """Test Neo4j graph_store is included when NEO4J_URL is set."""
        env_vars = {
            "NEO4J_URL": "neo4j://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "password",
            "NEO4J_DATABASE": "mem0",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = _get_default_mem0_config()

            assert "graph_store" in config
            assert config["graph_store"]["provider"] == "neo4j"
            assert config["graph_store"]["config"]["url"] == "neo4j://localhost:7687"
            assert config["graph_store"]["config"]["username"] == "neo4j"
            assert config["graph_store"]["config"]["password"] == "password"
            assert config["graph_store"]["config"]["database"] == "mem0"

    def test_custom_llm_model_env_var(self):
        """Test MEMORY_LLM_MODEL env var override."""
        with patch.dict(os.environ, {"MEMORY_LLM_MODEL": "gpt-5-mini"}, clear=True):
            config = _get_default_mem0_config()
            assert config["llm"]["config"]["model"] == "gpt-5-mini"

    def test_custom_embed_model_env_var(self):
        """Test MEMORY_EMBED_MODEL env var override."""
        with patch.dict(os.environ, {"MEMORY_EMBED_MODEL": "custom-embed-model"}, clear=True):
            config = _get_default_mem0_config()
            assert config["embedder"]["config"]["model"] == "custom-embed-model"

    def test_custom_qdrant_collection_env_var(self):
        """Test QDRANT_COLLECTION env var override."""
        with patch.dict(os.environ, {"QDRANT_COLLECTION": "my_collection"}, clear=True):
            config = _get_default_mem0_config()
            assert config["vector_store"]["config"]["collection_name"] == "my_collection"

    def test_qdrant_host_port_env_vars(self):
        """Test QDRANT_HOST and QDRANT_PORT env var override."""
        env_vars = {
            "QDRANT_HOST": "qdrant.example.com",
            "QDRANT_PORT": "9999",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = _get_default_mem0_config()
            vs_config = config["vector_store"]["config"]
            assert vs_config["host"] == "qdrant.example.com"
            assert vs_config["port"] == 9999

    def test_all_env_vars_combined(self):
        """Test all environment variables work together."""
        env_vars = {
            "MEMORY_LLM_MODEL": "gpt-5",
            "MEMORY_EMBED_MODEL": "text-embedding-3-large",
            "QDRANT_COLLECTION": "prod_memories",
            "QDRANT_HOST": "prod.qdrant.io",
            "QDRANT_PORT": "6333",
            "QDRANT_URL": "https://prod.qdrant.io",
            "NEO4J_URL": "neo4j+s://prod.neo4j.io:7687",
            "NEO4J_USERNAME": "admin",
            "NEO4J_PASSWORD": "secure_pass",
            "NEO4J_DATABASE": "production",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = _get_default_mem0_config()

            # LLM
            assert config["llm"]["config"]["model"] == "gpt-5"
            # Embedder
            assert config["embedder"]["config"]["model"] == "text-embedding-3-large"
            # Vector store
            vs_config = config["vector_store"]["config"]
            assert vs_config["collection_name"] == "prod_memories"
            assert vs_config["host"] == "prod.qdrant.io"
            assert vs_config["port"] == 6333
            assert vs_config["path"] is None  # URL is set
            # Graph store
            assert "graph_store" in config
            assert config["graph_store"]["config"]["url"] == "neo4j+s://prod.neo4j.io:7687"
            assert config["graph_store"]["config"]["username"] == "admin"
