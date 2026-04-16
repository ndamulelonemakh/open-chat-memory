# Environment Configuration Guide

Complete guide to configuring Open Chat Memory for different deployment scenarios.

## Quick Setup

1. **Copy template:**
   ```bash
   cp .env.example .env
   ```

2. **Set API key:**
   ```bash
   echo "OPENAI_API_KEY=sk-proj-your-key-here" >> .env
   ```

3. **Verify setup:**
   ```bash
   ocmem diagnose
   ```

## Configuration Scenarios

### Scenario 1: Local Development (Minimal)

Use local file-based storage, no external services needed:

```bash
# .env
OPENAI_API_KEY=sk-proj-...
```

This setup:
- ✅ Stores vectors locally in `./data/qdrant_data`
- ✅ No Docker required
- ✅ Fastest startup
- ❌ No graph features (Neo4j)

### Scenario 2: Docker-Based Local (Recommended)

Run Qdrant and Neo4j via Docker for full features:

```bash
# Start services
docker run -d --name qdrant -p 6333:6333 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant

docker run -d --name neo4j -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/devpassword \
  neo4j:latest

# .env
OPENAI_API_KEY=sk-proj-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URL=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=devpassword
NEO4J_DATABASE=mem0
```

This setup:
- ✅ Full graph relationship features
- ✅ Production-like environment
- ✅ Persistent data storage
- ✅ Easy cleanup (`docker rm -f qdrant neo4j`)

### Scenario 3: Remote/Production Services

Connect to managed cloud services:

```bash
# .env
OPENAI_API_KEY=sk-proj-...

# Qdrant Cloud
QDRANT_URL=https://your-cluster.qdrant.io:443
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION=prod_openchatmemory

# Neo4j Aura
NEO4J_URL=neo4j+s://xxxxx.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secure-password
NEO4J_DATABASE=neo4j

# Managed PostgreSQL
DATABASE_URL=postgresql://user:pass@db.example.com:5432/chatdb
```

This setup:
- ✅ Scalable to large datasets
- ✅ High availability
- ✅ Managed backups
- ❌ Additional cost

## Variable Reference

### Required Variables

| Variable | Required For | Where to Get |
|----------|-------------|--------------|
| `OPENAI_API_KEY` | `mem push` command | [OpenAI Platform](https://platform.openai.com/api-keys) |

### Optional - LLM Configuration

| Variable | Default | Options |
|----------|---------|---------|
| `MEMORY_LLM_MODEL` | `gpt-5-nano` | `gpt-5-nano`, `gpt-5-mini`, `gpt-5`, `gpt-4o-mini`, `gpt-4o` |
| `MEMORY_EMBED_MODEL` | `all-MiniLM-L6-v2` | Any HuggingFace sentence-transformers model |

**Model Selection Guide:**
- **gpt-5-nano**: Fastest, cheapest ($0.05/1M tokens)
- **gpt-5-mini**: Balanced performance/cost
- **gpt-4o-mini**: Older, still capable
- **gpt-5**: Most capable, expensive

### Optional - Qdrant Vector Store

**For local file storage (default):**
Leave these empty. Data stored in `./data/qdrant_data`.

**For remote Qdrant:**

| Variable | Description | Example |
|----------|-------------|---------|
| `QDRANT_URL` | Full URL to Qdrant instance | `https://cluster.qdrant.io:443` |
| `QDRANT_HOST` | Hostname only | `cluster.qdrant.io` |
| `QDRANT_PORT` | Port number | `6333` or `443` |
| `QDRANT_API_KEY` | API key for authentication | `your-api-key` |
| `QDRANT_COLLECTION` | Collection name | `openchatmemory` |

**Important:** If `QDRANT_URL` is set, local file storage is disabled.

### Optional - Neo4j Graph Store

**When to use:**
- Want to explore conversation relationships
- Need graph-based memory queries
- Building knowledge graphs from chats

**Variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `NEO4J_URL` | Connection URL (scheme matters!) | `neo4j://localhost:7687` (local)<br>`neo4j+s://xxx.neo4j.io:7687` (Aura) |
| `NEO4J_USERNAME` | Username | `neo4j` |
| `NEO4J_PASSWORD` | Password | Required to enable graph store |
| `NEO4J_DATABASE` | Database name | `mem0` or `neo4j` |

**Important:** If `NEO4J_URL` is not set, graph features are disabled (optional feature).

### Optional - PostgreSQL

Only needed for `ocmem db load` command:

| Variable | Description | Format |
|----------|-------------|--------|
| `DATABASE_URL` | Full connection string | `postgresql://user:pass@host:port/db` |

## Verification

After configuration, verify your setup:

```bash
# Check environment & dependencies
ocmem diagnose

# Output shows:
# - Python version
# - Package version
# - Available optional dependencies
```

Example output:
```json
{
  "python": "3.12.11",
  "platform": "macOS-14.0-arm64",
  "package_version": "0.1.0",
  "schema_version": "0.1.0",
  "optional": {
    "mem0": true,
    "psycopg": true,
    "sqlalchemy": true,
    "pandas": true
  }
}
```

## Troubleshooting

### "mem0ai is not installed"
```bash
pip install -e .[mem0]
```

### "Connection refused" to Qdrant
```bash
# Check if running:
docker ps | grep qdrant

# Start if needed:
docker run -d -p 6333:6333 qdrant/qdrant
```

### "Failed to connect" to Neo4j
```bash
# Check if running:
docker ps | grep neo4j

# Check credentials:
# Default: neo4j/neo4j (must change on first login)

# Verify connection:
docker logs neo4j | grep "Started"
```

### "Cannot convert None to int" error
Ensure `QDRANT_PORT` is set if using `QDRANT_HOST`:
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333  # Must be set together
```

## Security Best Practices

1. **Never commit `.env` to git**
   - Already in `.gitignore`, but double-check

2. **Use strong passwords**
   - Especially for production Neo4j instances

3. **Rotate API keys regularly**
   - OpenAI keys can be rotated at platform.openai.com

4. **Restrict database access**
   - Use read-only credentials when possible
   - Limit network access via firewall rules

5. **Audit exported data**
   - Review JSONL files before sharing
   - Redaction features coming in future releases

## Next Steps

- [CLI Usage Guide](cli.md)
- [Analysis Examples](analysis-tools-index.md)
- [Adding Custom Parsers](adding-parsers.md)
