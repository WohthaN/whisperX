#!/usr/bin/env python3
"""
Dictionary Manager CLI - Query and update Italian IPA dictionary stored in SQLite.
Batch-oriented utility for dictionary management operations.
"""

import argparse
import sqlite3
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


class DictionaryManager:
    """Manages Italian IPA dictionary operations."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize dictionary manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            current_dir = Path(__file__).resolve().parent
            default_db = current_dir / "assets" / "italian_dictionary.db"
            if not default_db.exists():
                # Try alternative path if assets directory doesn't exist
                alt_db = current_dir / "italian_dictionary.db"
                if alt_db.exists():
                    self.db_path = str(alt_db)
                else:
                    self.db_path = str(default_db)
            else:
                self.db_path = str(default_db)
        else:
            self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def lookup_word(self, word: str) -> Dict[str, Any]:
        """
        Look up exact word and return all pronunciations.
        
        Args:
            word: The word to look up
            
        Returns:
            Dictionary with word and pronunciations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT word, ipa_transcription, pronunciation_index FROM dictionary WHERE word = ? ORDER BY pronunciation_index',
                (word,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                return {"word": word, "found": False, "pronunciations": []}
            
            pronunciations = [
                {"index": row["pronunciation_index"], "ipa": row["ipa_transcription"]}
                for row in rows
            ]
            
            return {
                "word": word,
                "found": True,
                "pronunciations": pronunciations
            }
        finally:
            conn.close()
    
    def search_pattern(self, pattern: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for words matching SQL LIKE pattern.
        
        Args:
            pattern: SQL LIKE pattern (supports % and _ wildcards)
            limit: Maximum number of results
            
        Returns:
            List of matching words with pronunciations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if limit:
                cursor.execute(
                    'SELECT DISTINCT word FROM dictionary WHERE word LIKE ? COLLATE NOCASE ORDER BY word LIMIT ?',
                    (pattern, limit)
                )
            else:
                cursor.execute(
                    'SELECT DISTINCT word FROM dictionary WHERE word LIKE ? COLLATE NOCASE ORDER BY word',
                    (pattern,)
                )
            
            words = [row["word"] for row in cursor.fetchall()]
            
            results = []
            for word in words:
                cursor.execute(
                    'SELECT ipa_transcription, pronunciation_index FROM dictionary WHERE word = ? ORDER BY pronunciation_index',
                    (word,)
                )
                pronunciations = cursor.fetchall()
                results.append({
                    "word": word,
                    "pronunciations": [
                        {"index": p["pronunciation_index"], "ipa": p["ipa_transcription"]}
                        for p in pronunciations
                    ]
                })
            
            return results
        finally:
            conn.close()
    
    def search_pronunciation(self, pattern: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Find words containing specific IPA symbols/patterns.
        
        Args:
            pattern: SQL LIKE pattern for IPA transcription
            limit: Maximum number of results
            
        Returns:
            List of words with matching pronunciations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if limit:
                cursor.execute(
                    'SELECT word, ipa_transcription, pronunciation_index FROM dictionary WHERE ipa_transcription LIKE ? ORDER BY word LIMIT ?',
                    (pattern, limit)
                )
            else:
                cursor.execute(
                    'SELECT word, ipa_transcription, pronunciation_index FROM dictionary WHERE ipa_transcription LIKE ? ORDER BY word',
                    (pattern,)
                )
            
            rows = cursor.fetchall()
            
            results = {}
            for row in rows:
                word = row["word"]
                if word not in results:
                    results[word] = {
                        "word": word,
                        "pronunciations": []
                    }
                results[word]["pronunciations"].append({
                    "index": row["pronunciation_index"],
                    "ipa": row["ipa_transcription"]
                })
            
            return list(results.values())
        finally:
            conn.close()
    
    def list_words(self, filter_pattern: str = None, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all unique words in dictionary.
        
        Args:
            filter_pattern: Optional filter pattern
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of words with pronunciations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if filter_pattern:
                if limit:
                    cursor.execute(
                        'SELECT DISTINCT word FROM dictionary WHERE word LIKE ? COLLATE NOCASE ORDER BY word LIMIT ? OFFSET ?',
                        (filter_pattern, limit, offset)
                    )
                else:
                    cursor.execute(
                        'SELECT DISTINCT word FROM dictionary WHERE word LIKE ? COLLATE NOCASE ORDER BY word',
                        (filter_pattern,)
                    )
            else:
                if limit:
                    cursor.execute(
                        'SELECT DISTINCT word FROM dictionary ORDER BY word LIMIT ? OFFSET ?',
                        (limit, offset)
                    )
                else:
                    cursor.execute(
                        'SELECT DISTINCT word FROM dictionary ORDER BY word',
                        ()
                    )
            
            words = [row["word"] for row in cursor.fetchall()]
            
            results = []
            for word in words:
                cursor.execute(
                    'SELECT ipa_transcription, pronunciation_index FROM dictionary WHERE word = ? ORDER BY pronunciation_index',
                    (word,)
                )
                pronunciations = cursor.fetchall()
                results.append({
                    "word": word,
                    "pronunciations": [
                        {"index": p["pronunciation_index"], "ipa": p["ipa_transcription"]}
                        for p in pronunciations
                    ]
                })
            
            return results
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(DISTINCT word) FROM dictionary')
            unique_words = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM dictionary')
            total_pronunciations = cursor.fetchone()[0]
            
            db_file = Path(self.db_path)
            file_size = db_file.stat().st_size / (1024 * 1024) if db_file.exists() else 0
            
            return {
                "unique_words": unique_words,
                "total_pronunciations": total_pronunciations,
                "database_file": self.db_path,
                "file_size_mb": round(file_size, 2)
            }
        finally:
            conn.close()
    
    def add_word(self, word: str, pronunciations: List[str]) -> Dict[str, Any]:
        """
        Add new word with one or more pronunciations.
        
        Args:
            word: The word to add
            pronunciations: List of IPA transcriptions
            
        Returns:
            Result dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            for idx, ipa in enumerate(pronunciations):
                cursor.execute(
                    'INSERT INTO dictionary (word, ipa_transcription, pronunciation_index) VALUES (?, ?, ?)',
                    (word, ipa, idx)
                )
            
            conn.commit()
            return {
                "word": word,
                "added": True,
                "pronunciations": len(pronunciations)
            }
        except Exception as e:
            conn.rollback()
            return {
                "word": word,
                "added": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def modify_pronunciation(self, word: str, index: int, new_ipa: str) -> Dict[str, Any]:
        """
        Replace specific pronunciation of existing word.
        
        Args:
            word: The word to modify
            index: Pronunciation index to replace
            new_ipa: New IPA transcription
            
        Returns:
            Result dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'UPDATE dictionary SET ipa_transcription = ? WHERE word = ? AND pronunciation_index = ?',
                (new_ipa, word, index)
            )
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            return {
                "word": word,
                "index": index,
                "new_ipa": new_ipa,
                "modified": rows_affected > 0,
                "rows_affected": rows_affected
            }
        except Exception as e:
            conn.rollback()
            return {
                "word": word,
                "index": index,
                "modified": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def add_alternate(self, word: str, new_ipa: str) -> Dict[str, Any]:
        """
        Add new pronunciation as alternate for existing word.
        
        Args:
            word: The word to add alternate for
            new_ipa: New IPA transcription
            
        Returns:
            Result dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT MAX(pronunciation_index) FROM dictionary WHERE word = ?',
                (word,)
            )
            result = cursor.fetchone()
            max_index = result[0] if result and result[0] is not None else -1
            
            new_index = max_index + 1
            cursor.execute(
                'INSERT INTO dictionary (word, ipa_transcription, pronunciation_index) VALUES (?, ?, ?)',
                (word, new_ipa, new_index)
            )
            
            conn.commit()
            return {
                "word": word,
                "new_ipa": new_ipa,
                "added": True,
                "index": new_index
            }
        except Exception as e:
            conn.rollback()
            return {
                "word": word,
                "new_ipa": new_ipa,
                "added": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def delete_word(self, word: str, index: int = None) -> Dict[str, Any]:
        """
        Delete word or specific pronunciation.
        
        Args:
            word: The word to delete
            index: Optional pronunciation index (if None, delete all)
            
        Returns:
            Result dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if index is not None:
                cursor.execute(
                    'DELETE FROM dictionary WHERE word = ? AND pronunciation_index = ?',
                    (word, index)
                )
                action = f"deleted pronunciation {index}"
            else:
                cursor.execute('DELETE FROM dictionary WHERE word = ?', (word,))
                action = "deleted word"
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            return {
                "word": word,
                "index": index,
                "action": action,
                "deleted": rows_affected > 0,
                "rows_affected": rows_affected
            }
        except Exception as e:
            conn.rollback()
            return {
                "word": word,
                "index": index,
                "deleted": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def import_from_file(self, input_file: str, format: str = "json", replace: bool = False) -> Dict[str, Any]:
        """
        Bulk import from file.
        
        Args:
            input_file: Path to input file
            format: File format (json or csv)
            replace: If True, replace existing words
            
        Returns:
            Result dictionary with import statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if format == "json":
                with open(input_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                added = 0
                modified = 0
                errors = []
                
                for word, pronunciations in data.items():
                    try:
                        if replace:
                            cursor.execute('DELETE FROM dictionary WHERE word = ?', (word,))
                        
                        for idx, ipa in enumerate(pronunciations):
                            cursor.execute(
                                'INSERT INTO dictionary (word, ipa_transcription, pronunciation_index) VALUES (?, ?, ?)',
                                (word, ipa, idx)
                            )
                        added += len(pronunciations)
                    except Exception as e:
                        errors.append({"word": word, "error": str(e)})
                
            elif format == "csv":
                with open(input_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    
                    added = 0
                    modified = 0
                    errors = []
                    
                    for row in reader:
                        word = row.get('word', '')
                        ipa = row.get('ipa_transcription', '')
                        index_str = row.get('pronunciation_index', '0')
                        
                        try:
                            index = int(index_str)
                            
                            if replace:
                                cursor.execute('DELETE FROM dictionary WHERE word = ? AND pronunciation_index = ?', (word, index))
                                modified += 1
                            
                            cursor.execute(
                                'INSERT INTO dictionary (word, ipa_transcription, pronunciation_index) VALUES (?, ?, ?)',
                                (word, ipa, index)
                            )
                            added += 1
                        except Exception as e:
                            errors.append({"word": word, "error": str(e)})
            
            conn.commit()
            
            return {
                "input_file": input_file,
                "format": format,
                "replace": replace,
                "added": added,
                "modified": modified,
                "errors": len(errors),
                "error_details": errors[:10] if errors else []
            }
        except Exception as e:
            conn.rollback()
            return {
                "input_file": input_file,
                "imported": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def export_dictionary(self, output_file: str, format: str = "json", filter_pattern: str = None) -> Dict[str, Any]:
        """
        Export dictionary to file.
        
        Args:
            output_file: Path to output file
            format: Output format (json, csv, or sql)
            filter_pattern: Optional filter pattern
            
        Returns:
            Result dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if filter_pattern:
                cursor.execute(
                    'SELECT word, ipa_transcription, pronunciation_index FROM dictionary WHERE word LIKE ? COLLATE NOCASE ORDER BY word, pronunciation_index',
                    (filter_pattern,)
                )
            else:
                cursor.execute(
                    'SELECT word, ipa_transcription, pronunciation_index FROM dictionary ORDER BY word, pronunciation_index'
                )
            
            rows = cursor.fetchall()
            
            if format == "json":
                output_data = {}
                for row in rows:
                    word = row["word"]
                    ipa = row["ipa_transcription"]
                    if word not in output_data:
                        output_data[word] = []
                    output_data[word].append(ipa)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            elif format == "csv":
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['word', 'ipa_transcription', 'pronunciation_index'])
                    for row in rows:
                        writer.writerow([row["word"], row["ipa_transcription"], row["pronunciation_index"]])
            
            elif format == "sql":
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("-- Dictionary Export\n")
                    f.write("-- Generated by dictionary_manager.py\n\n")
                    for row in rows:
                        escaped_word = row["word"].replace("'", "''")
                        escaped_ipa = row["ipa_transcription"].replace("'", "''")
                        f.write(f"INSERT INTO dictionary (word, ipa_transcription, pronunciation_index) VALUES ('{escaped_word}', '{escaped_ipa}', {row['pronunciation_index']});\n")
            
            exported_words = len(set(row["word"] for row in rows))
            
            return {
                "output_file": output_file,
                "format": format,
                "filter": filter_pattern,
                "exported_words": exported_words,
                "total_rows": len(rows),
                "exported": True
            }
        except Exception as e:
            return {
                "output_file": output_file,
                "exported": False,
                "error": str(e)
            }
        finally:
            conn.close()


def format_output_pretty(result: Any, show_all: bool = False) -> str:
    """Format result as human-readable text."""
    if isinstance(result, dict):
        if "found" in result:
            word = result["word"]
            if not result["found"]:
                return f"'{word}': Not found in dictionary"
            
            output = [f"{word}:"]
            for p in result["pronunciations"]:
                output.append(f"  [{p['index']}] {p['ipa']}")
            return "\n".join(output)
        
        elif "word" in result and "added" in result:
            word = result["word"]
            if result["added"]:
                count = result.get("pronunciations", 1)
                return f"Added '{word}' with {count} pronunciation(s)"
            else:
                error = result.get("error", "Unknown error")
                return f"Failed to add '{word}': {error}"
        
        elif "word" in result and "modified" in result:
            word = result["word"]
            if result["modified"]:
                return f"Modified {word}[{result['index']}] to {result['new_ipa']}"
            else:
                error = result.get("error", "No matching pronunciation found")
                return f"Failed to modify {word}[{result['index']}]: {error}"
        
        elif "word" in result and "deleted" in result:
            word = result["word"]
            if result["deleted"]:
                if "index" in result and result["index"] is not None:
                    return f"Deleted {word}[{result['index']}]"
                else:
                    count = result.get("rows_affected", 0)
                    return f"Deleted '{word}' ({count} pronunciation(s))"
            else:
                error = result.get("error", "Unknown error")
                return f"Failed to delete '{word}': {error}"
        
        elif "unique_words" in result:
            lines = [
                "Database Statistics:",
                f"  Unique words: {result['unique_words']:,}",
                f"  Total pronunciations: {result['total_pronunciations']:,}",
                f"  Database file: {result['database_file']}",
                f"  File size: {result['file_size_mb']} MB"
            ]
            return "\n".join(lines)
        
        elif "imported" in result:
            if result.get("imported", True):
                lines = [
                    f"Importing from {result['input_file']}...",
                    f"  Format: {result['format']}",
                    f"  Added: {result['added']} entries",
                    f"  Modified: {result.get('modified', 0)} entries"
                ]
                if result.get("errors", 0) > 0:
                    lines.append(f"  Errors: {result['errors']}")
                    lines.append("  First 10 errors:")
                    for err in result.get("error_details", []):
                        lines.append(f"    - {err['word']}: {err['error']}")
                lines.append("Done.")
                return "\n".join(lines)
            else:
                return f"Failed to import: {result.get('error', 'Unknown error')}"
        
        elif "exported" in result:
            if result["exported"]:
                return f"Exported {result['exported_words']:,} words to {result['output_file']}"
            else:
                return f"Failed to export: {result.get('error', 'Unknown error')}"
        
        elif "new_ipa" in result and result.get("added"):
            word = result["word"]
            return f"Added alternate pronunciation for {word}: {result['new_ipa']}"
    
    elif isinstance(result, list):
        if not result:
            return "No results found"
        
        output = []
        for item in result:
            word = item["word"]
            pronunciations = ", ".join([p['ipa'] for p in item['pronunciations']])
            output.append(f"  {word}: {pronunciations}")
        
        return "\n".join(output)
    
    return str(result)


def format_output_json(result: Any) -> str:
    """Format result as JSON."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Dictionary Manager - Query and update Italian IPA dictionary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Look up a word
  python3 dictionary_manager.py lookup casa
  
  # Pattern search
  python3 dictionary_manager.py pattern "ca%" --limit 5
  
  # Find words with specific IPA
  python3 dictionary_manager.py pronunciation "%k%"
  
  # Add new word
  python3 dictionary_manager.py add newword "niːwɔd" "njuːwɜːd"
  
  # Modify pronunciation
  python3 dictionary_manager.py modify casa 1 "kaːsa"
  
  # Export dictionary
  python3 dictionary_manager.py export backup.json
  
  # Get statistics
  python3 dictionary_manager.py stats
        """
    )
    
    parser.add_argument("--db", type=str, default=None, help="Path to database file")
    parser.add_argument("--output_format", type=str, choices=["json", "pretty"], default="pretty", help="Output format (for query commands)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Query commands
    lookup_parser = subparsers.add_parser("lookup", help="Look up exact word")
    lookup_parser.add_argument("word", type=str, help="Word to look up")
    
    pattern_parser = subparsers.add_parser("pattern", help="Search for words matching pattern")
    pattern_parser.add_argument("pattern", type=str, help="SQL LIKE pattern (% for wildcards)")
    pattern_parser.add_argument("--limit", type=int, default=None, help="Maximum results")
    
    pronunciation_parser = subparsers.add_parser("pronunciation", help="Find words by IPA symbols")
    pronunciation_parser.add_argument("pattern", type=str, help="SQL LIKE pattern for IPA")
    pronunciation_parser.add_argument("--limit", type=int, default=None, help="Maximum results")
    
    list_parser = subparsers.add_parser("list", help="List all words")
    list_parser.add_argument("--filter", type=str, default=None, help="Filter pattern")
    list_parser.add_argument("--limit", type=int, default=None, help="Maximum results")
    list_parser.add_argument("--offset", type=int, default=0, help="Skip N results")
    
    export_parser = subparsers.add_parser("export", help="Export dictionary to file")
    export_parser.add_argument("output_file", type=str, help="Output file path")
    export_parser.add_argument("--format", type=str, choices=["json", "csv", "sql"], default="json", help="Export format")
    export_parser.add_argument("--filter", type=str, default=None, help="Filter pattern")
    
    # Update commands
    add_parser = subparsers.add_parser("add", help="Add new word")
    add_parser.add_argument("word", type=str, help="Word to add")
    add_parser.add_argument("pronunciations", type=str, nargs="+", help="IPA transcriptions (one or more)")
    
    modify_parser = subparsers.add_parser("modify", help="Modify pronunciation")
    modify_parser.add_argument("word", type=str, help="Word to modify")
    modify_parser.add_argument("index", type=int, help="Pronunciation index")
    modify_parser.add_argument("new_ipa", type=str, help="New IPA transcription")
    
    alternate_parser = subparsers.add_parser("alternate", help="Add alternate pronunciation")
    alternate_parser.add_argument("word", type=str, help="Word to add alternate for")
    alternate_parser.add_argument("new_ipa", type=str, help="New IPA transcription")
    
    delete_parser = subparsers.add_parser("delete", help="Delete word or pronunciation")
    delete_parser.add_argument("word", type=str, help="Word to delete")
    delete_parser.add_argument("--index", type=int, default=None, help="Delete specific pronunciation index")
    
    import_parser = subparsers.add_parser("import", help="Bulk import from file")
    import_parser.add_argument("input_file", type=str, help="Input file path")
    import_parser.add_argument("--format", type=str, choices=["json", "csv"], default="json", help="File format")
    import_parser.add_argument("--replace", action="store_true", help="Replace existing words")
    
    # Utility commands
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    manager = DictionaryManager(args.db)
    
    try:
        result = None
        
        if args.command == "lookup":
            result = manager.lookup_word(args.word)
        
        elif args.command == "pattern":
            result = manager.search_pattern(args.pattern, args.limit)
        
        elif args.command == "pronunciation":
            result = manager.search_pronunciation(args.pattern, args.limit)
        
        elif args.command == "list":
            result = manager.list_words(args.filter, args.limit, args.offset)
        
        elif args.command == "export":
            result = manager.export_dictionary(args.output_file, args.format, args.filter)
        
        elif args.command == "add":
            result = manager.add_word(args.word, args.pronunciations)
        
        elif args.command == "modify":
            result = manager.modify_pronunciation(args.word, args.index, args.new_ipa)
        
        elif args.command == "alternate":
            result = manager.add_alternate(args.word, args.new_ipa)
        
        elif args.command == "delete":
            result = manager.delete_word(args.word, args.index)
        
        elif args.command == "import":
            result = manager.import_from_file(args.input_file, args.format, args.replace)
        
        elif args.command == "stats":
            result = manager.get_stats()
        
        # Format and output result
        if result is not None:
            if args.output_format == "json":
                print(format_output_json(result))
            else:
                print(format_output_pretty(result))
        
        sys.exit(0)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
