"""Tests for change detection and monitoring."""

import tempfile
from pathlib import Path

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult, VerificationResult
from argus.watch.monitor import Change, ChangeReport, WatchMonitor, diff_results


def _vr(platform: str, username: str, confidence: float, bio: str = "") -> VerificationResult:
    return VerificationResult(
        candidate=CandidateProfile(
            platform=platform,
            username=username,
            url=f"https://{platform}.com/{username}",
            exists=True,
            scraped_data=ProfileData(username=username, bio=bio) if bio else None,
        ),
        signals=[SignalResult(signal_name="test", score=confidence, weight=1.0, evidence="test")],
        confidence=confidence,
        threshold_label="likely",
    )


class TestDiffResults:
    def test_no_changes(self):
        old = [_vr("github", "johndoe", 0.8)]
        new = [_vr("github", "johndoe", 0.8)]
        report = diff_results(old, new)
        assert not report.has_changes
        assert "No changes" in report.summary

    def test_new_account(self):
        old = [_vr("github", "johndoe", 0.8)]
        new = [_vr("github", "johndoe", 0.8), _vr("reddit", "johndoe", 0.6)]
        report = diff_results(old, new)
        assert report.has_changes
        new_changes = [c for c in report.changes if c.type == "new_account"]
        assert len(new_changes) == 1
        assert new_changes[0].platform == "reddit"

    def test_removed_account(self):
        old = [_vr("github", "johndoe", 0.8), _vr("reddit", "johndoe", 0.6)]
        new = [_vr("github", "johndoe", 0.8)]
        report = diff_results(old, new)
        removed = [c for c in report.changes if c.type == "removed_account"]
        assert len(removed) == 1
        assert removed[0].platform == "reddit"

    def test_confidence_change(self):
        old = [_vr("github", "johndoe", 0.5)]
        new = [_vr("github", "johndoe", 0.9)]
        report = diff_results(old, new)
        conf_changes = [c for c in report.changes if c.type == "confidence_change"]
        assert len(conf_changes) == 1

    def test_small_confidence_change_ignored(self):
        old = [_vr("github", "johndoe", 0.80)]
        new = [_vr("github", "johndoe", 0.82)]
        report = diff_results(old, new)
        conf_changes = [c for c in report.changes if c.type == "confidence_change"]
        assert len(conf_changes) == 0

    def test_bio_change(self):
        old = [_vr("github", "johndoe", 0.8, bio="Software engineer")]
        new = [_vr("github", "johndoe", 0.8, bio="Senior software engineer")]
        report = diff_results(old, new)
        bio_changes = [c for c in report.changes if c.type == "bio_change"]
        assert len(bio_changes) == 1

    def test_summary_text(self):
        old = []
        new = [_vr("github", "johndoe", 0.8), _vr("reddit", "johndoe", 0.6)]
        report = diff_results(old, new)
        assert "2 new account" in report.summary


class TestWatchMonitor:
    def test_save_and_read_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = WatchMonitor(changes_file=Path(tmpdir) / "changes.jsonl")
            report = ChangeReport(
                changes=[Change(type="new_account", platform="github", username="johndoe")],
                summary="1 new account",
            )
            monitor.save_change_report("inv-123", report)
            entries = monitor.read_changes()
            assert len(entries) == 1
            assert entries[0]["investigation_id"] == "inv-123"
            assert entries[0]["summary"] == "1 new account"

    def test_empty_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = WatchMonitor(changes_file=Path(tmpdir) / "changes.jsonl")
            entries = monitor.read_changes()
            assert entries == []
