# Open Chat Memory - AI Assistant Instructions

## Project Overview
This is an ETL pipeline for AI chat exports (ChatGPT, Claude) that normalizes conversations into JSONL, loads them into PostgreSQL, and pushes grouped memories to Mem0 vector store. The CLI tool `ocmem` orchestrates the entire workflow.

## Core Architecture

### Data Flow Pipeline
1. **Parse** (`ocmem parse`): Raw JSON exports → Normalized JSONL via provider-specific parsers
2. **Load** (`ocmem db load`): JSONL → PostgreSQL via SQLAlchemy 
3. **Memory** (`ocmem mem push`): JSONL → Mem0 vector store with conversation grouping

### Key Components
- **Parsers** (`openchatmemory/parsers/`): Provider-specific parsers inherit from `BaseParser`, auto-register via `ParserRegistry`
- **Schemas** (`openchatmemory/schemas/`): `MessageModel` is the canonical normalized format with strict Pydantic validation
- **CLI** (`openchatmemory/cli.py`): Single entry point with subcommands, handles input resolution (files/dirs/zips)
- **Memory Integration** (`openchatmemory/memory/mem0.py`): Groups messages by conversation, configures Qdrant/Neo4j backends

## Development Patterns

### Parser Implementation
```python
# All parsers must inherit BaseParser and auto-register
class NewProviderParser(BaseParser):
    provider = "newprovider"  # Registry key
    
    def parse(self, input_path: Path) -> list[MessageModel]:
        # Provider-specific parsing logic
        pass

# Auto-registration at module level
ParserRegistry.register(NewProviderParser.provider, NewProviderParser)
```

### Content Normalization
Parsers must flatten complex content structures (arrays/dicts) into strings. See `ChatGPTParser._clean_content()` for the pattern - handles nested lists/dicts by joining with newlines and key-value formatting.

### Input Resolution
CLI accepts flexible inputs via `_resolve_conversations_json()`: direct `conversations.json` files, directories containing them, or `.zip` exports (auto-extracts and locates the JSON).

## Configuration & Environment

### Development Setup
```bash
pip install -e .[db,mem0]  # Install with optional dependencies
cp .env.example .env       # Configure environment variables
pytest -q                  # Run tests (use pytest task if available)
```

### Environment Hierarchy
- **Required**: `OPENAI_API_KEY` (for Mem0 features only)
- **Vector Store**: Qdrant config - leave `QDRANT_URL` empty for local file storage at `./data/qdrant_data`
- **Optional**: Neo4j graph store, PostgreSQL for `db load` command

### Testing Patterns
- Use `tmp_path` fixture for file-based tests
- Mock conversation exports with minimal valid JSON structure
- Test parser registry functionality and MessageModel validation
- Validate both happy path and error cases (empty content, validation errors)

## Critical Implementation Notes

### Message Validation
`MessageModel` has strict content validation - empty strings, None, empty dicts/lists are rejected. Content can be text, dict, or list but must contain actual data.

### Error Handling
Parsers should log warnings for individual message failures but continue processing the conversation. Use `logger.warning()` for non-fatal issues, `logger.error()` for failures.

### Provider Registration
New parsers auto-register by importing their module. The `__init__.py` files in `parsers/` ensure registration happens on import.

### CLI Architecture
Uses argparse with subparsers. Each command has a dedicated `_cmd_*` function that returns an exit code (0=success, >0=error). Main CLI handles logging configuration and exit code propagation.

## Key Files to Understand
- `openchatmemory/cli.py` - Complete CLI implementation and input handling
- `openchatmemory/schemas/__init__.py` - Canonical MessageModel with validation
- `openchatmemory/parsers/base.py` - Parser interface and registry pattern
- `openchatmemory/parsers/chatgpt.py` - Reference parser implementation
- `tests/test_parsers.py` - Testing patterns and fixtures