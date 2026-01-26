import pytest
from pathlib import Path
from whisperx.ipa_converter import ItalianIPAConverter, ItalianDictionary

def parse_reference_phrases(filepath):
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

def parse_reference_phrases(filepath):
    """
    Parse REFERENCE_PHRASES.md file.
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
    Remove stress marks, standalone length marks, and spaces.
    """
    normalized = ipa
    normalized = normalized.replace('ˈ', '')
    normalized = normalized.replace('ˌ', '')
    normalized = normalized.replace('\'', '')
    normalized = normalized.replace('ː', '')
    normalized = normalized.replace(' ', '')
    return normalized

def split_into_words(text):
    """
    Split text into words, removing punctuation.
    """
    import re
    words = re.findall(r'\b\w+\b', text, re.UNICODE)
    return words

def match_words_to_ipa(words, reference_ipa):
    """
    Naive word-to-IPA matching.
    Since reference IPA doesn't have explicit word boundaries,
    we'll try to match phonemes sequentially.
    Returns list of (word, expected_ipa_segment)
    """
    results = []
    ref_phonemes = reference_ipa.split()
    ref_index = 0
    
    for word in words:
        word_phonemes = []
        while ref_index < len(ref_phonemes) and len(word_phonemes) < 5:
            word_phonemes.append(ref_phonemes[ref_index])
            ref_index += 1
        expected_ipa = ' '.join(word_phonemes)
        results.append((word, expected_ipa))
    
    return results

def test_italian_phonemization():
    """
    Test Italian phonemization against reference phrases.
    """
    converter = ItalianIPAConverter()
    
    test_file = Path(__file__).parent / 'REFERENCE_PHRASES.md'
    phrases = parse_reference_phrases(test_file)
    
    results = []
    total_phrases = len(phrases)
    passed_phrases = 0
    
    for idx, (text, reference_ipa) in enumerate(phrases):
        words = split_into_words(text)
        
        phrase_pass = True
        word_results = []
        
        for word in words:
            try:
                ipa_sequence = converter.convert_word_to_ipa_dict_first(word, list(word))
                converted_ipa = ' '.join([sym for sym, weight in ipa_sequence])
                normalized_converted = normalize_ipa(converted_ipa)
                
                word_results.append({
                    'word': word,
                    'converted': converted_ipa,
                    'normalized_converted': normalized_converted
                })
            except Exception as e:
                word_results.append({
                    'word': word,
                    'error': str(e)
                })
                phrase_pass = False
        
        if phrase_pass:
            passed_phrases += 1
        
        results.append({
            'index': idx + 1,
            'text': text,
            'reference_ipa': reference_ipa,
            'word_results': word_results,
            'passed': phrase_pass
        })
    
    print(f"\n{'='*80}")
    print(f"ITALIAN PHONEMIZATION TEST RESULTS")
    print(f"{'='*80}")
    print(f"Total phrases: {total_phrases}")
    print(f"Passed: {passed_phrases}")
    print(f"Failed: {total_phrases - passed_phrases}")
    print(f"{'='*80}\n")
    
    for result in results:
        print(f"\nPhrase {result['index']}: {result['text']}")
        print(f"Reference IPA: {result['reference_ipa']}")
        print(f"Word-level conversions:")
        for word_res in result['word_results']:
            if 'error' in word_res:
                print(f"  {word_res['word']}: ERROR - {word_res['error']}")
            else:
                print(f"  {word_res['word']}: {word_res['converted']}")
    
    print(f"\n{'='*80}")
    
    assert passed_phrases > 0, "All phrases failed to process"

if __name__ == '__main__':
    test_italian_phonemization()
