"""Local NLP intent classification and entity extraction for sales questions."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


class NlpRouter:
    """Classify question intent and extract entities without an external API."""

    def __init__(
        self,
        training_path: str | Path,
        *,
        products: Iterable[str] = (),
        regions: Iterable[str] = (),
        categories: Iterable[str] = (),
    ) -> None:
        training = pd.read_csv(training_path)
        required_columns = {"text", "intent"}
        if not required_columns.issubset(training.columns):
            raise ValueError(f"Training data must contain {sorted(required_columns)}")

        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        strip_accents="unicode",
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                    ),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1_000,
                        random_state=42,
                    ),
                ),
            ]
        )
        self.pipeline.fit(training["text"], training["intent"])
        self.products = self._prepare_vocabulary(products)
        self.regions = self._prepare_vocabulary(regions)
        self.categories = self._prepare_vocabulary(categories)

    @staticmethod
    def _prepare_vocabulary(values: Iterable[str]) -> dict[str, str]:
        return {str(value).casefold(): str(value) for value in values}

    @staticmethod
    def _find_vocabulary_value(text: str, vocabulary: dict[str, str]) -> str | None:
        for normalized, original in sorted(
            vocabulary.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text):
                return original
        return None

    def extract_entities(self, question: str) -> dict[str, int | str]:
        normalized = question.casefold()
        entities: dict[str, int | str] = {}

        today = date.today()
        if re.search(r"\byesterday\b", normalized):
            target = today - timedelta(days=1)
            entities["start_date"] = target.isoformat()
            entities["end_date"] = target.isoformat()
        elif re.search(r"\btoday\b", normalized):
            entities["start_date"] = today.isoformat()
            entities["end_date"] = today.isoformat()
        elif re.search(r"\blast\s+week\b", normalized):
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            entities["start_date"] = start.isoformat()
            entities["end_date"] = end.isoformat()
        elif re.search(r"\blast\s+month\b", normalized):
            end = today.replace(day=1) - timedelta(days=1)
            start = end.replace(day=1)
            entities["start_date"] = start.isoformat()
            entities["end_date"] = end.isoformat()

        year_match = re.search(r"\b(20\d{2})\b", normalized)
        if year_match:
            entities["year"] = int(year_match.group(1))

        top_n_match = re.search(
            r"\b(?:top|best|highest)\s+(\d{1,2})\b", normalized
        )
        if top_n_match:
            entities["top_n"] = max(1, min(int(top_n_match.group(1)), 20))

        region = self._find_vocabulary_value(normalized, self.regions)
        category = self._find_vocabulary_value(normalized, self.categories)
        product = self._find_vocabulary_value(normalized, self.products)
        if region:
            entities["region"] = region
        if category:
            entities["category"] = category
        if product:
            entities["product"] = product

        return entities

    def predict(self, question: str) -> dict[str, object]:
        probabilities = self.pipeline.predict_proba([question])[0]
        classifier = self.pipeline.named_steps["classifier"]
        best_index = int(probabilities.argmax())
        return {
            "intent": str(classifier.classes_[best_index]),
            "confidence": round(float(probabilities[best_index]), 4),
            "entities": self.extract_entities(question),
        }
