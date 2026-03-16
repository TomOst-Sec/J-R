"""Keyword-based dimension classifier for topic categorization."""

from __future__ import annotations

_PROFESSIONAL_KEYWORDS = {
    "engineer", "developer", "architect", "manager", "director", "analyst",
    "scientist", "researcher", "consultant", "designer", "devops", "sre",
    "infrastructure", "backend", "frontend", "fullstack", "cloud", "aws",
    "kubernetes", "docker", "ci/cd", "agile", "scrum", "startup", "saas",
    "api", "database", "sql", "machine learning", "deep learning", "ai",
    "data science", "nlp", "computer vision", "cybersecurity", "security",
    "blockchain", "fintech", "product", "marketing", "sales", "recruitment",
    "hr", "finance", "accounting", "legal", "compliance", "audit",
    "certification", "degree", "university", "conference", "keynote",
    "published", "patent", "open source", "github", "stack overflow",
    "linkedin", "resume", "portfolio", "interview", "hiring", "salary",
    "remote", "office", "team", "leadership", "promotion", "quarterly",
}

_PERSONAL_KEYWORDS = {
    "hobby", "travel", "vacation", "weekend", "family", "kids", "children",
    "wife", "husband", "partner", "dog", "cat", "pet", "cooking", "recipe",
    "hiking", "camping", "skiing", "surfing", "cycling", "running",
    "marathon", "fitness", "gym", "yoga", "meditation", "gaming", "game",
    "movie", "film", "music", "concert", "festival", "book", "reading",
    "photography", "art", "painting", "crafts", "gardening", "diy",
    "home", "house", "apartment", "birthday", "holiday", "christmas",
    "thanksgiving", "new year", "food", "restaurant", "coffee",
    "beer", "wine", "sports", "football", "basketball", "soccer", "tennis",
    "golf", "anime", "manga", "streaming", "netflix", "spotify",
}

_PUBLIC_KEYWORDS = {
    "politics", "election", "vote", "democrat", "republican", "liberal",
    "conservative", "policy", "government", "congress", "senate", "law",
    "regulation", "climate", "environment", "sustainability", "green",
    "renewable", "social justice", "equality", "diversity", "inclusion",
    "blm", "lgbtq", "rights", "activism", "protest", "petition",
    "charity", "donation", "volunteer", "nonprofit", "community",
    "education", "public health", "pandemic", "covid", "vaccine",
    "immigration", "privacy", "surveillance", "censorship", "free speech",
    "union", "labor", "minimum wage", "healthcare", "housing", "homelessness",
    "gun", "abortion", "religion", "church", "mosque", "temple",
}


class DimensionClassifier:
    """Classifies topics into professional, personal, or public dimensions."""

    def __init__(
        self,
        extra_professional: set[str] | None = None,
        extra_personal: set[str] | None = None,
        extra_public: set[str] | None = None,
    ) -> None:
        self._professional = _PROFESSIONAL_KEYWORDS | (extra_professional or set())
        self._personal = _PERSONAL_KEYWORDS | (extra_personal or set())
        self._public = _PUBLIC_KEYWORDS | (extra_public or set())

    def classify(self, topic: str) -> str:
        """Classify a topic into a dimension: professional, personal, or public."""
        topic_lower = topic.lower()

        scores = {
            "professional": self._match_score(topic_lower, self._professional),
            "personal": self._match_score(topic_lower, self._personal),
            "public": self._match_score(topic_lower, self._public),
        }

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            return "personal"  # default to personal if no match
        return best

    def _match_score(self, topic: str, keywords: set[str]) -> int:
        """Count how many keywords appear in the topic string."""
        score = 0
        for kw in keywords:
            if kw in topic:
                score += 1
        return score
