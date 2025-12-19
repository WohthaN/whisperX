#!/usr/bin/env python3
"""
Letter-Phoneme Alignment Extractor

Extracts and displays letter-phoneme correspondence from WhisperX aligned output JSON files.
Shows three lines per segment: letters, pipes, and phonemes, with perfect vertical alignment.
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
    Build three-line display with letters, pipes, and phonemes.
    Letters may be shifted to ensure vertical alignment with pipes.
    Returns: (letters_line, pipes_line, phonemes_line)
    """
    if not ipa_segments:
        return text, "", ""
    
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
    
    # Build three-line display for each word
    letters_words = []
    pipes_words = []
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
            
            # Build the word three lines with proper alignment
            word_letters, word_pipes, word_phonemes = build_word_three_lines(letter_groups, phonemes)
            letters_words.append(word_letters)
            pipes_words.append(word_pipes)
            phonemes_words.append(word_phonemes)
    
    # Join words with 4 spaces
    letters_line = '    '.join(letters_words)
    pipes_line = '    '.join(pipes_words)
    phonemes_line = '    '.join(phonemes_words)
    
    return letters_line, pipes_line, phonemes_line


def build_word_three_lines(letter_groups, phonemes):
    """
    Build three lines for a single word with perfect vertical alignment.
    Returns: (letters_line, pipes_line, phonemes_line)
    """
    
    # Calculate the width needed for each position
    # Use the maximum of letter width and phoneme width for each column
    column_widths = []
    for letter_group, phoneme in zip(letter_groups, phonemes):
        letter_width = len(letter_group)
        phoneme_width = len(phoneme)
        max_width = max(letter_width, phoneme_width)
        column_widths.append(max_width)
    
    # Line 3: Phonemes (bottom line) - build this first
    phonemes_parts = []
    for i, (phoneme, column_width) in enumerate(zip(phonemes, column_widths)):
        if i > 0:
            phonemes_parts.append(' ')  # 1 space between phonemes
        
        # Center phoneme in its allocated space
        padding = column_width - len(phoneme)
        left_padding = padding // 2
        right_padding = padding - left_padding
        
        phoneme_with_padding = ' ' * left_padding + phoneme + ' ' * right_padding
        phonemes_parts.append(phoneme_with_padding)
    
    phonemes_line = ''.join(phonemes_parts)
    
    # Line 2: Pipes (middle line) - one pipe per letter group, centered
    pipes_parts = []
    for i, column_width in enumerate(column_widths):
        if i > 0:
            pipes_parts.append(' ')  # 1 space between pipes
        
        # Center the pipe in its allocated space
        pipe_position = column_width // 2
        pipe_with_padding = ' ' * pipe_position + '|' + ' ' * (column_width - pipe_position - 1)
        pipes_parts.append(pipe_with_padding)
    
    pipes_line = ''.join(pipes_parts)
    
    # Line 1: Letters (top line) - shift letters to align with pipes
    letters_parts = []
    for i, (letter_group, column_width) in enumerate(zip(letter_groups, column_widths)):
        if i > 0:
            letters_parts.append(' ')  # 1 space between letter groups
        
        # Center letter group in its allocated space
        padding = column_width - len(letter_group)
        left_padding = padding // 2
        right_padding = padding - left_padding
        
        letters_with_padding = ' ' * left_padding + letter_group + ' ' * right_padding
        letters_parts.append(letters_with_padding)
    
    letters_line = ''.join(letters_parts)
    
    return letters_line, pipes_line, phonemes_line


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


def format_segment_output(letters_line, pipes_line, phonemes_line):
    """Format the output for a single segment."""
    return "{}\n{}\n{}".format(letters_line, pipes_line, phonemes_line)


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
        
        letters_line, pipes_line, phonemes_line = build_aligned_lines(text, ipa_segments)
        
        if not first_segment:
            print()  # Empty line between segments for better readability
        
        output = format_segment_output(letters_line, pipes_line, phonemes_line)
        print(output)
        
        first_segment = False


if __name__ == "__main__":
    main()