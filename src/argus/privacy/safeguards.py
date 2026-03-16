"""Privacy safeguards: consent, scope limiting, data minimization."""

from __future__ import annotations

_ETHICS_REMINDER = """
╔══════════════════════════════════════════════════════════════╗
║                    ARGUS OSINT PLATFORM                      ║
╠══════════════════════════════════════════════════════════════╣
║ This tool collects PUBLICLY AVAILABLE information only.      ║
║                                                              ║
║ Before proceeding, ensure you:                               ║
║  • Have legal authorization to investigate this person        ║
║  • Are complying with applicable privacy laws (GDPR, etc.)   ║
║  • Are using this for legitimate purposes (security,         ║
║    journalism, authorized investigations)                    ║
║  • Will handle collected data responsibly                    ║
║                                                              ║
║ Argus does NOT access private data, crack passwords,         ║
║ or circumvent access controls.                               ║
╚══════════════════════════════════════════════════════════════╝
""".strip()


class ConsentChecker:
    """Verify operator has authorized the investigation."""

    def __init__(self, authorized: bool = False, auto_accept: bool = False) -> None:
        self._authorized = authorized
        self._auto_accept = auto_accept

    def check(self) -> bool:
        """Check consent. Returns True if authorized to proceed."""
        if self._authorized or self._auto_accept:
            return True

        print(_ETHICS_REMINDER)
        print()
        try:
            response = input("Do you confirm authorized use? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return response in ("y", "yes")


class ScopeLimiter:
    """Enforce investigation scope limits."""

    def __init__(
        self,
        max_platforms: int | None = None,
        max_content_items: int = 100,
        max_investigation_time: int = 300,
    ) -> None:
        self.max_platforms = max_platforms
        self.max_content_items = max_content_items
        self.max_investigation_time = max_investigation_time

    def limit_platforms(self, platforms: list[str]) -> list[str]:
        """Limit list of platforms to max_platforms."""
        if self.max_platforms is not None:
            return platforms[: self.max_platforms]
        return platforms


class DataMinimizer:
    """Minimize stored data by default."""

    def __init__(self, store_raw: bool = False) -> None:
        self.store_raw = store_raw

    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Truncate text to max_length for storage."""
        if self.store_raw:
            return text
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    def strip_metadata(self, metadata: dict | None) -> dict | None:
        """Remove potentially sensitive fields from metadata."""
        if metadata is None or self.store_raw:
            return metadata
        sensitive_keys = {"ip_address", "email", "phone", "password", "token", "session"}
        return {k: v for k, v in metadata.items() if k.lower() not in sensitive_keys}
