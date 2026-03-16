"""Linker Agent — discovers topic connections across verified accounts."""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from argus.agents.base import BaseAgent
from argus.models.agent import AgentInput, AgentOutput, Connection, LinkerOutput
from argus.models.profile import ContentItem
from argus.models.verification import VerificationResult

# Minimum similarity for a connection to be included
_MIN_SIMILARITY = 0.05


class LinkerInput(AgentInput):
    """Input for the Linker Agent."""

    topic: str
    topic_description: str | None = None
    accounts: list[VerificationResult] = []
    content: list[ContentItem] = []


class LinkerAgent(BaseAgent):
    """Discovers connections between a target's accounts and a given topic."""

    name = "linker"

    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        if not isinstance(agent_input, LinkerInput):
            return LinkerOutput(
                target_name=agent_input.target.name,
                agent_name=self.name,
                connections=[],
            )

        topic = agent_input.topic.lower()
        topic_desc = agent_input.topic_description or agent_input.topic
        accounts = agent_input.accounts
        content = agent_input.content

        connections: list[Connection] = []

        # Step 1: Scan bios for topic mentions
        for acct in accounts:
            profile = acct.candidate.scraped_data
            if profile and profile.bio:
                bio_connections = _find_keyword_connections(
                    text=profile.bio,
                    topic=topic,
                    topic_desc=topic_desc,
                    platform=acct.candidate.platform,
                    source_type="bio",
                )
                connections.extend(bio_connections)

        # Step 2: Scan content for topic mentions and semantic similarity
        for item in content:
            # Keyword matching
            kw_conns = _find_keyword_connections(
                text=item.text,
                topic=topic,
                topic_desc=topic_desc,
                platform=item.platform,
                source_type=item.content_type,
            )
            connections.extend(kw_conns)

        # Step 3: Semantic similarity via TF-IDF across all texts
        all_texts = []
        text_sources: list[tuple[str, str, str]] = []  # (platform, snippet, source_type)

        for acct in accounts:
            profile = acct.candidate.scraped_data
            if profile and profile.bio:
                all_texts.append(profile.bio)
                text_sources.append((acct.candidate.platform, profile.bio, "bio"))

        for item in content:
            if item.text:
                all_texts.append(item.text)
                text_sources.append((item.platform, item.text, item.content_type))

        if all_texts:
            semantic_conns = _semantic_similarity_connections(
                texts=all_texts,
                sources=text_sources,
                topic_desc=topic_desc,
            )
            connections.extend(semantic_conns)

        # Deduplicate by (platform, snippet)
        seen: set[tuple[str, str]] = set()
        unique: list[Connection] = []
        for conn in connections:
            key = (conn.platform, conn.content_snippet[:100])
            if key not in seen:
                seen.add(key)
                unique.append(conn)

        # Sort by confidence descending
        unique.sort(key=lambda c: c.confidence, reverse=True)

        return LinkerOutput(
            target_name=agent_input.target.name,
            agent_name=self.name,
            connections=unique,
        )


def _find_keyword_connections(
    text: str,
    topic: str,
    topic_desc: str,
    platform: str,
    source_type: str,
) -> list[Connection]:
    """Find keyword matches of topic in text."""
    connections: list[Connection] = []
    text_lower = text.lower()
    topic_words = topic.split()

    # Exact topic match
    if topic in text_lower:
        rel_type = _classify_relationship(text_lower, source_type, platform)
        confidence = 0.8 if len(topic_words) > 1 else 0.6
        snippet = _extract_snippet(text, topic, max_len=150)
        connections.append(
            Connection(
                platform=platform,
                content_snippet=snippet,
                relationship_type=rel_type,
                confidence=confidence,
            )
        )
    # Individual word matches (for multi-word topics)
    elif len(topic_words) > 1:
        matches = sum(1 for w in topic_words if w in text_lower)
        if matches >= len(topic_words) * 0.5:
            rel_type = _classify_relationship(text_lower, source_type, platform)
            confidence = 0.3 * (matches / len(topic_words))
            snippet = _extract_snippet(text, topic_words[0], max_len=150)
            connections.append(
                Connection(
                    platform=platform,
                    content_snippet=snippet,
                    relationship_type=rel_type,
                    confidence=min(confidence, 1.0),
                )
            )

    return connections


def _semantic_similarity_connections(
    texts: list[str],
    sources: list[tuple[str, str, str]],
    topic_desc: str,
) -> list[Connection]:
    """Use TF-IDF cosine similarity to find semantically related content."""
    connections: list[Connection] = []

    all_docs = [topic_desc] + texts
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf = vectorizer.fit_transform(all_docs)
    except ValueError:
        return connections

    topic_vec = tfidf[0:1]
    doc_vecs = tfidf[1:]
    similarities = cosine_similarity(topic_vec, doc_vecs).flatten()

    for i, sim in enumerate(similarities):
        if sim >= _MIN_SIMILARITY:
            platform, text, source_type = sources[i]
            snippet = text[:150].strip()
            if len(text) > 150:
                snippet += "..."
            rel_type = _classify_relationship(text.lower(), source_type, platform)
            connections.append(
                Connection(
                    platform=platform,
                    content_snippet=snippet,
                    relationship_type=rel_type,
                    confidence=min(float(sim), 1.0),
                )
            )

    return connections


def _classify_relationship(text: str, source_type: str, platform: str) -> str:
    """Classify the relationship type based on content and source."""
    employment_keywords = {"work at", "employed", "engineer at", "developer at", "role at"}
    contribution_keywords = {"contributed", "pull request", "commit", "merged", "fork"}
    following_keywords = {"follow", "subscribe", "joined"}
    endorsement_keywords = {"recommend", "endorse", "vouch"}

    for kw in employment_keywords:
        if kw in text:
            return "employment"
    for kw in contribution_keywords:
        if kw in text:
            return "contribution"
    for kw in following_keywords:
        if kw in text:
            return "following"
    for kw in endorsement_keywords:
        if kw in text:
            return "endorsement"

    if platform == "github" and source_type == "repo":
        return "contribution"
    if source_type == "bio":
        return "mention"
    return "mention"


def _extract_snippet(text: str, keyword: str, max_len: int = 150) -> str:
    """Extract a snippet around the keyword match."""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return text[:max_len].strip() + ("..." if len(text) > max_len else "")

    start = max(0, idx - 40)
    end = min(len(text), idx + len(keyword) + 60)
    snippet = text[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet[:max_len]
