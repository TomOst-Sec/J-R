"""Tests for privacy and ethics safeguards."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from argus.privacy.audit import AuditLogger
from argus.privacy.safeguards import ConsentChecker, DataMinimizer, ScopeLimiter


class TestConsentChecker:
    def test_authorized_flag_skips_prompt(self):
        checker = ConsentChecker(authorized=True)
        assert checker.check() is True

    def test_auto_accept_skips_prompt(self):
        checker = ConsentChecker(auto_accept=True)
        assert checker.check() is True

    def test_user_accepts(self):
        checker = ConsentChecker()
        with patch("builtins.input", return_value="y"):
            assert checker.check() is True

    def test_user_accepts_yes(self):
        checker = ConsentChecker()
        with patch("builtins.input", return_value="yes"):
            assert checker.check() is True

    def test_user_declines(self):
        checker = ConsentChecker()
        with patch("builtins.input", return_value="n"):
            assert checker.check() is False

    def test_user_declines_empty(self):
        checker = ConsentChecker()
        with patch("builtins.input", return_value=""):
            assert checker.check() is False

    def test_eof_declines(self):
        checker = ConsentChecker()
        with patch("builtins.input", side_effect=EOFError):
            assert checker.check() is False


class TestScopeLimiter:
    def test_no_limit(self):
        limiter = ScopeLimiter()
        platforms = ["github", "reddit", "twitter"]
        assert limiter.limit_platforms(platforms) == platforms

    def test_limit_platforms(self):
        limiter = ScopeLimiter(max_platforms=2)
        platforms = ["github", "reddit", "twitter", "linkedin"]
        assert limiter.limit_platforms(platforms) == ["github", "reddit"]

    def test_defaults(self):
        limiter = ScopeLimiter()
        assert limiter.max_content_items == 100
        assert limiter.max_investigation_time == 300


class TestDataMinimizer:
    def test_summarize_short_text(self):
        minimizer = DataMinimizer()
        assert minimizer.summarize_text("Hello") == "Hello"

    def test_summarize_long_text(self):
        minimizer = DataMinimizer()
        long = "x" * 300
        result = minimizer.summarize_text(long)
        assert len(result) == 203  # 200 + "..."
        assert result.endswith("...")

    def test_raw_mode_keeps_full_text(self):
        minimizer = DataMinimizer(store_raw=True)
        long = "x" * 300
        assert minimizer.summarize_text(long) == long

    def test_strip_metadata_removes_sensitive(self):
        minimizer = DataMinimizer()
        meta = {"platform": "github", "email": "secret@example.com", "stars": 42}
        result = minimizer.strip_metadata(meta)
        assert "email" not in result
        assert result["platform"] == "github"
        assert result["stars"] == 42

    def test_strip_metadata_raw_mode_keeps_all(self):
        minimizer = DataMinimizer(store_raw=True)
        meta = {"email": "secret@example.com"}
        result = minimizer.strip_metadata(meta)
        assert result == meta

    def test_strip_metadata_none(self):
        minimizer = DataMinimizer()
        assert minimizer.strip_metadata(None) is None


class TestAuditLogger:
    def test_log_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)
            logger.log("investigation_start", platform="github", reason="test")
            entries = logger.read_entries()
            assert len(entries) == 1
            assert entries[0]["action_type"] == "investigation_start"
            assert entries[0]["platform"] == "github"
            assert "timestamp" in entries[0]

    def test_multiple_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)
            logger.log("start")
            logger.log("scrape", platform="reddit")
            logger.log("complete")
            entries = logger.read_entries()
            assert len(entries) == 3

    def test_no_pii_in_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)
            logger.log("scrape", platform="github", operator_id="agent-1")
            raw = log_path.read_text()
            # Should not contain any personal data
            assert "John Doe" not in raw
            assert "agent-1" in raw  # operator ID is fine

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)
            entries = logger.read_entries()
            assert entries == []

    def test_jsonl_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)
            logger.log("test_action")
            raw = log_path.read_text().strip()
            # Should be valid JSON
            data = json.loads(raw)
            assert data["action_type"] == "test_action"
