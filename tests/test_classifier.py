import json
from types import SimpleNamespace

import pytest

from app.classifier import LLMClassifier, RuleBasedClassifier
from app.models import Category, Priority


@pytest.mark.parametrize(
    "title, body, category",
    [
        ("Refund please", "I was charged twice for my subscription", Category.billing),
        ("App crashes", "I get an error every time I open settings", Category.bug),
        ("Cannot log in", "My account is locked after a password reset", Category.account),
        ("Dark mode", "It would be great if you could add a dark theme", Category.feature_request),
        ("Outage", "The whole site is down", Category.bug),
        ("Hello", "Just saying thanks for the service", Category.other),
    ],
)
def test_rule_based_category(title, body, category):
    assert RuleBasedClassifier().classify(title, body).category == category


def test_urgent_words_set_urgent_priority():
    result = RuleBasedClassifier().classify("Outage", "Production down since 9am, data loss possible")
    assert result.priority == Priority.urgent


def test_plain_feedback_is_low_priority():
    result = RuleBasedClassifier().classify("Idea", "Please add an export button")
    assert result.priority == Priority.low


class FakeClient:
    """Mimics the parts of the Anthropic client that LLMClassifier uses."""

    def __init__(self, text=None, error=None):
        self._text, self._error = text, error
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        if self._error:
            raise self._error
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])


def test_llm_classifier_uses_model_answer():
    client = FakeClient(json.dumps({"category": "billing", "priority": "high"}))
    result = LLMClassifier(client=client).classify("Hi", "Something vague")
    assert (result.category, result.priority) == (Category.billing, Priority.high)


def test_llm_classifier_falls_back_on_bad_json():
    client = FakeClient("not json at all")
    result = LLMClassifier(client=client).classify("App crashes", "I get an error on start")
    assert result.category == Category.bug  # came from the rule-based fallback


def test_llm_classifier_falls_back_on_invalid_value():
    client = FakeClient(json.dumps({"category": "spaceship", "priority": "high"}))
    result = LLMClassifier(client=client).classify("Refund", "charged twice")
    assert result.category == Category.billing


def test_llm_classifier_falls_back_on_exception():
    client = FakeClient(error=RuntimeError("network down"))
    result = LLMClassifier(client=client).classify("Cannot log in", "password problem")
    assert result.category == Category.account
