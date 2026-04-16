# Adding a New Parser

To add support for a new chat provider:

## 1. Create Parser Class

```python
# openchatmemory/parsers/newprovider.py
from pathlib import Path
from typing import List
import pandas as pd
from loguru import logger

from ..schemas import MessageModel
from .base import BaseParser, ParserRegistry

class NewProviderParser(BaseParser):
    provider = "newprovider"
    
    def parse(self, input_path: Path) -> List[MessageModel]:
        """Parse NewProvider export format."""
        # Load the export
        df = pd.read_json(str(input_path))
        records = []
        
        # Transform to MessageModel
        for _, row in df.iterrows():
            model = MessageModel(
                message_id=row["id"],
                conversation_id=row["conv_id"],
                role=row["role"],
                content=row["text"],
                message_create_time=row["timestamp"],
                title=row.get("title", ""),
            )
            records.append(model)
        
        return records

# Register the parser
ParserRegistry.register(NewProviderParser.provider, NewProviderParser)
```

## 2. Export in __init__.py

```python
# openchatmemory/parsers/__init__.py
from .newprovider import NewProviderParser

__all__ = [..., "NewProviderParser"]
```

## 3. Add Tests

```python
# tests/test_newprovider_parser.py
from openchatmemory.parsers import NewProviderParser

def test_newprovider_basic():
    parser = NewProviderParser()
    messages = parser.parse(Path("tests/fixtures/newprovider.json"))
    assert len(messages) > 0
```

## 4. Update Documentation

Add to [Index.md](Index.md) supported providers table.

That's it! The CLI automatically discovers registered parsers.
