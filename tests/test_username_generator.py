"""Tests for username candidate generator."""

from argus.utils.username_generator import generate_username_candidates


class TestBasicNameGeneration:
    def test_two_part_name_produces_candidates(self):
        results = generate_username_candidates("John Doe")
        assert len(results) > 0
        assert all(isinstance(r, str) for r in results)

    def test_two_part_name_contains_expected_patterns(self):
        results = generate_username_candidates("John Doe")
        assert "johndoe" in results
        assert "jdoe" in results
        assert "johnd" in results
        assert "john.doe" in results
        assert "john_doe" in results
        assert "john-doe" in results
        assert "doejohn" in results
        assert "doe.john" in results

    def test_three_part_name(self):
        results = generate_username_candidates("John Michael Doe")
        assert "johnmichaeldoe" in results
        assert "johndoe" in results
        assert "jdoe" in results

    def test_common_suffixes(self):
        results = generate_username_candidates("John Doe")
        assert "johndoe1" in results
        assert "thejohndoe" in results
        assert "realjohndoe" in results

    def test_no_duplicates(self):
        results = generate_username_candidates("John Doe")
        assert len(results) == len(set(results))

    def test_max_30_candidates(self):
        results = generate_username_candidates("John Michael Doe")
        assert len(results) <= 30

    def test_results_are_lowercase(self):
        results = generate_username_candidates("John DOE")
        for r in results:
            assert r.islower() or any(c.isdigit() for c in r)


class TestEmailAndHintPriority:
    def test_email_username_extracted(self):
        results = generate_username_candidates("John Doe", email="coolj@example.com")
        assert "coolj" in results

    def test_email_username_is_prioritized(self):
        results = generate_username_candidates("John Doe", email="coolj@example.com")
        assert results.index("coolj") < results.index("johndoe")

    def test_username_hint_included(self):
        results = generate_username_candidates("John Doe", username_hint="j_d_hacker")
        assert "j_d_hacker" in results

    def test_username_hint_prioritized(self):
        results = generate_username_candidates("John Doe", username_hint="j_d_hacker")
        assert results.index("j_d_hacker") < results.index("johndoe")

    def test_hint_variations_included(self):
        results = generate_username_candidates("John Doe", username_hint="jdhacker")
        assert "jdhacker" in results
        hint_variants = [r for r in results if "jdhacker" in r and r != "jdhacker"]
        assert len(hint_variants) >= 1


class TestEdgeCases:
    def test_single_name_mononym(self):
        results = generate_username_candidates("Madonna")
        assert "madonna" in results
        assert len(results) > 0
        assert len(results) <= 30

    def test_compound_last_name(self):
        results = generate_username_candidates("Ludwig van Beethoven")
        assert "ludwigvanbeethoven" in results
        assert "ludwigbeethoven" in results

    def test_name_with_apostrophe(self):
        results = generate_username_candidates("Miles O'Brien")
        assert "milesobrien" in results
        assert all("'" not in r for r in results)

    def test_name_with_hyphen_in_surname(self):
        results = generate_username_candidates("Mary Smith-Jones")
        assert "marysmithjones" in results

    def test_accented_characters_normalized(self):
        results = generate_username_candidates("José García")
        assert "josegarcia" in results

    def test_empty_name_returns_empty(self):
        results = generate_username_candidates("")
        assert results == []

    def test_very_long_name_truncated(self):
        long_name = "Alexander Bartholomew Christopher Davidson"
        results = generate_username_candidates(long_name)
        assert len(results) <= 30
        assert all(len(r) <= 50 for r in results)

    def test_al_prefix_name(self):
        results = generate_username_candidates("Ahmed Al-Rashid")
        assert "ahmedalrashid" in results

    def test_van_der_name(self):
        results = generate_username_candidates("Jan van der Berg")
        assert "janvanderberg" in results
        assert "janberg" in results
