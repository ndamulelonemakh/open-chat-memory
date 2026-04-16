# Open Chat Memory Documentation

## Quick Start

Install and run in 3 steps:

```bash
# Install
pip install openchatmemory[db,mem0]

# Configure (see Environment Setup guide)
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Parse your chat export
ocmem parse --provider chatgpt --input conversations.json --out messages.jsonl

# Load to database
ocmem db load --input messages.jsonl --db-url postgresql://localhost/chatdb
```

## Documentation Guides

- **[Environment Setup](environment-setup.md)** - Complete configuration guide with deployment scenarios
- **[CLI Usage](cli.md)** - Command-line interface reference
- **[Analysis Tools](analysis-tools-index.md)** - Data analysis examples
- **[Adding Parsers](adding-parsers.md)** - Extend with new providers

## Supported Providers

| Provider | Status | Export Format |
|----------|--------|---------------|
| ChatGPT  | ✅ Supported | JSON |
| Claude   | ✅ Supported | JSON |
| Grok     | 🚧 Planned | - |

## Architecture

```
openchatmemory/
├── schemas/      # Shared data models (MessageModel)
├── parsers/      # Provider-specific parsers
├── persistence/  # Database loaders
├── memory/       # Memory store integrations
└── cli.py        # Command-line interface
```

## API Reference

See inline docstrings for detailed API documentation:

```python
from openchatmemory.parsers import ChatGPTParser
from openchatmemory.schemas import MessageModel

# Parse programmatically
parser = ChatGPTParser()
messages = parser.parse(Path("conversations.json"))
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - see [LICENSE](../LICENSE)
