import pytest
from whisperx.ipa_converter import ItalianIPAConverter, ItalianDictionary

def parse_test_reference_phrases(filepath):
    """
    Parse TEST_REFERENCE_PHRASES file.
    Returns list of (text, ipa) tuples.
    """
    phrases = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and not line.startswith('/'):
            text = line
            if i + 1 < len(lines):
                ipa_line = lines[i + 1].strip()
                if ipa_line.startswith('/'):
                    ipa = ipa_line.strip('/')
                    phrases.append((text, ipa))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    
    return phrases

def normalize_ipa(ipa):
    """
    Normalize IPA for comparison.
    Remove stress marks, standalone length marks.
    Keep spaces to preserve word boundaries.
    """
    normalized = ipa
    normalized = normalized.replace('ˈ', '')
    normalized = normalized.replace('ˌ', '')
    normalized = normalized.replace("'", '')
    normalized = normalized.replace('ː', ':')  # Normalize different length marks
    # Remove extra spaces
    import re
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def split_into_words(text):
    """
    Split text into words, removing punctuation.
    """
    import re
    words = re.findall(r"\b\w+\b", text, re.UNICODE)
    return words

def compare_ipa_sequences(converted, reference):
    """
    Compare two IPA sequences, return True if match.
    """
    conv_norm = normalize_ipa(converted)
    ref_norm = normalize_ipa(reference)
    
    # Simple string comparison
    return conv_norm == ref_norm

def test_italian_phonemization_detailed():
    """
    Test Italian phonemization against reference phrases with detailed comparison.
    """
    converter = ItalianIPAConverter()
    
    test_file = '/home/data/work/work/business/vibe_tech_group/vibe/whisperX/TEST_REFERENCE_PHRASES'
    phrases = parse_test_reference_phrases(test_file)
    
    results = []
    total_phrases = len(phrases)
    matched_phrases = 0
    
    for idx, (text, reference_ipa) in enumerate(phrases):
        words = split_into_words(text)
        
        # Convert each word
        word_ipas = []
        for word in words:
            try:
                ipa_sequence = converter.convert_word_to_ipa_dict_first(word, list(word))
                converted_ipa = ' '.join([sym for sym, weight in ipa_sequence])
                word_ipas.append(converted_ipa)
            except Exception as e:
                word_ipas.append(f"ERROR: {e}")
        
        # Join all word IPAs (simulating full phrase IPA)
        full_converted_ipa = ' '.join(word_ipas)
        
        # Try to match
        matched = compare_ipa_sequences(full_converted_ipa, reference_ipa)
        
        if matched:
            matched_phrases += 1
        
        # Calculate word-level matches
        word_matches = []
        # Split reference IPA into parts (rough approximation)
        ref_parts = reference_ipa.split()
        ref_idx = 0
        for word, word_ipa in zip(words, word_ipas):
            # Try to match word's IPA to corresponding reference segment
            # This is a naive approach - just count phonemes
            expected_phoneme_count = len(word) // 2 + 1  # Rough estimate
            expected_ipa = ' '.join(ref_parts[ref_idx:ref_idx + expected_phoneme_count])
            ref_idx += expected_phoneme_count
            if ref_idx >= len(ref_parts):
                ref_idx = len(ref_parts) - 1
            
            word_match = word_ipa == expected_ipa if expected_ipa else False
            word_matches.append({
                'word': word,
                'converted': word_ipa,
                'expected_approx': expected_ipa,
                'match': word_match
            })
        
        results.append({
            'index': idx + 1,
            'text': text,
            'reference_ipa': reference_ipa,
            'converted_ipa': full_converted_ipa,
            'matched': matched,
            'word_matches': word_matches
        })
    
    # Print detailed results
    print(f"\n{'='*100}")
    print(f"ITALIAN PHONEMIZATION TEST - DETAILED COMPARISON")
    print(f"{'='*100}")
    print(f"Total phrases: {total_phrases}")
    print(f"Exact phrase matches: {matched_phrases}")
    print(f"Phrase match rate: {matched_phrases/total_phrases*100:.1f}%")
    print(f"{'='*100}\n")
    
    # Show mismatches first
    mismatches = [r for r in results if not r['matched']]
    
    print(f"\n--- PHRASE MISMATCHES ({len(mismatches)}) ---")
    for result in mismatches:
        print(f"\nPhrase {result['index']}: {result['text']}")
        print(f"  Reference: {result['reference_ipa']}")
        print(f"  Converted: {result['converted_ipa']}")
        print(f"  Word-level:")
        for wm in result['word_matches']:
            if not wm['match']:
                print(f"    {wm['word']}: got '{wm['converted']}', approx '{wm['expected_approx']}'")
    
    # Show matches
    matches = [r for r in results if r['matched']]
    print(f"\n\n--- PHRASE MATCHES ({len(matches)}) ---")
    for result in matches:
        print(f"Phrase {result['index']}: {result['text']}")
    
    # Summary statistics
    print(f"\n\n{'='*100}")
    print(f"WORD-LEVEL STATISTICS")
    print(f"{'='*100}")
    
    total_words = sum(len(r['word_matches']) for r in results)
    matched_words = sum(sum(1 for wm in r['word_matches'] if wm['match']) for r in results)
    
    print(f"Total words: {total_words}")
    print(f"Matched words: {matched_words}")
    print(f"Word match rate: {matched_words/total_words*100:.1f}%")
    print(f"{'='*100}\n")
    
    # Save results to file for analysis
    import json
    output_file = '/tmp/phonemization_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Full results saved to: {output_file}\n")

if __name__ == '__main__':
    test_italian_phonemization_detailed()
