"""Tests for batch investigation processing."""

import tempfile
from pathlib import Path

from argus.batch.processor import BatchResult, read_targets_csv


class TestReadTargetsCSV:
    def test_basic_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,location,email\n")
            f.write("John Doe,NYC,john@example.com\n")
            f.write("Jane Doe,LA,jane@example.com\n")
            f.flush()
            targets = read_targets_csv(Path(f.name))
        assert len(targets) == 2
        assert targets[0].name == "John Doe"
        assert targets[0].location == "NYC"
        assert targets[0].email == "john@example.com"
        assert targets[1].name == "Jane Doe"

    def test_name_only_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name\n")
            f.write("Alice\n")
            f.write("Bob\n")
            f.flush()
            targets = read_targets_csv(Path(f.name))
        assert len(targets) == 2

    def test_seed_url_split(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,seed_url\n")
            f.write('John Doe,https://github.com/john;https://twitter.com/john\n')
            f.flush()
            targets = read_targets_csv(Path(f.name))
        assert len(targets[0].seed_urls) == 2

    def test_empty_rows_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,location\n")
            f.write("John,NYC\n")
            f.write(",\n")
            f.write("Jane,LA\n")
            f.flush()
            targets = read_targets_csv(Path(f.name))
        assert len(targets) == 2

    def test_with_username_hint(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,username_hint\n")
            f.write("John Doe,johndoe\n")
            f.flush()
            targets = read_targets_csv(Path(f.name))
        assert targets[0].username_hint == "johndoe"


class TestBatchResult:
    def test_default_values(self):
        result = BatchResult()
        assert result.targets_processed == 0
        assert result.total_accounts == 0
        assert result.errors == []

    def test_accumulation(self):
        result = BatchResult()
        result.targets_processed = 5
        result.total_accounts = 15
        result.errors.append({"target": "Test", "error": "fail"})
        assert result.targets_processed == 5
        assert len(result.errors) == 1
