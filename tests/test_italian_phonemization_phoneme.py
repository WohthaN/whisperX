import pytest
import json
from pathlib import Path
from whisperx.ipa_converter import ItalianIPAConverter, ItalianDictionary

def parse_test_reference_phrases(filepath):
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

def normalize_for_phoneme_comparison(ipa):
    """
    Normalize IPA to pure phoneme sequence for comparison.
    Removes stress marks, spaces, and length markers.
    """
    normalized = ipa
    normalized = normalized.replace('ˈ', '')
    normalized = normalized.replace('ˌ', '')
    normalized = normalized.replace("'", '')
    normalized = normalized.replace(':', '')
    normalized = normalized.replace('ː', '')
    normalized = normalized.replace(' ', '')
    return normalized

def split_into_words(text):
    import re
    words = re.findall(r"\b\w+\b", text, re.UNICODE)
    return words

def test_italian_phonemization_phoneme_level():
    """
    Test Italian phonemization at phoneme level (ignoring stress and length marks).
    """
    converter = ItalianIPAConverter()
    
    test_file = Path(__file__).parent / 'REFERENCE_PHRASES.md'
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
                converted_ipa = ''.join([sym for sym, weight in ipa_sequence])
                word_ipas.append(converted_ipa)
            except Exception as e:
                word_ipas.append(f"ERROR: {e}")
        
        # Join all word IPAs
        full_converted_ipa = ''.join(word_ipas)
        
        # Normalize and compare
        ref_phonemes = normalize_for_phoneme_comparison(reference_ipa)
        conv_phonemes = normalize_for_phoneme_comparison(full_converted_ipa)
        
        matched = ref_phonemes == conv_phonemes
        
        if matched:
            matched_phrases += 1
        
        results.append({
            'index': idx + 1,
            'text': text,
            'reference_ipa': reference_ipa,
            'converted_ipa': full_converted_ipa,
            'ref_phonemes': ref_phonemes,
            'conv_phonemes': conv_phonemes,
            'matched': matched,
            'words': words,
            'word_ipas': word_ipas
        })
    
    # Print results
    print(f"\n{'='*100}")
    print(f"ITALIAN PHONEMIZATION TEST - PHONEME LEVEL (ignoring stress/length marks)")
    print(f"{'='*100}")
    print(f"Total phrases: {total_phrases}")
    print(f"Exact phoneme matches: {matched_phrases}")
    print(f"Match rate: {matched_phrases/total_phrases*100:.1f}%")
    print(f"{'='*100}\n")
    
    # Show mismatches
    mismatches = [r for r in results if not r['matched']]
    
    print(f"\n--- MISMATCHES ({len(mismatches)}) ---")
    for result in mismatches:
        print(f"\nPhrase {result['index']}: {result['text']}")
        print(f"  Reference phonemes: {result['ref_phonemes']}")
        print(f"  Converted phonemes: {result['conv_phonemes']}")
        
        # Find where they differ
        for i, (r, c) in enumerate(zip(result['ref_phonemes'], result['conv_phonemes'])):
            if r != c:
                print(f"  Position {i}: expected '{r}', got '{c}'")
        
        # Also show word-level
        print(f"  Word-level:")
        for word, word_ipa in zip(result['words'], result['word_ipas']):
            print(f"    {word}: {word_ipa}")
    
    # Show matches
    matches = [r for r in results if r['matched']]
    print(f"\n\n--- MATCHES ({len(matches)}) ---")
    for result in matches:
        print(f"Phrase {result['index']}: {result['text']}")
    
    # Detailed word analysis
    print(f"\n\n{'='*100}")
    print(f"DETAILED WORD ANALYSIS")
    print(f"{'='*100}")
    
    word_errors = []
    for result in results:
        if not result['matched']:
            # Get reference IPA segments for each word
            ref_phonemes = result['ref_phonemes']
            conv_phonemes = result['conv_phonemes']
            
            # Try to map words to their expected IPA
            ref_idx = 0
            for word in result['words']:
                # Estimate word phoneme count
                estimated_count = len(word) // 2 + 1
                
                if ref_idx + estimated_count <= len(ref_phonemes):
                    expected_segment = ref_phonemes[ref_idx:ref_idx + estimated_count]
                    ref_idx += estimated_count
                else:
                    expected_segment = ref_phonemes[ref_idx:]
                    ref_idx = len(ref_phonemes)
                
                word_errors.append({
                    'phrase': result['index'],
                    'word': word,
                    'expected': expected_segment,
                    'converted': conv_phonemes
                })
    
    # Save to file
    with open('/tmp/phonemization_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Full results saved to: /tmp/phonemization_test_results.json\n")

if __name__ == '__main__':
    test_italian_phonemization_phoneme_level()
