"""Tests for CLI functionality."""

from io import StringIO
from unittest.mock import patch

import pytest

from openchatmemory.cli import build_parser, main


class TestCLI:
    """Test CLI command-line interface."""

    def test_parser_builds(self):
        """Test that argument parser builds successfully."""
        ap = build_parser()
        assert ap is not None

    def test_no_args_shows_help(self):
        """Test that running with no args shows help."""
        with patch("sys.argv", ["ocmem"]), patch("sys.stdout", new_callable=StringIO), pytest.raises(SystemExit):
            main()

    def test_parse_command_requires_provider(self):
        """Test that parse command requires provider argument."""
        with patch("sys.argv", ["ocmem", "parse"]), pytest.raises(SystemExit):
            main()

    def test_parse_command_requires_input(self):
        """Test that parse command requires input argument."""
        with patch("sys.argv", ["ocmem", "parse", "--provider", "chatgpt"]), pytest.raises(SystemExit):
            main()

    def test_db_command_requires_subcommand(self):
        """Test that db command requires a subcommand."""
        with patch("sys.argv", ["ocmem", "db"]), pytest.raises(SystemExit):
            main()

    def test_mem_command_requires_subcommand(self):
        """Test that mem command requires a subcommand."""
        with patch("sys.argv", ["ocmem", "mem"]), pytest.raises(SystemExit):
            main()

    def test_invalid_provider_shows_error(self):
        """Test that invalid provider shows helpful error."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["parse", "--provider", "invalid", "--input", "test.json", "--output", "out.jsonl"])


class TestParserValidation:
    """Test argument parser validation."""

    def test_valid_parse_args(self):
        """Test that valid parse arguments are accepted."""
        parser = build_parser()
        args = parser.parse_args(["parse", "--provider", "chatgpt", "--input", "input.json", "--out", "output.jsonl"])
        assert args.provider == "chatgpt"
        assert args.input == "input.json"
        assert args.out == "output.jsonl"

    def test_valid_db_load_args(self):
        """Test that valid db load arguments are accepted."""
        parser = build_parser()
        args = parser.parse_args(["db", "load", "--input", "data.jsonl", "--db-url", "postgresql://localhost/db"])
        assert args.input == "data.jsonl"
        assert args.db_url == "postgresql://localhost/db"

    def test_valid_mem_push_args(self):
        """Test that valid mem push arguments are accepted."""
        parser = build_parser()
        args = parser.parse_args(["mem", "push", "--input", "data.jsonl", "--user-id", "user123"])
        assert args.input == "data.jsonl"
        assert args.user_id == "user123"
