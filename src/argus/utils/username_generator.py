"""Username candidate generator for OSINT person resolution."""

import re
import unicodedata

MAX_CANDIDATES = 30

_PREFIXES = ["the", "real"]
_SUFFIXES = ["1", "_"]

_NAME_PARTICLES = {"van", "von", "de", "del", "der", "di", "da", "la", "le", "al", "el", "bin"}


def _normalize(text: str) -> str:
    """Normalize text: remove accents, lowercase, strip special chars."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9\-]", "", ascii_text)
    return ascii_text


def _strip_hyphens(s: str) -> str:
    return s.replace("-", "")


def _split_name_parts(name: str) -> tuple[str, list[str], str]:
    """Split a name into (first, middle_parts, last)."""
    parts = name.split()
    if not parts:
        return ("", [], "")
    if len(parts) == 1:
        return (parts[0], [], "")
    first = parts[0]
    rest = parts[1:]
    last = rest[-1]
    middle = rest[:-1]
    return (first, middle, last)


def generate_username_candidates(
    name: str,
    email: str | None = None,
    username_hint: str | None = None,
) -> list[str]:
    """Generate likely username candidates from a person's name.

    Returns sorted list of unique username candidates, max 30.
    Hints and email usernames appear first.
    """
    name = name.strip()
    if not name:
        return []

    priority: list[str] = []
    generated: list[str] = []

    # Extract email username
    if email and "@" in email:
        email_user = email.split("@")[0].lower()
        if email_user:
            priority.append(email_user)

    # Username hint + variations
    if username_hint:
        hint = username_hint.lower().strip()
        if hint:
            priority.append(hint)
            for suffix in _SUFFIXES:
                priority.append(f"{hint}{suffix}")
            priority.append(f"{hint}1")

    # Normalize name parts
    parts_raw = name.split()
    parts_norm = [_normalize(p) for p in parts_raw if _normalize(p)]

    if not parts_norm:
        return _dedupe_and_limit(priority, generated)

    first_norm, middle_parts, last_norm = _split_name_parts(" ".join(parts_norm))

    if not first_norm:
        return _dedupe_and_limit(priority, generated)

    # Single name (mononym)
    if not last_norm:
        generated.append(first_norm)
        for prefix in _PREFIXES:
            generated.append(f"{prefix}{first_norm}")
        for suffix in _SUFFIXES:
            generated.append(f"{first_norm}{suffix}")
        generated.append(f"{first_norm}1")
        return _dedupe_and_limit(priority, generated)

    # Multi-part name
    all_parts_joined = "".join(parts_norm)
    first_last = f"{first_norm}{last_norm}"

    first_clean = _strip_hyphens(first_norm)
    last_clean = _strip_hyphens(last_norm)
    all_clean = _strip_hyphens(all_parts_joined)
    first_last_clean = f"{first_clean}{last_clean}"

    # Full name concatenated
    generated.append(all_clean)
    if all_parts_joined != all_clean:
        generated.append(all_parts_joined)

    # First + last
    generated.append(first_last_clean)
    if first_last != first_last_clean:
        generated.append(first_last)

    # First initial + last
    generated.append(f"{first_clean[0]}{last_clean}")

    # First + last initial
    generated.append(f"{first_clean}{last_clean[0]}")

    # Separator variants
    generated.append(f"{first_norm}.{last_norm}")
    generated.append(f"{first_norm}_{last_norm}")
    generated.append(f"{first_norm}-{last_norm}")

    # Reversed
    generated.append(f"{last_clean}{first_clean}")
    generated.append(f"{last_norm}.{first_norm}")

    # With particles dropped (e.g. "Jan van der Berg" -> "janberg")
    non_particle_parts = [p for p in parts_norm if p not in _NAME_PARTICLES]
    if len(non_particle_parts) >= 2 and non_particle_parts != [first_norm, last_norm]:
        dropped_first = _strip_hyphens(non_particle_parts[0])
        dropped_last = _strip_hyphens(non_particle_parts[-1])
        dropped_combo = f"{dropped_first}{dropped_last}"
        if dropped_combo != first_last_clean:
            generated.append(dropped_combo)

    # Common suffixes on first+last
    for suffix in _SUFFIXES:
        generated.append(f"{first_last_clean}{suffix}")
    generated.append(f"{first_last_clean}1")

    # Common prefixes
    for prefix in _PREFIXES:
        generated.append(f"{prefix}{first_last_clean}")

    return _dedupe_and_limit(priority, generated)


def _dedupe_and_limit(priority: list[str], generated: list[str]) -> list[str]:
    """Deduplicate and merge priority + generated lists, capped at MAX_CANDIDATES."""
    seen: set[str] = set()
    result: list[str] = []

    for item in priority:
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    for item in generated:
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return result[:MAX_CANDIDATES]
