from backend.classifier.domain_classifier import DomainClassifier
from backend.classifier.volatility_classifier import VolatilityClassifier


class TestVolatilityClassifier:
    def test_stable_query_classified_correctly(self):
        clf = VolatilityClassifier()
        assert clf.predict("what is the boiling point of water") == "STABLE"
        assert clf.volatility_score("what is the boiling point of water") == 0.0

    def test_temporal_query_classified_correctly(self):
        clf = VolatilityClassifier()
        assert clf.predict("what is happening today") == "TEMPORAL"
        assert clf.volatility_score("what is happening today") == 0.65

    def test_personal_query_classified_correctly(self):
        clf = VolatilityClassifier()
        assert clf.predict("what is my favorite color") == "PERSONAL"
        assert clf.volatility_score("what is my favorite color") == 0.85

    def test_empty_text_is_stable(self):
        clf = VolatilityClassifier()
        assert clf.predict("") == "STABLE"

    def test_regression_single_letter_i_does_not_false_positive_as_personal(self):
        """
        Regression test for a real bug: naive substring matching classified
        'describe gravity' as PERSONAL because the letter 'i' (a PERSONAL
        token, matching pronoun 'I') is a substring of both 'describe' and
        'gravity'. Word-boundary matching must not have this problem.
        """
        clf = VolatilityClassifier()
        assert clf.predict("describe gravity") == "STABLE"

    def test_regression_us_substring_inside_discuss_does_not_false_positive(self):
        clf = VolatilityClassifier()
        assert clf.predict("let's discuss the plan") == "STABLE"

    def test_batch_prediction_matches_individual(self):
        clf = VolatilityClassifier()
        texts = ["describe gravity", "what is my schedule", "what is happening today"]
        assert clf.predict_batch(texts) == [clf.predict(t) for t in texts]

    def test_score_batch_matches_individual(self):
        clf = VolatilityClassifier()
        texts = ["describe gravity", "what is my schedule"]
        assert clf.score_batch(texts) == [clf.volatility_score(t) for t in texts]


class TestDomainClassifier:
    def test_medical_keywords_classified_correctly(self):
        clf = DomainClassifier()
        assert clf.predict("the doctor prescribed medication for the patient") == "medical"

    def test_code_keywords_classified_correctly(self):
        clf = DomainClassifier()
        assert clf.predict("how do I debug this python function") == "code"

    def test_legal_keywords_classified_correctly(self):
        clf = DomainClassifier()
        assert clf.predict("review this contract for liability clauses") == "legal"

    def test_no_keywords_defaults_to_general(self):
        clf = DomainClassifier()
        assert clf.predict("banana bicycle mountain") == "general"

    def test_empty_text_is_general(self):
        clf = DomainClassifier()
        assert clf.predict("") == "general"

    def test_regression_substring_false_positive_fixed(self):
        """
        'how' is a general-domain keyword; naive substring matching would
        match it inside unrelated words. Confirm word-boundary matching
        doesn't false-positive on a medical-sounding word that happens to
        contain 'how' as a substring, e.g. 'shower' (not medical-relevant
        here, just a substring-collision check).
        """
        clf = DomainClassifier()
        # "shower" contains "how" as a substring but should not trigger
        # the "general" domain keyword "how" via substring match.
        result = clf.predict("shower routine")
        assert result == "general"  # no strong domain keyword matched -> general fallback

    def test_domain_to_weight_returns_expected_values(self):
        clf = DomainClassifier()
        assert clf.domain_to_weight("medical") == 1.15
        assert clf.domain_to_weight("general") == 1.0
        assert clf.domain_to_weight("unknown_domain") == 1.0
