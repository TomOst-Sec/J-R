"""Tests for custom scoring models."""

from argus.verification.custom_scoring import (
    BUILTIN_PROFILES,
    ScoringProfile,
    ScoringRule,
    apply_rules,
    get_profile,
    list_profiles,
)


class TestScoringProfile:
    def test_balanced_profile(self):
        p = get_profile("balanced")
        assert p is not None
        assert p.name == "balanced"
        assert p.minimum_threshold == 0.30

    def test_conservative_profile(self):
        p = get_profile("conservative")
        assert p is not None
        assert p.minimum_threshold > 0.50

    def test_aggressive_profile(self):
        p = get_profile("aggressive")
        assert p is not None
        assert p.minimum_threshold < 0.30

    def test_list_profiles(self):
        names = list_profiles()
        assert "balanced" in names
        assert "conservative" in names
        assert "aggressive" in names

    def test_nonexistent_profile(self):
        assert get_profile("nonexistent") is None


class TestScoringRules:
    def test_boost_rule(self):
        rules = [
            ScoringRule(
                name="photo_boost",
                signal_name="photo",
                condition="gt",
                threshold=0.8,
                adjustment=0.1,
            )
        ]
        score = apply_rules(0.5, {"photo": 0.9}, rules)
        assert score == 0.6

    def test_penalty_rule(self):
        rules = [
            ScoringRule(
                name="no_photo_penalty",
                signal_name="photo",
                condition="lt",
                threshold=0.1,
                adjustment=-0.2,
            )
        ]
        score = apply_rules(0.5, {"photo": 0.0}, rules)
        assert score == 0.3

    def test_no_matching_rule(self):
        rules = [
            ScoringRule(
                name="test",
                signal_name="photo",
                condition="gt",
                threshold=0.9,
                adjustment=0.5,
            )
        ]
        score = apply_rules(0.5, {"photo": 0.3}, rules)
        assert score == 0.5

    def test_score_capped_at_bounds(self):
        rules = [
            ScoringRule(name="big_boost", signal_name="x", condition="gt", threshold=0, adjustment=2.0)
        ]
        score = apply_rules(0.5, {"x": 1.0}, rules)
        assert score == 1.0

        rules = [
            ScoringRule(name="big_penalty", signal_name="x", condition="gt", threshold=0, adjustment=-2.0)
        ]
        score = apply_rules(0.5, {"x": 1.0}, rules)
        assert score == 0.0

    def test_multiple_rules(self):
        rules = [
            ScoringRule(name="r1", signal_name="a", condition="gt", threshold=0.5, adjustment=0.1),
            ScoringRule(name="r2", signal_name="b", condition="lt", threshold=0.3, adjustment=-0.05),
        ]
        score = apply_rules(0.5, {"a": 0.8, "b": 0.1}, rules)
        assert abs(score - 0.55) < 0.001

    def test_all_conditions(self):
        assert apply_rules(0.5, {"x": 0.6}, [
            ScoringRule(name="t", signal_name="x", condition="gte", threshold=0.6, adjustment=0.1)
        ]) == 0.6

        assert apply_rules(0.5, {"x": 0.4}, [
            ScoringRule(name="t", signal_name="x", condition="lte", threshold=0.4, adjustment=0.1)
        ]) == 0.6

        assert apply_rules(0.5, {"x": 0.5}, [
            ScoringRule(name="t", signal_name="x", condition="eq", threshold=0.5, adjustment=0.1)
        ]) == 0.6
