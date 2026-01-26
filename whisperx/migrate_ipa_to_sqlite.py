#!/usr/bin/env python3
"""
Migration script to convert Italian IPA dictionary from JSON to SQLite.
Creates italian_dictionary.db from all it_part_*.json and it-metadata.json files.
"""

import sqlite3
import json
import glob
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def create_database_schema(conn: sqlite3.Connection):
    """Create the database schema."""
    cursor = conn.cursor()
    
    # Metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY,
            language TEXT NOT NULL,
            language_name TEXT NOT NULL,
            graphemes TEXT,
            phonemes TEXT,
            grapheme_distribution TEXT,
            phoneme_distribution TEXT
        )
    ''')
    
    # Dictionary table - one row per pronunciation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            ipa_transcription TEXT NOT NULL,
            pronunciation_index INTEGER NOT NULL
        )
    ''')
    
    # Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dictionary_word ON dictionary(word)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dictionary_word_normalized ON dictionary(word COLLATE NOCASE)')
    
    conn.commit()


def load_metadata(metadata_file: Path) -> Dict:
    """Load metadata from JSON file."""
    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def insert_metadata(conn: sqlite3.Connection, metadata: Dict):
    """Insert metadata into database."""
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO metadata (
            language, language_name, graphemes, phonemes,
            grapheme_distribution, phoneme_distribution
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        metadata['language'],
        metadata['languageName'],
        json.dumps(metadata['graphemes']),
        json.dumps(metadata['phonemes']),
        json.dumps(metadata['graphemeDistribution']),
        json.dumps(metadata['phonemeDistribution'])
    ))
    
    conn.commit()
    logger.info(f"Inserted metadata for {metadata['languageName']}")


def load_and_insert_part_files(conn: sqlite3.Connection, assets_dir: Path):
    """Load all part JSON files and insert into database."""
    part_files = sorted(glob.glob(str(assets_dir / "it_part_*.json")))
    
    if not part_files:
        raise FileNotFoundError(f"No it_part_*.json files found in {assets_dir}")
    
    cursor = conn.cursor()
    total_words = 0
    
    for part_file in part_files:
        with open(part_file, 'r', encoding='utf-8') as f:
            part_dict = json.load(f)
        
        # Insert each pronunciation as a separate row
        for word, pronunciations in part_dict.items():
            for idx, ipa_transcription in enumerate(pronunciations):
                cursor.execute('''
                    INSERT INTO dictionary (word, ipa_transcription, pronunciation_index)
                    VALUES (?, ?, ?)
                ''', (word, ipa_transcription, idx))
        
        total_words += len(part_dict)
        logger.debug(f"Loaded {len(part_dict)} words from {Path(part_file).name}")
    
    conn.commit()
    logger.info(f"Loaded {total_words:,} total words from {len(part_files)} part files")
    
    return total_words


def verify_database(conn: sqlite3.Connection):
    """Verify the database was created correctly."""
    cursor = conn.cursor()
    
    # Check metadata
    cursor.execute('SELECT COUNT(*) FROM metadata')
    metadata_count = cursor.fetchone()[0]
    logger.info(f"Database contains {metadata_count} metadata entries")
    
    # Check dictionary entries
    cursor.execute('SELECT COUNT(*) FROM dictionary')
    dict_count = cursor.fetchone()[0]
    logger.info(f"Database contains {dict_count:,} pronunciation entries")
    
    # Check unique words
    cursor.execute('SELECT COUNT(DISTINCT word) FROM dictionary')
    unique_words = cursor.fetchone()[0]
    logger.info(f"Database contains {unique_words:,} unique words")
    
    # Sample query
    cursor.execute('SELECT word, ipa_transcription FROM dictionary LIMIT 5')
    logger.info("Sample entries:")
    for row in cursor.fetchall():
        logger.info(f"  '{row[0]}': {row[1]}")


def migrate_to_sqlite(assets_dir: str = None, output_db: str = None):
    """
    Migrate Italian IPA dictionary from JSON to SQLite.
    
    Args:
        assets_dir: Path to assets directory containing JSON files
        output_db: Path for output SQLite database file
    """
    # Determine paths
    if assets_dir is None:
        current_dir = Path(__file__).parent
        assets_dir = current_dir / "assets"
    else:
        assets_dir = Path(assets_dir)
    
    if output_db is None:
        output_db = assets_dir / "italian_dictionary.db"
    else:
        output_db = Path(output_db)
    
    logger.info(f"Migrating from {assets_dir} to {output_db}")
    
    # Remove existing database if it exists
    if output_db.exists():
        logger.info(f"Removing existing database at {output_db}")
        output_db.unlink()
    
    # Create database connection
    conn = sqlite3.connect(output_db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    
    try:
        # Create schema
        logger.info("Creating database schema...")
        create_database_schema(conn)
        
        # Load and insert metadata
        metadata_file = assets_dir / "it-metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        logger.info(f"Loading metadata from {metadata_file}...")
        metadata = load_metadata(metadata_file)
        insert_metadata(conn, metadata)
        
        # Load and insert part files
        logger.info("Loading and inserting dictionary data...")
        total_words = load_and_insert_part_files(conn, assets_dir)
        
        # Verify database
        logger.info("Verifying database...")
        verify_database(conn)
        
        # Optimize database
        cursor = conn.cursor()
        cursor.execute('ANALYZE')
        conn.commit()
        logger.info("Database optimized with ANALYZE")
        
        # Get final database size
        db_size = output_db.stat().st_size / (1024 * 1024)
        logger.info(f"Migration complete! Database size: {db_size:.2f} MB")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        if output_db.exists():
            output_db.unlink()
        raise
    finally:
        conn.close()
    
    return output_db


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate Italian IPA dictionary from JSON to SQLite"
    )
    parser.add_argument(
        "--assets-dir",
        type=str,
        default=None,
        help="Path to assets directory containing JSON files"
    )
    parser.add_argument(
        "--output-db",
        type=str,
        default=None,
        help="Path for output SQLite database file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    try:
        db_path = migrate_to_sqlite(args.assets_dir, args.output_db)
        print(f"\n✓ Migration successful! Database created at: {db_path}")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        exit(1)
