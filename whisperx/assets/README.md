https://github.com/DanielSWolf/wiki-pronunciation-dict/

## Italian IPA Dictionary

The Italian IPA pronunciation dictionary is stored in `italian_dictionary.db` (SQLite database).

### Database Schema

```sql
-- Metadata table
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY,
    language TEXT NOT NULL,
    language_name TEXT NOT NULL,
    graphemes TEXT,  -- JSON array
    phonemes TEXT,   -- JSON array
    grapheme_distribution TEXT,  -- JSON object
    phoneme_distribution TEXT    -- JSON object
);

-- Dictionary table - one row per pronunciation
CREATE TABLE dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    ipa_transcription TEXT NOT NULL,
    pronunciation_index INTEGER NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_dictionary_word ON dictionary(word);
CREATE INDEX idx_dictionary_word_normalized ON dictionary(word COLLATE NOCASE);
```

### Statistics
- **Unique words**: 91,307
- **Pronunciation entries**: 97,421
- **Database size**: ~6.9 MB (compared to ~20 MB for original JSON files)
- **Space savings**: ~65%

### Usage

The dictionary is automatically loaded by `ItalianDictionary` class in `ipa_converter.py`:

```python
from whisperx.ipa_converter import ItalianDictionary

dict_obj = ItalianDictionary()
pronunciations = dict_obj.lookup_word("casa")
# Returns: ['kasa', 'kaza']
```

### Migration

To rebuild the database from scratch (if you have the original JSON files):

```bash
python3 migrate_ipa_to_sqlite.py --verbose
```

The migration script will create `italian_dictionary.db` from all `it_part_*.json` files and `it-metadata.json`.
