"""
Italian IPA Converter for WhisperX
Converts Italian orthographic phoneme groups to IPA symbols with linguistic weights
"""

from typing import Dict, List, Tuple, Optional
import re
import json
import os
import sqlite3
from pathlib import Path
from whisperx.log_utils import get_logger

logger = get_logger(__name__)


class ItalianDictionary:
    """
    Manages Italian pronunciation dictionary for IPA transcription.
    Loads from SQLite database and provides lookup functionality.
    """
    
    def __init__(self, assets_dir: Optional[str] = None):
        """
        Initialize Italian dictionary.
        
        Args:
            assets_dir: Path to assets directory containing dictionary files
        """
        if assets_dir is None:
            # Default assets directory relative to this file
            current_dir = Path(__file__).parent
            self.assets_dir = current_dir / "assets"
        else:
            self.assets_dir = Path(assets_dir)
        
        self.conn = None
        self.is_loaded_flag = False
        
        self._load_dictionary()
    
    def _load_dictionary(self):
        """Load Italian pronunciation dictionary from SQLite database."""
        db_path = self.assets_dir / "italian_dictionary.db"
        
        try:
            if not db_path.exists():
                logger.warning(f"SQLite database not found at {db_path}")
                self.is_loaded_flag = False
                return
            
            # Open database connection
            self.conn = sqlite3.connect(str(db_path))
            self.conn.row_factory = sqlite3.Row
            
            # Verify database has expected tables
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'dictionary' not in tables:
                logger.error(f"Database at {db_path} missing 'dictionary' table")
                self.conn.close()
                self.conn = None
                self.is_loaded_flag = False
                return
            
            # Get dictionary stats
            cursor.execute('SELECT COUNT(DISTINCT word) FROM dictionary')
            unique_words = cursor.fetchone()[0]
            
            self.is_loaded_flag = True
            logger.info(f"Loaded Italian dictionary from SQLite: {unique_words:,} unique words")
            
        except Exception as e:
            logger.error(f"Failed to load Italian dictionary from SQLite: {e}")
            if self.conn:
                self.conn.close()
                self.conn = None
            self.is_loaded_flag = False
    
    def lookup_word(self, word: str) -> List[str]:
        """
        Look up IPA transcriptions for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            List of IPA transcriptions (empty if not found)
        """
        if not self.is_loaded_flag or not self.conn:
            return []
        
        cursor = self.conn.cursor()
        
        # Try exact match first
        cursor.execute(
            'SELECT ipa_transcription FROM dictionary WHERE word = ? ORDER BY pronunciation_index',
            (word,)
        )
        exact_results = [row[0] for row in cursor.fetchall()]
        
        if exact_results:
            return exact_results
        
        # Try case-insensitive match
        cursor.execute(
            'SELECT ipa_transcription FROM dictionary WHERE word = ? COLLATE NOCASE ORDER BY word, pronunciation_index',
            (word,)
        )
        caseless_results = [row[0] for row in cursor.fetchall()]
        
        if caseless_results:
            return caseless_results
        
        # Try normalized match (remove accents)
        normalized_word = self._normalize_word(word)
        if normalized_word != word:
            cursor.execute(
                'SELECT ipa_transcription FROM dictionary WHERE word = ? COLLATE NOCASE ORDER BY pronunciation_index',
                (normalized_word,)
            )
            normalized_results = [row[0] for row in cursor.fetchall()]
            
            if normalized_results:
                return normalized_results
        
        return []
    
    def _normalize_word(self, word: str) -> str:
        """
        Normalize word by removing common accents and diacritics.
        
        Args:
            word: Word to normalize
            
        Returns:
            Normalized word
        """
        # Basic normalization - can be expanded as needed
        replacements = {
            'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
            'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
            'À': 'A', 'Á': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A',
            'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
            'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O',
            'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U'
        }
        
        normalized = word
        for accented, plain in replacements.items():
            normalized = normalized.replace(accented, plain)
        
        return normalized
    
    def is_loaded(self) -> bool:
        """Check if dictionary is successfully loaded."""
        return self.is_loaded_flag
    
    def get_dictionary_size(self) -> int:
        """Get the number of unique words in the dictionary."""
        if not self.is_loaded_flag or not self.conn:
            return 0
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT word) FROM dictionary')
        return cursor.fetchone()[0]
    
    def __del__(self):
        """Close database connection when object is destroyed."""
        if self.conn:
            self.conn.close()


class ItalianIPAConverter:
    """
    Converts Italian orthographic characters to IPA symbols with context-aware rules
    and assigns linguistic weights based on phonological characteristics.
    Uses dictionary-first approach with rule-based fallback.
    """
    
    def __init__(self, dictionary: Optional[ItalianDictionary] = None):
        """
        Initialize Italian IPA converter.
        
        Args:
            dictionary: ItalianDictionary instance for pronunciation lookup
        """
        # Initialize dictionary if not provided
        if dictionary is None:
            self.dictionary = ItalianDictionary()
        else:
            self.dictionary = dictionary
        # IPA weights from user's schema (using standard IPA symbols)
        self.ipa_weights = {
            'ˈ': 1.0,  # Primary stress mark
            'ˌ': 0.95,  # Secondary stress mark
            'tʃ': 0.9,  # C morbida (es. cena)
            'k': 0.9,  # C dura (es. cane)
            'ʎ': 1.0,  # GLI (es. moglie)
            'r': 0.8,  # R (vibrante)
            'z': 0.8,  # S sonora (es. casa)
            's': 0.9,  # S silente (es. sole)
            't': 0.7,  # T
            'ɲ': 0.9,  # GN (es. gnomo)
            'dz': 0.8, # Z sonora (es. zero)
            'ts': 0.8, # Z silente (es. pazzo)
            'dʒ': 0.9, # g gente
            'ʃ': 0.8, # Sc scena
            'j': 0.6, # j di iena
            'e': 0.9, # e chiusa di vede
            'ɛ': 0.9, # e aperto di bello
            'ɔ': 0.9, # o aperta
            'o': 0.9, # o chiusa
            'a': 0.9, # a
            'i': 0.9, # i
            'u': 0.9, # u
            'DOPPIE': 1.0, # Le doppie
        }
        
        # Default weights for other phonemes
        self.default_weights = {
            'vowel': 0.85,
            'consonant': 0.8,
            'semivowel': 0.7
        }
        
        # Italian orthography to IPA mappings with context rules (standard IPA)
        self.consonant_mappings = {
            # C and G patterns
            'ci': 'tʃ', 'ce': 'tʃ',  # soft c before i,e
            'gi': 'dʒ', 'ge': 'dʒ',  # soft g before i,e
            'gli': 'ʎ',  # before i,e
            'gn': 'ɲ',
            'sc': 'ʃ',  # before i,e
            's': {'voiced': 'z', 'voiceless': 's'},
            'z': {'voiced': 'dz', 'voiceless': 'ts'}
        }
        
        # Vowel mappings with open/closed distinction
        self.vowel_mappings = {
            'e': {'closed': 'e', 'open': 'ɛ'},
            'o': {'closed': 'o', 'open': 'ɔ'}
        }
        
        # Geminated consonants (Le doppie)
        self.geminated_consonants = {
            'pp': 'p:', 'bb': 'b:', 'tt': 't:', 'dd': 'd:',
            'cc': 'k:', 'gg': 'g:', 'ff': 'f:', 'vv': 'v:',
            'mm': 'm:', 'nn': 'n:', 'll': 'l:', 'rr': 'r:',
            'ss': 's:', 'zz': 'z:'
        }
    
    def convert_orthographic_to_ipa(self, orthographic_phoneme: str, 
                                  position: int = 0, 
                                  word_context: str = "") -> Tuple[str, float]:
        """
        Convert orthographic phoneme to IPA symbol with appropriate weight.
        
        Args:
            orthographic_phoneme: The orthographic representation
            position: Position in word (0-based)
            word_context: Full word for context analysis
            
        Returns:
            Tuple of (IPA_symbol, linguistic_weight)
        """
        lower_phoneme = orthographic_phoneme.lower()
        
        # Handle geminated consonants (Le doppie) - check within word context
        if position < len(word_context) - 1:
            two_char = word_context[position:position+2].lower()
            if two_char in self.geminated_consonants:
                ipa = self.geminated_consonants[two_char]
                return ipa, self.ipa_weights['DOPPIE']
        
        # Check multi-character patterns first
        if position < len(word_context) - 1:
            two_char = word_context[position:position+2].lower()
            
            # C and G soft patterns
            if two_char in ['ci', 'ce']:
                return 'tʃ', self.ipa_weights['tʃ']
            elif two_char in ['gi', 'ge']:
                return 'dʒ', self.ipa_weights['dʒ']
            elif two_char == 'gli':
                return 'ʎ', self.ipa_weights['ʎ']
            elif two_char == 'gn':
                return 'ɲ', self.ipa_weights['ɲ']
            elif two_char == 'sc':
                # Check if followed by i or e
                if position < len(word_context) - 2:
                    next_char = word_context[position+2].lower()
                    if next_char in ['i', 'e']:
                        return 'ʃ', self.ipa_weights['ʃ']
        
        # Check for gli pattern (not just at start)
        if position < len(word_context) - 2:
            three_char = word_context[position:position+3].lower()
            if three_char == 'gli':
                return 'ʎ', self.ipa_weights['ʎ']
        
        # Handle s/z with context-dependent voicing
        if lower_phoneme == 's':
            sound_type = self._get_s_sound_type(position, word_context)
            ipa = self.consonant_mappings['s'][sound_type]
            return ipa, self.ipa_weights.get(ipa, 0.8)
            
        if lower_phoneme == 'z':
            sound_type = self._get_z_sound_type(position, word_context)
            ipa = self.consonant_mappings['z'][sound_type]
            return ipa, self.ipa_weights.get(ipa, 0.8)
        
        # Handle vowel quality
        if lower_phoneme in self.vowel_mappings:
            vowel_mapping = self.vowel_mappings[lower_phoneme]
            quality = self._determine_vowel_quality(lower_phoneme, word_context, position)
            ipa = vowel_mapping[quality]
            return ipa, self.ipa_weights.get(ipa, 0.9)
        
        # Handle i as glide (j) between vowels - check before individual vowel handling
        if lower_phoneme == 'i' and self._is_glide_context(position, word_context):
            return 'j', self.ipa_weights.get('j', 0.6)
        
        # Standard consonant mappings with context for c/g
        if lower_phoneme == 'c':
            # Check if soft (already handled above)
            if position < len(word_context) - 1:
                next_char = word_context[position+1].lower()
                if next_char not in ['i', 'e']:
                    return 'k', self.ipa_weights['k']
            else:
                return 'k', self.ipa_weights['k']
                
        elif lower_phoneme == 'g':
            # Check if soft (already handled above)
            if position < len(word_context) - 1:
                next_char = word_context[position+1].lower()
                if next_char not in ['i', 'e']:
                    return 'g', 0.8
            else:
                return 'g', 0.8
        
        # Standard consonant mappings
        consonant_map = {
            'q': 'k', 'r': 'r', 'l': 'l', 'm': 'm', 'n': 'n',
            'p': 'p', 'b': 'b', 't': 't', 'd': 'd',
            'f': 'f', 'v': 'v'
        }
        
        if lower_phoneme in consonant_map:
            ipa = consonant_map[lower_phoneme]
            # t gets standard IPA symbol and weight
            if lower_phoneme == 't':
                return 't', self.ipa_weights.get('t', 0.7)
            return ipa, self.ipa_weights.get(ipa, 0.8)
        
        # Default vowel handling
        if self._is_vowel(lower_phoneme):
            if lower_phoneme == 'i':
                return 'i', self.default_weights['vowel']
            elif lower_phoneme == 'u':
                return 'u', self.default_weights['vowel']
            elif lower_phoneme == 'a':
                return 'a', self.default_weights['vowel']
        
        # Fallback
        return orthographic_phoneme, 0.8
    
    def _get_s_sound_type(self, position: int, word_context: str) -> str:
        """Determine if 's' is voiced or voiceless based on context."""
        # Simple rule: s is voiced between vowels, at word start before voiced consonant
        if position > 0 and position < len(word_context) - 1:
            prev_char = word_context[position - 1].lower()
            next_char = word_context[position + 1].lower()
            if self._is_vowel(prev_char) and self._is_vowel(next_char):
                return 'voiced'
        
        # At word start
        if position == 0 and len(word_context) > 1:
            next_char = word_context[1].lower()
            if next_char in ['b', 'd', 'g', 'l', 'm', 'n', 'r', 'v', 'z']:
                return 'voiced'
        
        return 'voiceless'
    
    def _get_z_sound_type(self, position: int, word_context: str) -> str:
        """Determine if 'z' is voiced or voiceless based on context."""
        # In Italian: initial z is often voiced (dz), between vowels voiceless (ʦ)
        if position == 0:
            return 'voiced'  # zero -> dz
            
        # Between vowels tends to be voiceless
        if position > 0 and position < len(word_context) - 1:
            prev_char = word_context[position - 1].lower()
            next_char = word_context[position + 1].lower()
            if self._is_vowel(prev_char) and self._is_vowel(next_char):
                return 'voiceless'  # pazzo -> ʦ
        
        # Check if part of geminates - already handled above
        return 'voiceless'  # Default to voiceless for consistency
    
    def _determine_vowel_quality(self, vowel: str, word_context: str, position: int) -> str:
        """Determine if vowel is open or closed based on context."""
        # Simplified rules for Italian vowel quality
        if vowel == 'e':
            # Before consonant clusters tend to be closed
            if position < len(word_context) - 1:
                next_char = word_context[position + 1].lower()
                if next_char in ['r', 'l', 'n'] + list('bcdfghjklmnpqrstvwxyz'):
                    return 'closed'
            return 'open'  # Default to open
        
        elif vowel == 'o':
            # Before consonants tends to be closed
            if position < len(word_context) - 1:
                next_char = word_context[position + 1].lower()
                if next_char in list('bcdfghjklmnpqrstvwxyz'):
                    return 'closed'
            return 'open'  # Default to open
        
        return 'closed'
    
    def _is_glide_context(self, position: int, word_context: str) -> bool:
        """Check if 'i' should be treated as glide (j) in current context."""
        if position == 0 or position >= len(word_context) - 1:
            return False
        
        prev_char = word_context[position - 1].lower()
        next_char = word_context[position + 1].lower()
        
        # i is glide between vowels (e.g., "lei" where i becomes j in some dialects)
        # For this implementation, we'll use a simpler rule
        if self._is_vowel(prev_char) and self._is_vowel(next_char):
            # Avoid gli pattern and specific consonant contexts
            if position > 0 and position < len(word_context) - 1:
                # Check if this is part of gli
                if position > 0 and position < len(word_context) - 1:
                    context_window = word_context[max(0, position-1):position+2].lower()
                    if 'gli' in context_window:
                        return False
                
                # Simple rule: i between a and e, a and a, e and a, etc. becomes j
                return True
        
        return False
    
    def _is_vowel(self, char: str) -> bool:
        """Check if character is a vowel."""
        return char.lower() in 'aeiou'
    
    def get_phoneme_description(self, ipa_symbol: str) -> str:
        """Get phonetic description for IPA symbol."""
        descriptions = {
            'tʃ': "C morbida (es. cena)",
            'k': "C dura (es. cane)",
            'ʎ': "GLI (es. moglie)",
            'r': "R (vibrante)",
            'z': "S sonora (es. casa)",
            's': "S sorda (es. sole)",
            't': "T",
            'ɲ': "GN (es. gnomo)",
            'dz': "Z sonora (es. zero)",
            'ts': "Z sorda (es. pazzo)",
            'dʒ': "G morbido (es. gente)",
            'ʃ': "SC (es. scena)",
            'j': "I glide (es. iato)",
            'e': "E chiusa (es. vede)",
            'ɛ': "E aperta (es. bello)",
            'ɔ': "O aperta (es. ora)",
            'o': "O chiusa (es. porta)",
            'a': "A",
            'i': "I",
            'u': "U"
        }
        return descriptions.get(ipa_symbol, f"IPA symbol: {ipa_symbol}")
    
    def _is_consonant(self, char: str) -> bool:
        """Check if character is a consonant."""
        return char.lower() in 'bcdfghjklmnpqrstvwxyz'
    
    def convert_word_to_ipa_sequence(self, word: str, phonemes: List[str]) -> List[Tuple[str, float]]:
        """
        Convert a sequence of orthographic phonemes to IPA sequence.
        
        Args:
            word: The original word
            phonemes: List of orthographic phonemes
            
        Returns:
            List of (IPA_symbol, linguistic_weight) tuples
        """
        ipa_sequence = []
        
        for i, phoneme in enumerate(phonemes):
            ipa_symbol, weight = self.convert_orthographic_to_ipa(phoneme, i, word)
            ipa_sequence.append((ipa_symbol, weight))
        
        return ipa_sequence
    
    def convert_word_to_ipa_dict_first(self, word: str, phonemes: List[str]) -> List[Tuple[str, float]]:
        """
        Convert a word to IPA using dictionary-first approach.
        
        Args:
            word: The original word
            phonemes: List of orthographic phonemes (for fallback)
            
        Returns:
            List of (IPA_symbol, linguistic_weight) tuples
        """
        # Try dictionary lookup first
        if self.dictionary.is_loaded():
            # Strip punctuation for dictionary lookup
            word_for_lookup = word.strip('.,!?;:"\'')
            dictionary_transcriptions = self.dictionary.lookup_word(word_for_lookup)
            if dictionary_transcriptions:
                # Use the first transcription from dictionary
                ipa_transcription = dictionary_transcriptions[0]
                return self._parse_dictionary_ipa(ipa_transcription)
        
        # Fallback to rule-based conversion
        logger.debug(f"Word '{word}' not found in dictionary, using rule-based conversion")
        return self.convert_word_to_ipa_sequence(word, phonemes)
    
    def _parse_dictionary_ipa(self, ipa_transcription: str) -> List[Tuple[str, float]]:
        """
        Parse IPA transcription from dictionary into weighted phoneme sequence.
        Handles both space-separated and continuous IPA strings.
        Preserves stress marks from dictionary entries.
        
        Args:
            ipa_transcription: IPA transcription from dictionary (may be space-separated or continuous)
            
        Returns:
            List of (IPA_symbol, linguistic_weight) tuples
        """
        if not ipa_transcription:
            return []
        
        # Preserve stress marks, split by spaces and filter out empty strings
        ipa_symbols = [symbol for symbol in ipa_transcription.split() if symbol.strip()]
        
        # If no spaces, need to parse the continuous string
        if len(ipa_symbols) == 1 and len(ipa_symbols[0]) > 1:
            ipa_symbols = self._parse_continuous_ipa(ipa_symbols[0])
        
        ipa_sequence = []
        for symbol in ipa_symbols:
            # Dictionary transcriptions get higher base weight
            base_weight = 0.95
            
            # Adjust weight based on phoneme type using existing weight system
            if symbol in self.ipa_weights:
                weight = self.ipa_weights[symbol]
            elif symbol in ['a', 'e', 'i', 'o', 'u', 'ɛ', 'ɔ']:
                weight = self.default_weights['vowel']
            elif symbol in ['j', 'w']:
                weight = self.default_weights['semivowel']
            else:
                weight = self.default_weights['consonant']
            
            # Use higher of base weight and specific weight
            final_weight = max(base_weight, weight)
            ipa_sequence.append((symbol, final_weight))
        
        return ipa_sequence
    
    def _parse_continuous_ipa(self, ipa_string: str) -> List[str]:
        """
        Parse a continuous IPA string into individual IPA symbols.
        Handles multi-character symbols like tʃ, dʒ, etc.
        Also handles stress marks (ˈ, ˌ) as separate symbols.
        
        Args:
            ipa_string: Continuous IPA string without spaces
            
        Returns:
            List of individual IPA symbols
        """
        symbols = []
        i = 0
        
        # Multi-character IPA symbols to check for
        multi_char_symbols = ['tʃ', 'dʒ', 'ts', 'dz', 'ʎ', 'ɲ', 'ʃ']
        
        while i < len(ipa_string):
            # Check for stress marks first
            if ipa_string[i] in ['ˈ', 'ˌ']:
                symbols.append(ipa_string[i])
                i += 1
                continue
            
            # Check for multi-character symbols
            if i < len(ipa_string) - 1:
                two_char = ipa_string[i:i+2]
                if two_char in multi_char_symbols:
                    symbols.append(two_char)
                    i += 2
                    continue
            
            # Check for length mark (colon)
            if i < len(ipa_string) - 1 and ipa_string[i+1] == ':':
                symbols.append(ipa_string[i] + ':')
                i += 2
                continue
            
            # Single character symbol
            symbols.append(ipa_string[i])
            i += 1
        
        return symbols


def create_italian_ipa_converter(dictionary: Optional[ItalianDictionary] = None) -> ItalianIPAConverter:
    """
    Factory function to create Italian IPA converter instance.
    
    Args:
        dictionary: Optional ItalianDictionary instance for pronunciation lookup
        
    Returns:
        ItalianIPAConverter instance
    """
    return ItalianIPAConverter(dictionary)


# Utility function for batch conversion
def batch_convert_to_ipa(words: List[str], phoneme_sequences: List[List[str]]) -> List[List[Tuple[str, float]]]:
    """
    Convert multiple words and their phoneme sequences to IPA.
    
    Args:
        words: List of words
        phoneme_sequences: List of phoneme sequences for each word
        
    Returns:
        List of IPA sequences with weights
    """
    converter = create_italian_ipa_converter()
    results = []
    
    for word, phonemes in zip(words, phoneme_sequences):
        ipa_sequence = converter.convert_word_to_ipa_sequence(word, phonemes)
        results.append(ipa_sequence)
    
    return results
