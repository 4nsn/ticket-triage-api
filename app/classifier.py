"""Ticket classifiers.

Two implementations share one interface (`classify(title, body)`):

* RuleBasedClassifier: deterministic keyword rules. Default, needs no network.
* LLMClassifier: asks an LLM for a category and priority, and falls back to the
  rule-based classifier if the call fails or returns something invalid.
"""
import json
import logging
import os

from .models import Category, Classification, Priority

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    Category.billing: ["invoice", "refund", "charge", "payment", "billing", "subscription"],
    Category.bug: ["error", "crash", "bug", "broken", "not working", "fails", "exception", "outage"],
    Category.account: ["password", "login", "log in", "account", "locked", "2fa"],
    Category.feature_request: ["feature", "would be great", "please add", "suggest", "wish"],
}

URGENT_WORDS = ["outage", "data loss", "security", "breach", "cannot access", "production down"]
HIGH_WORDS = ["crash", "charged twice", "locked", "urgent", "asap", "error"]


class RuleBasedClassifier:
    def classify(self, title: str, body: str) -> Classification:
        text = f"{title} {body}".lower()
        return Classification(
            category=self._category(text),
            priority=self._priority(text),
        )

    @staticmethod
    def _category(text: str) -> Category:
        best, best_score = Category.other, 0
        for category, words in CATEGORY_KEYWORDS.items():
            score = sum(1 for word in words if word in text)
            if score > best_score:
                best, best_score = category, score
        return best

    def _priority(self, text: str) -> Priority:
        if any(word in text for word in URGENT_WORDS):
            return Priority.urgent
        if any(word in text for word in HIGH_WORDS):
            return Priority.high
        category = self._category(text)
        if category in (Category.bug, Category.billing):
            return Priority.medium
        return Priority.low


SYSTEM_PROMPT = (
    "You triage customer support tickets. Reply with JSON only, in the form "
    '{"category": "<billing|bug|account|feature_request|other>", '
    '"priority": "<low|medium|high|urgent>"}.'
)


class LLMClassifier:
    """Classifies tickets with an LLM and falls back to rules on any failure."""

    def __init__(self, client=None, model: str = "claude-sonnet-4-6", fallback=None):
        self._client = client
        self._model = model
        self._fallback = fallback or RuleBasedClassifier()

    def _get_client(self):
        if self._client is None:
            import anthropic  # imported lazily so the package is optional

            self._client = anthropic.Anthropic()
        return self._client

    def classify(self, title: str, body: str) -> Classification:
        try:
            response = self._get_client().messages.create(
                model=self._model,
                max_tokens=100,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Title: {title}\n\n{body}"}],
            )
            data = json.loads(response.content[0].text)
            return Classification(
                category=Category(data["category"]),
                priority=Priority(data["priority"]),
            )
        except Exception as exc:  # any failure must not stop ticket creation
            logger.warning("LLM classification failed, using rules: %s", exc)
            return self._fallback.classify(title, body)


def get_classifier():
    """Pick a classifier from the CLASSIFIER environment variable."""
    if os.getenv("CLASSIFIER", "rules").lower() == "llm":
        return LLMClassifier()
    return RuleBasedClassifier()
