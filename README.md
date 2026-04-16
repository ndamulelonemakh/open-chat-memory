# Open Chat Memory (ocmem) [WIP]

Parse AI chat exports (ChatGPT, Claude, etc.), load them into a database, and publish grouped memories to memory stores (like Mem0).

Official project name: openchatmemory

CLI name: ocmem (also available: openchatmemory)

## Motivation

> I have always been curios about my behavior and patterns when using AI chat services. However, these platforms often retain this insights for their own analytics and bulk profiling. This project is an attempt to make such insights accessible in a privacy-preserving manner. You are welcome to adopt and extend it as you see fit.

## Features

- Parsers for different providers to normalize conversations
- Database loader for `Postgres` via SQLAlchemy
- Memory loader to group messages by conversation and push to `Mem0`
- Single CLI `ocmem` to run end-to-end

![Example analysis output](docs/images/chatgpt_temporal.png)

## Install

```bash
pip install -e .
# or with extras
pip install -e .[db]
pip install -e .[mem0]
pip install -e .[db,mem0]
```

## Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your credentials. At minimum, set:
- `OPENAI_API_KEY` (required for Mem0 features)

See [Environment Variables](#environment-variables) section below for all options.

* [Demo app]() - `streamlit run app.py`

![AI Overview Screenshot](docs/images/ai_overviews.png)

## Quickstart

```bash
# Parse exports - accepts conversations.json, directory, or .zip
ocmem parse --provider chatgpt --input data/interim/chatgpt/conversations.json --out data/final/chatgpt/messages.jsonl

# Load to PostgreSQL
ocmem db load --input data/final/chatgpt/messages.jsonl --db-url $DATABASE_URL --provider chatgpt

# Push to Mem0
ocmem mem push --input data/final/chatgpt/messages.jsonl --user-id your_user --provider chatgpt
```

**Note:** The `--input` flag for `parse` accepts:
- Direct path to `conversations.json`
- Directory containing `conversations.json` (macOS auto-extracts zips)
- `.zip` export file (will extract and locate `conversations.json`)

## Analysis Examples

Example scripts showing what you can do with parsed chat history:

The export files under `docs/examples/*-export-sample/` are synthetic public fixtures. Do not commit real chat exports, user profiles, phone numbers, or provider-generated system context to this repository.

### Statistical EDA
```bash
python docs/examples/eda_analysis.py
```
Generates temporal patterns, word clouds, and platform comparisons.

### LLM-Powered Analysis
```bash
export OPENAI_API_KEY="your-key-here"
python docs/examples/llm_conversation_analysis.py
```

📚 **[View Analysis Examples Documentation →](docs/analysis-tools-index.md)**

## JSONL Output Schema

Each line produced by `ocmem parse` is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | string | Unique identifier for the message (provider native) |
| `conversation_id` | string | Conversation/thread identifier |
| `role` | string | Author role (e.g. `user`, `assistant`, `human`, `system`) |
| `content` | string | Normalized text content (arrays/dicts flattened) |
| `title` | string | Conversation title if available |
| `message_create_time` | number/string/null | Original message creation timestamp |
| `conversation_create_time` | string/null | Conversation creation timestamp |
| `message_update_time` | string/null | Message update timestamp |

Example line:

```json
{"message_id": "msg-1", "conversation_id": "conv-123", "role": "user", "content": "Hello", "title": "Test Conversation", "message_create_time": 1704067200.0}
```

## Environment Variables

All configuration is optional except `OPENAI_API_KEY` (required for `mem push`).

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _none_ | **Required** for Mem0. Get from [OpenAI Platform](https://platform.openai.com/api-keys) |
| `MEMORY_LLM_MODEL` | `gpt-5-nano` | LLM for memory processing (gpt-5-nano, gpt-5-mini, gpt-4o-mini) |
| `MEMORY_EMBED_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |

### Qdrant Vector Store

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_COLLECTION` | `openchatmemory` | Collection name |
| `QDRANT_URL` | _none_ | Remote Qdrant URL (if set, uses remote; else local file storage) |
| `QDRANT_HOST` | _none_ | Qdrant host (for remote) |
| `QDRANT_PORT` | _none_ | Qdrant port (for remote) |
| `QDRANT_API_KEY` | _none_ | API key (for remote) |

**Local setup:** Leave `QDRANT_URL` empty → uses `./data/qdrant_data`

**Docker setup:**
```bash
docker run -d -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant
```

### Neo4j Graph Store (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URL` | _none_ | Neo4j connection URL. If omitted, graph store disabled |
| `NEO4J_USERNAME` | _none_ | Neo4j username |
| `NEO4J_PASSWORD` | _none_ | Neo4j password |
| `NEO4J_DATABASE` | _none_ | Neo4j database name |

**Docker setup:**
```bash
docker run -d -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:latest
```

### PostgreSQL (for `db load`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | _none_ | Full PostgreSQL connection string |

Example: `postgresql://user:pass@localhost:5432/chatdb`



See [`.env.example`](.env.example) for a complete template.

## Development

- Python 3.11+
- Run tests: `pytest -q`
- Lint/typecheck: `ruff`, `mypy` (coming soon)

## Contributing

Please see `CONTRIBUTING.md`. Before submitting a PR:

- Run tests: `pytest -q`
- Run linter: `ruff check .`
- Run type checker: `mypy .` (if enabled)

## Version

Current package version: `0.1.0`

## License

MIT
