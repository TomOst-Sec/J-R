"""Profiler Agent — builds behavioral profiles from discovered content."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sklearn.feature_extraction.text import TfidfVectorizer

from argus.agents.base import BaseAgent
from argus.agents.classifiers import DimensionClassifier
from argus.models.agent import AgentInput, AgentOutput, ProfilerOutput, TopicScore
from argus.models.profile import ContentItem
from argus.models.verification import VerificationResult

# Number of top keywords to extract
_TOP_KEYWORDS = 20
# Decay half-life in days for recency weighting
_RECENCY_HALF_LIFE_DAYS = 90


class ProfilerInput(AgentInput):
    """Input for the Profiler Agent."""

    accounts: list[VerificationResult] = []
    content: list[ContentItem] = []


class ProfilerAgent(BaseAgent):
    """Builds a behavioral profile from aggregated content across platforms."""

    name = "profiler"

    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        if not isinstance(agent_input, ProfilerInput):
            return ProfilerOutput(
                target_name=agent_input.target.name,
                agent_name=self.name,
                dimensions={},
            )

        accounts = agent_input.accounts
        content = agent_input.content

        # Step 1: Aggregate all text
        texts: list[str] = []
        timestamps: list[datetime | None] = []
        engagements: list[float] = []
        platforms: list[str] = []

        for acct in accounts:
            if acct.candidate.scraped_data and acct.candidate.scraped_data.bio:
                texts.append(acct.candidate.scraped_data.bio)
                timestamps.append(None)
                engagements.append(1.0)
                platforms.append(acct.candidate.platform)

        for item in content:
            if item.text:
                texts.append(item.text)
                timestamps.append(item.timestamp)
                engagements.append(_engagement_score(item))
                platforms.append(item.platform)

        if not texts:
            return ProfilerOutput(
                target_name=agent_input.target.name,
                agent_name=self.name,
                dimensions={},
            )

        # Step 2: TF-IDF keyword extraction
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=500,
                ngram_range=(1, 2),
            )
            tfidf = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()

            # Sum TF-IDF scores per feature across all documents
            scores = tfidf.sum(axis=0).A1
            top_indices = scores.argsort()[::-1][:_TOP_KEYWORDS]
            top_keywords = [(feature_names[i], float(scores[i])) for i in top_indices]
        except ValueError:
            top_keywords = []

        # Step 3: Activity scoring with recency and engagement weighting
        now = datetime.now(tz=timezone.utc)
        keyword_activity: dict[str, float] = {}
        keyword_evidence: dict[str, list[str]] = defaultdict(list)

        for kw, base_score in top_keywords:
            total = 0.0
            for i, text in enumerate(texts):
                if kw.lower() in text.lower():
                    recency_w = _recency_weight(timestamps[i], now)
                    engagement_w = engagements[i]
                    length_w = _length_weight(text)
                    total += base_score * recency_w * engagement_w * length_w
                    keyword_evidence[kw].append(
                        f"{platforms[i]}: {text[:80]}..."
                        if len(text) > 80
                        else f"{platforms[i]}: {text}"
                    )
            keyword_activity[kw] = total

        # Step 4: Dimension classification
        classifier = DimensionClassifier()
        dimensions: dict[str, list[TopicScore]] = defaultdict(list)

        for kw, activity in keyword_activity.items():
            if activity <= 0:
                continue
            dim = classifier.classify(kw)
            trend = _detect_trend(kw, texts, timestamps)
            dimensions[dim].append(
                TopicScore(
                    topic=kw,
                    score=min(activity, 1.0) if activity <= 1.0 else activity,
                    evidence=keyword_evidence[kw][:5],
                    trend=trend,
                )
            )

        # Sort each dimension by score
        for dim in dimensions:
            dimensions[dim].sort(key=lambda t: t.score, reverse=True)

        # Step 5: Summary stats
        platform_counts = Counter(platforms)
        top_platforms = [p for p, _ in platform_counts.most_common(5)]

        posting_hours = _extract_posting_hours(content)
        estimated_tz = _estimate_timezone(posting_hours)

        return ProfilerOutput(
            target_name=agent_input.target.name,
            agent_name=self.name,
            dimensions=dict(dimensions),
            metadata={
                "top_platforms": top_platforms,
                "estimated_timezone": estimated_tz,
                "posting_frequency": len(content),
                "total_topics_extracted": len(keyword_activity),
            },
        )


def _engagement_score(item: ContentItem) -> float:
    """Compute engagement weighting for a content item."""
    if not item.engagement:
        return 1.0
    total = 0
    for key in ("ups", "stars", "likes", "reactions", "score"):
        val = item.engagement.get(key, 0)
        if isinstance(val, (int, float)):
            total += val
    for key in ("num_comments", "comments", "forks"):
        val = item.engagement.get(key, 0)
        if isinstance(val, (int, float)):
            total += val * 2  # Comments/forks weight higher
    return 1.0 + math.log1p(total) * 0.2


def _recency_weight(ts: datetime | None, now: datetime) -> float:
    """Exponential decay weight based on content age."""
    if ts is None:
        return 0.5  # Unknown time gets moderate weight
    delta_days = (now - ts).total_seconds() / 86400
    if delta_days < 0:
        return 1.0
    return 2.0 ** (-delta_days / _RECENCY_HALF_LIFE_DAYS)


def _length_weight(text: str) -> float:
    """Weight by content length (longer = more substantive)."""
    words = len(text.split())
    if words < 10:
        return 0.5
    if words < 50:
        return 1.0
    if words < 200:
        return 1.5
    return 2.0


def _detect_trend(
    keyword: str,
    texts: list[str],
    timestamps: list[datetime | None],
) -> str:
    """Detect if a topic is rising, declining, or stable over time."""
    dated_mentions: list[datetime] = []
    for text, ts in zip(texts, timestamps):
        if ts and keyword.lower() in text.lower():
            dated_mentions.append(ts)

    if len(dated_mentions) < 2:
        return "stable"

    dated_mentions.sort()
    mid = len(dated_mentions) // 2
    first_half = dated_mentions[:mid]
    second_half = dated_mentions[mid:]

    if len(second_half) > len(first_half) * 1.5:
        return "rising"
    elif len(first_half) > len(second_half) * 1.5:
        return "declining"
    return "stable"


def _extract_posting_hours(content: list[ContentItem]) -> list[int]:
    """Extract UTC hours from content timestamps."""
    hours = []
    for item in content:
        if item.timestamp:
            hours.append(item.timestamp.hour)
    return hours


def _estimate_timezone(posting_hours: list[int]) -> str | None:
    """Estimate timezone from posting hour distribution (peak activity = daytime)."""
    if not posting_hours:
        return None

    hour_counts = Counter(posting_hours)
    if not hour_counts:
        return None

    # Find peak hour
    peak_hour = max(hour_counts, key=hour_counts.get)  # type: ignore[arg-type]

    # Assume peak activity is around 10-14 local time
    # Offset from UTC = peak_hour - 12
    offset = peak_hour - 12
    if offset > 12:
        offset -= 24
    elif offset < -12:
        offset += 24

    sign = "+" if offset >= 0 else "-"
    return f"UTC{sign}{abs(offset)}"
