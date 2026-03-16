"""Language detection and multi-language text processing."""

from __future__ import annotations

import re
from collections import Counter

# Stop words for common languages (minimal sets)
_STOP_WORDS: dict[str, set[str]] = {
    "en": {"the", "a", "an", "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
           "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall",
           "can", "need", "dare", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
           "into", "through", "during", "before", "after", "above", "below", "between", "and", "but",
           "or", "not", "no", "this", "that", "these", "those", "it", "its", "i", "me", "my", "we"},
    "es": {"el", "la", "los", "las", "un", "una", "de", "en", "y", "que", "es", "por", "con", "no",
           "se", "su", "para", "al", "lo", "como", "más", "pero", "fue", "son", "del"},
    "fr": {"le", "la", "les", "un", "une", "de", "du", "des", "en", "et", "est", "que", "qui", "dans",
           "ce", "il", "ne", "pas", "sur", "se", "par", "pour", "au", "avec", "son", "sont"},
    "de": {"der", "die", "das", "ein", "eine", "und", "ist", "von", "in", "mit", "den", "des", "auf",
           "für", "nicht", "sich", "auch", "als", "an", "es", "dem", "zu", "er", "hat", "aus"},
    "pt": {"o", "a", "os", "as", "um", "uma", "de", "em", "e", "que", "é", "para", "com", "não",
           "se", "por", "mais", "mas", "foi", "do", "da", "no", "na", "ao", "dos", "das"},
    "ru": {"и", "в", "не", "на", "я", "с", "что", "он", "как", "это", "по", "но", "они",
           "к", "из", "от", "за", "о", "а", "его", "ее", "мы", "так", "да", "нет"},
    "ja": {"の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ", "ある",
           "いる", "も", "する", "から", "な", "こと", "として", "い", "や", "など"},
    "zh": {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
           "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看"},
    "ko": {"이", "가", "은", "는", "을", "를", "에", "의", "도", "로", "와", "과", "하다",
           "있다", "되다", "그", "수", "것", "나", "우리", "그리고", "하지만"},
    "ar": {"في", "من", "على", "إلى", "أن", "هذا", "هذه", "التي", "الذي", "هو", "هي",
           "كان", "لا", "ما", "مع", "عن", "لم", "قد", "كل", "بعد", "بين"},
    "he": {"של", "את", "על", "אל", "הוא", "היא", "לא", "עם", "כי", "גם", "מה", "אם",
           "אני", "זה", "כל", "הם", "יש", "אין", "רק", "או", "עד", "כמו"},
}

# CJK character ranges
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
)

# Simple language detection based on character scripts
_SCRIPT_PATTERNS = [
    (re.compile(r"[\u0400-\u04ff]"), "ru"),  # Cyrillic
    (re.compile(r"[\u3040-\u309f\u30a0-\u30ff]"), "ja"),  # Hiragana/Katakana (before CJK)
    (re.compile(r"[\uac00-\ud7af]"), "ko"),  # Hangul
    (re.compile(r"[\u4e00-\u9fff]"), "zh"),  # CJK (Chinese if no Japanese/Korean markers)
    (re.compile(r"[\u0590-\u05ff]"), "he"),  # Hebrew
    (re.compile(r"[\u0600-\u06ff]"), "ar"),  # Arabic
]


def detect_language(text: str) -> str:
    """Detect the primary language of text. Returns ISO 639-1 code."""
    if not text or not text.strip():
        return "en"

    # Try langdetect if available
    try:
        from langdetect import detect  # type: ignore[import-untyped]
        return detect(text)
    except (ImportError, Exception):
        pass

    # Fallback: script-based detection
    for pattern, lang in _SCRIPT_PATTERNS:
        if pattern.search(text):
            return lang

    # Default to English for Latin scripts
    return "en"


class LanguageProcessor:
    """Multi-language text processing for keyword extraction."""

    def tokenize(self, text: str, language: str | None = None) -> list[str]:
        """Tokenize text into words/tokens based on language."""
        if language is None:
            language = detect_language(text)

        # CJK: character-based tokenization
        if language in ("zh", "ja", "ko"):
            chars = list(text)
            # Extract CJK character n-grams (bigrams)
            tokens = []
            for i in range(len(chars) - 1):
                if _CJK_RE.match(chars[i]) and _CJK_RE.match(chars[i + 1]):
                    tokens.append(chars[i] + chars[i + 1])
            # Also add individual characters
            tokens.extend(c for c in chars if _CJK_RE.match(c))
            return tokens

        # Space-based tokenization for other languages
        words = re.findall(r"\b\w+\b", text.lower())
        return words

    def remove_stop_words(self, tokens: list[str], language: str = "en") -> list[str]:
        """Remove stop words for the given language."""
        stop = _STOP_WORDS.get(language, _STOP_WORDS.get("en", set()))
        return [t for t in tokens if t not in stop and len(t) > 1]

    def extract_keywords(self, text: str, top_n: int = 10, language: str | None = None) -> list[str]:
        """Extract top keywords from text."""
        if language is None:
            language = detect_language(text)
        tokens = self.tokenize(text, language)
        filtered = self.remove_stop_words(tokens, language)
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(top_n)]
