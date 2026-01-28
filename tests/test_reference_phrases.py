import re
from pathlib import Path
from whisperx.ipa_converter import ItalianIPAConverter


def parse_reference_phrases(filepath):
    """
    Parse REFERENCE_PHRASES.md - alternating text and /ipa/ lines
    Returns list of (text, ipa) tuples
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


def normalize_ipa_for_comparison(ipa):
    """
    Normalize IPA for comparison while preserving gemination markers.
    Removes stress marks, normalizes length marks, removes all spaces.
    """
    normalized = ipa
    # Remove stress marks
    normalized = normalized.replace('ˈ', '')
    normalized = normalized.replace('ˌ', '')
    normalized = normalized.replace("'", '')
    # Normalize length marks (keep colons for gemination!)
    normalized = normalized.replace('ː', ':')
    # Remove all spaces
    normalized = re.sub(r'\s+', '', normalized)
    return normalized


def split_phrase_into_words(text):
    """
    Split phrase into words, preserving Italian contractions like "l'illumina"
    Returns list of words with apostrophes preserved for contraction matching
    """
    # Match words including contractions (words with both regular and curly apostrophes)
    words = re.findall(r"\b\w+(?:[\u0027\u2019]\w+)?\b", text, re.UNICODE)
    
    return words


def test_reference_phrases():
    """
    Test Italian phonemization against 40 reference phrases.
    Strict mode: fails if ANY word doesn't match reference IPA.
    """
    converter = ItalianIPAConverter()
    
    test_file = Path(__file__).parent / 'REFERENCE_PHRASES.md'
    phrases = parse_reference_phrases(test_file)
    
    results = []
    total_phrases = len(phrases)
    passed_phrases = 0
    total_mismatches = 0
    mismatched_words = []
    
    for idx, (text, reference_ipa) in enumerate(phrases):
        words = split_phrase_into_words(text)
        reference_ipa_tokens = reference_ipa.split()
        phrase_mismatches = []
        generated_ipa_words = []
        
        # Convert each word and compare (1-to-1 word-to-IPA mapping)
        for word_idx, word in enumerate(words):
            expected_ipa = 'N/A'
            try:
                ipa_sequence = converter.convert_word_to_ipa_dict_first(word, list(word))
                converted_ipa = ''.join([sym for sym, weight in ipa_sequence])
                generated_ipa_words.append(converted_ipa)
                normalized_converted = normalize_ipa_for_comparison(converted_ipa)
                
                # Get expected IPA for this word (1-to-1 correspondence)
                if word_idx < len(reference_ipa_tokens):
                    expected_ipa = reference_ipa_tokens[word_idx]
                    normalized_expected = normalize_ipa_for_comparison(expected_ipa)
                else:
                    normalized_expected = 'N/A'
                
                # Compare
                if normalized_converted != normalized_expected:
                    phrase_mismatches.append({
                        'word': word,
                        'expected': expected_ipa,
                        'got': converted_ipa,
                        'normalized_expected': normalized_expected,
                        'normalized_got': normalized_converted
                    })
                    mismatched_words.append({
                        'phrase_idx': idx + 1,
                        'phrase': text,
                        'word': word,
                        'expected': expected_ipa,
                        'got': converted_ipa
                    })
                    total_mismatches += 1
                
            except Exception as e:
                phrase_mismatches.append({
                    'word': word,
                    'error': str(e)
                })
                mismatched_words.append({
                    'phrase_idx': idx + 1,
                    'phrase': text,
                    'word': word,
                    'expected': 'N/A',
                    'got': f'ERROR: {e}'
                })
                total_mismatches += 1
        
        if not phrase_mismatches:
            passed_phrases += 1
        
        generated_ipa = ' '.join(generated_ipa_words)
        results.append({
            'index': idx + 1,
            'text': text,
            'reference_ipa': reference_ipa,
            'generated_ipa': generated_ipa,
            'mismatches': phrase_mismatches,
            'passed': len(phrase_mismatches) == 0
        })
    
    # Print summary
    print(f"\n{'='*100}")
    print(f"ITALIAN PHONEMIZATION TEST - REFERENCE PHRASES")
    print(f"{'='*100}")
    print(f"Total phrases: {total_phrases}")
    print(f"Passed phrases: {passed_phrases}")
    print(f"Failed phrases: {total_phrases - passed_phrases}")
    print(f"Match rate: {passed_phrases/total_phrases*100:.1f}%")
    print(f"Total mismatches: {total_mismatches}")
    print(f"{'='*100}\n")
    
    # Print all phrases with comparison
    print(f"--- PHRASE-BY-PHRASE COMPARISON ---")
    for result in results:
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        print(f"\nPhrase {result['index']} [{status}]")
        print(f"  Reference: {result['text']}")
        print(f"  Reference IPA:   {result['reference_ipa']}")
        print(f"  Generated IPA:   {result['generated_ipa']}")
    print(f"\n{'='*100}\n")
    
    # Print mismatched words
    if mismatched_words:
        print(f"--- MISMATCHED WORDS ({len(mismatched_words)}) ---")
        for item in mismatched_words:
            print(f"\nPhrase {item['phrase_idx']}: {item['phrase']}")
            print(f"  Word: '{item['word']}'")
            print(f"  Expected: {item['expected']}")
            print(f"  Got: {item['got']}")
        print(f"\n{'='*100}\n")
    
    # Print passed phrases summary
    passed_phrases_list = [r for r in results if r['passed']]
    if passed_phrases_list:
        print(f"--- PASSED PHRASES ({len(passed_phrases_list)}) ---")
        for result in passed_phrases_list:
            print(f"Phrase {result['index']}: {result['text']}")
        print(f"\n{'='*100}\n")
    
    # Strict failure mode
    assert total_mismatches == 0, f"Found {total_mismatches} mismatches - dictionary needs updates"


if __name__ == '__main__':
    test_reference_phrases()
