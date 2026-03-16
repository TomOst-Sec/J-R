"""Tests for batch investigation processing."""

import pytest

from argus.batch import BatchResult, parse_csv, results_to_csv


class TestParseCSV:
    def test_basic_csv(self):
        csv_text = "name,location,email\nJohn Doe,NYC,john@example.com\nJane Smith,LA,"
        targets = parse_csv(csv_text)
        assert len(targets) == 2
        assert targets[0].name == "John Doe"
        assert targets[0].location == "NYC"
        assert targets[0].email == "john@example.com"
        assert targets[1].name == "Jane Smith"
        assert targets[1].email is None

    def test_with_seed_urls(self):
        csv_text = "name,seed_urls\nTest User,https://a.com;https://b.com"
        targets = parse_csv(csv_text)
        assert len(targets) == 1
        assert targets[0].seed_urls == ["https://a.com", "https://b.com"]

    def test_empty_rows_skipped(self):
        csv_text = "name\nJohn\n\nJane"
        targets = parse_csv(csv_text)
        assert len(targets) == 2

    def test_minimal_csv(self):
        csv_text = "name\nAlice"
        targets = parse_csv(csv_text)
        assert len(targets) == 1
        assert targets[0].name == "Alice"

    def test_empty_csv(self):
        csv_text = "name\n"
        targets = parse_csv(csv_text)
        assert targets == []

    def test_all_fields(self):
        csv_text = "name,location,email,username_hint,phone,seed_urls\nTest,NYC,a@b.com,testuser,+1234,https://x.com"
        targets = parse_csv(csv_text)
        assert targets[0].username_hint == "testuser"
        assert targets[0].phone == "+1234"


class TestResultsToCSV:
    def test_basic_output(self):
        results = [
            BatchResult(target_name="John", status="success", accounts_found=3),
            BatchResult(target_name="Jane", status="error", accounts_found=0, error_message="timeout"),
        ]
        csv_out = results_to_csv(results)
        assert "John" in csv_out
        assert "success" in csv_out
        assert "error" in csv_out
        assert "timeout" in csv_out

    def test_empty_results(self):
        csv_out = results_to_csv([])
        assert "target_name" in csv_out  # header still present

    def test_csv_parseable(self):
        import csv
        import io
        results = [BatchResult(target_name="Test", status="success", accounts_found=1)]
        csv_out = results_to_csv(results)
        reader = csv.DictReader(io.StringIO(csv_out))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["target_name"] == "Test"
