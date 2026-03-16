"""LLM-enhanced helpers with offline fallbacks."""

from __future__ import annotations

import re

from argus.llm.provider import LLMProvider


async def compare_bios(bio_a: str, bio_b: str, provider: LLMProvider) -> float:
    """Compare two bios using LLM, falling back to TF-IDF similarity."""
    if await provider.is_available():
        prompt = (
            f"Compare these two bios and rate similarity 0.0-1.0:\n"
            f"Bio A: {bio_a}\nBio B: {bio_b}\n"
            f"Respond with ONLY a float number."
        )
        try:
            result = await provider.complete(prompt, max_tokens=10)
            score = float(result.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            pass

    # Offline fallback: TF-IDF cosine similarity
    return _tfidf_similarity(bio_a, bio_b)


async def extract_topics(text: str, provider: LLMProvider) -> list[str]:
    """Extract topics from text using LLM, falling back to keyword extraction."""
    if await provider.is_available():
        prompt = (
            f"Extract 5-10 key topics from this text. "
            f"Return only comma-separated topic names:\n{text[:1000]}"
        )
        try:
            result = await provider.complete(prompt, max_tokens=100)
            return [t.strip() for t in result.split(",") if t.strip()]
        except Exception:
            pass

    # Offline fallback: simple keyword extraction
    return _extract_keywords(text)


async def classify_dimension(
    topic: str, context: str, provider: LLMProvider
) -> str:
    """Classify a topic into a dimension using LLM, falling back to keyword matching."""
    if await provider.is_available():
        prompt = (
            f"Classify this topic into one dimension "
            f"(technology, business, science, arts, sports, lifestyle, politics, other):\n"
            f"Topic: {topic}\nContext: {context[:500]}\n"
            f"Respond with ONLY the dimension name."
        )
        try:
            result = await provider.complete(prompt, max_tokens=20)
            return result.strip().lower()
        except Exception:
            pass

    # Offline fallback: keyword-based classification
    return _keyword_classify(topic, context)


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    """Simple word-overlap similarity as TF-IDF fallback."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """Extract keywords using frequency analysis."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "and", "but", "or", "if", "while", "i", "me",
        "my", "we", "our", "you", "your", "he", "him", "she", "her", "it",
        "its", "they", "them", "their", "this", "that", "these", "those",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    filtered = [w for w in words if w not in stop_words]
    freq: dict[str, int] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


_DIMENSION_KEYWORDS = {
    "technology": ["python", "javascript", "code", "software", "api", "data", "machine", "learning", "cloud", "devops", "web", "app", "developer", "engineer"],
    "business": ["startup", "business", "market", "finance", "management", "leadership", "strategy", "revenue", "growth", "product"],
    "science": ["research", "study", "experiment", "physics", "biology", "chemistry", "math", "academic", "paper", "journal"],
    "arts": ["art", "music", "design", "creative", "writing", "photography", "film", "animation", "painting", "craft"],
    "sports": ["sport", "fitness", "running", "gym", "training", "football", "basketball", "soccer", "cycling", "marathon"],
    "lifestyle": ["travel", "food", "cooking", "fashion", "health", "wellness", "yoga", "meditation", "garden"],
    "politics": ["politics", "government", "policy", "election", "democracy", "law", "justice", "rights", "activism"],
}


def _keyword_classify(topic: str, context: str) -> str:
    """Classify using keyword matching."""
    combined = f"{topic} {context}".lower()
    best_dim = "other"
    best_count = 0
    for dim, keywords in _DIMENSION_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in combined)
        if count > best_count:
            best_count = count
            best_dim = dim
    return best_dim
