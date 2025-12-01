from typing import TypedDict, Optional, List, Tuple


class SingleWordSegment(TypedDict):
    """
    A single word of a speech.
    """
    word: str
    start: float
    end: float
    score: float

class SingleCharSegment(TypedDict):
    """
    A single char of a speech.
    """
    char: str
    start: float
    end: float
    score: float


class SinglePhonemeSegment(TypedDict):
    """
    A single phoneme of a speech.
    """
    phoneme: str
    start: float
    end: float
    score: float


class SingleIPASegment(TypedDict):
    """
    A single IPA phoneme segment with linguistic weight.
    """
    ipa_symbol: str          # IPA symbol (e.g., 'ʧ', 'k', 'ʎ')
    orthographic: str        # Original text (e.g., 'ci', 'c', 'gl')
    start: float            # Start timestamp
    end: float              # End timestamp
    linguistic_weight: float # Linguistic weight from schema (0.0-1.0)
    confidence: float       # Model confidence score
    description: Optional[str] # Description of phoneme characteristics


class SingleSegment(TypedDict):
    """
    A single segment (up to multiple sentences) of a speech.
    """

    start: float
    end: float
    text: str


class SegmentData(TypedDict):
    """
    Temporary processing data used during alignment.
    Contains cleaned and preprocessed data for each segment.
    """
    clean_char: List[str]  # Cleaned characters that exist in model dictionary
    clean_cdx: List[int]   # Original indices of cleaned characters
    clean_wdx: List[int]   # Indices of words containing valid characters
    sentence_spans: List[Tuple[int, int]]  # Start and end indices of sentences


class SingleAlignedSegment(TypedDict):
    """
    A single segment (up to multiple sentences) of a speech with word alignment.
    """

    start: float
    end: float
    text: str
    words: List[SingleWordSegment]
    chars: Optional[List[SingleCharSegment]]
    phonemes: Optional[List[SinglePhonemeSegment]]
    ipa_segments: Optional[List[SingleIPASegment]]


class TranscriptionResult(TypedDict):
    """
    A list of segments and word segments of a speech.
    """
    segments: List[SingleSegment]
    language: str


class AlignedTranscriptionResult(TypedDict):
    """
    A list of segments and word segments of a speech.
    """
    segments: List[SingleAlignedSegment]
    word_segments: List[SingleWordSegment]
    phoneme_segments: Optional[List[SinglePhonemeSegment]]
    ipa_segments: Optional[List[SingleIPASegment]]
