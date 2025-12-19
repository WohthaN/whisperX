#!/usr/bin/env python3
"""
Letter-Phoneme Alignment Extractor

Extracts and displays letter-phoneme correspondence from WhisperX aligned output JSON files.
Shows two lines per segment: one for letters, one for phonemes, with visual alignment.
"""

import json
import sys


def load_json_file(file_path):
    """Load and parse JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: File '{}' not found.".format(file_path), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("Error: Invalid JSON in file '{}': {}".format(file_path, e), file=sys.stderr)
        sys.exit(1)


def extract_segment_data(segment):
    """Extract text and ipa_segments from a segment."""
    text = segment.get('text', '')
    ipa_segments = segment.get('ipa_segments', [])
    return text, ipa_segments


def build_aligned_lines(text, ipa_segments):
    """
    Build aligned letters and phonemes lines with proper word and phoneme spacing.
    Returns: (letters_line, phonemes_line)
    """
    if not ipa_segments:
        return text, ""
    
    # Split original text into words to preserve word boundaries
    words = text.split()
    
    # Group IPA segments by words
    word_segments = []
    current_word_segments = []
    char_position = 0
    current_word_idx = 0
    
    for segment in ipa_segments:
        orthographic = segment.get('orthographic', '')
        ipa_symbol = segment.get('ipa_symbol', '')
        
        # Check if we've completed the current word
        if current_word_idx < len(words):
            current_word = words[current_word_idx]
            if char_position >= len(current_word):
                # Move to next word
                word_segments.append(current_word_segments)
                current_word_segments = [segment]
                current_word_idx += 1
                char_position = len(orthographic)
            else:
                current_word_segments.append(segment)
                char_position += len(orthographic)
        else:
            current_word_segments.append(segment)
            char_position += len(orthographic)
    
    # Add the last word
    if current_word_segments:
        word_segments.append(current_word_segments)
    
    # Build aligned lines for each word
    letters_words = []
    phonemes_words = []
    
    for word_idx, word_ipa_segments in enumerate(word_segments):
        if word_idx < len(words):
            # Extract letter groups and phonemes for this word
            letter_groups = []
            phonemes = []
            
            for segment in word_ipa_segments:
                orthographic = segment.get('orthographic', '')
                ipa_symbol = segment.get('ipa_symbol', '')
                
                letter_groups.append(orthographic)
                phonemes.append(ipa_symbol)
            
            # Build the word lines with proper alignment
            word_letters, word_phonemes = align_word_letters_and_phonemes(letter_groups, phonemes)
            letters_words.append(word_letters)
            phonemes_words.append(word_phonemes)
    
    # Join words with 4 spaces
    letters_line = '    '.join(letters_words)
    phonemes_line = '    '.join(phonemes_words)
    
    return letters_line, phonemes_line


def align_word_letters_and_phonemes(letter_groups, phonemes):
    """
    Align phonemes under their corresponding letter groups for a single word.
    Returns: (letters_line, phonemes_line)
    """
    letters_line = ''.join(letter_groups)
    
    # Build phonemes line with proper spacing
    phonemes_parts = []
    
    for i, (letter_group, phoneme) in enumerate(zip(letter_groups, phonemes)):
        if i > 0:
            phonemes_parts.append(' ')  # 1 space between phonemes
        
        # Calculate padding to center phoneme under letter group
        letter_width = len(letter_group)
        phoneme_width = len(phoneme)
        
        if letter_width > phoneme_width:
            # Center the phoneme under the letter group
            total_padding = letter_width - phoneme_width
            left_padding = total_padding // 2
            right_padding = total_padding - left_padding
            
            # Add padding and phoneme
            phoneme_with_padding = ' ' * left_padding + phoneme + ' ' * right_padding
            phonemes_parts.append(phoneme_with_padding)
        else:
            # Phoneme is wider or same width, just add it
            phonemes_parts.append(phoneme)
    
    # Join all parts and trim trailing spaces
    phonemes_line = ''.join(phonemes_parts).rstrip()
    
    return letters_line, phonemes_line


def format_segment_output(letters_line, phonemes_line):
    """Format the output for a single segment."""
    return "{}\n{}".format(letters_line, phonemes_line)


def main():
    """Main function with CLI argument parsing."""
    if len(sys.argv) != 2:
        print("Usage: python extract_alignment.py <json_file>", file=sys.stderr)
        print("Extracts letter-phoneme alignment from WhisperX JSON output", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    data = load_json_file(file_path)
    
    # Check if this is the expected format
    segments = data.get('segments', [])
    if not segments:
        print("Error: No segments found in JSON file.", file=sys.stderr)
        sys.exit(1)
    
    # Process each segment
    first_segment = True
    for i, segment in enumerate(segments):
        text, ipa_segments = extract_segment_data(segment)
        
        if not text or not ipa_segments:
            continue
        
        letters_line, phonemes_line = build_aligned_lines(text, ipa_segments)
        
        if not first_segment:
            print()  # Empty line between segments for better readability
        
        output = format_segment_output(letters_line, phonemes_line)
        print(output)
        
        first_segment = False


if __name__ == "__main__":
    main()