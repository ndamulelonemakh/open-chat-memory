# CLI Usage

## Commands

### parse
Convert chat exports to normalized JSONL format.

```bash
ocmem parse --provider PROVIDER --input PATH --out OUTPUT.jsonl
```

**Options:**
- `--provider`: `chatgpt` or `claude`
- `--input`: Path to `conversations.json`, directory containing it, or `.zip` export
- `--out`: Output JSONL path

**Examples:**
```bash
# Direct conversations.json file
ocmem parse --provider chatgpt \
  --input data/raw/conversations.json \
  --out data/processed/messages.jsonl

# Directory containing conversations.json (e.g., auto-extracted on macOS)
ocmem parse --provider chatgpt \
  --input data/raw/my-export/ \
  --out data/processed/messages.jsonl

# Zip export (will extract and find conversations.json)
ocmem parse --provider chatgpt \
  --input downloads/chatgpt-export.zip \
  --out data/processed/messages.jsonl
```

---

### db load
Load messages into PostgreSQL.

```bash
ocmem db load --input FILE.jsonl --db-url URL [--provider PROVIDER]
```

**Options:**
- `--input`: JSONL file from parse
- `--db-url`: PostgreSQL connection string
- `--provider`: Provider name (default: chatgpt)

**Example:**
```bash
export DATABASE_URL="postgresql://user:pass@localhost/chatdb"
ocmem db load --input messages.jsonl --db-url $DATABASE_URL
```

**Schema:**
- `chats.chat_headings`: Conversation metadata
- `chats.messages`: Individual messages

---

### mem push
Push conversations to Mem0 memory store.

```bash
ocmem mem push --input FILE.jsonl --user-id ID [--provider PROVIDER]
```

**Options:**
- `--input`: JSONL file from parse
- `--user-id`: User identifier for memory association
- `--provider`: Provider name (default: chatgpt)

**Example:**
```bash
ocmem mem push --input messages.jsonl --user-id user_123
```

---

## Environment Variables

```bash
# Database connection
export DATABASE_URL="postgresql://localhost/chatdb"

# Mem0 configuration (optional)
export MEM0_API_KEY="your-key"
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Missing dependency (e.g., mem0ai not installed)
