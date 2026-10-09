"""Evaluate the local intent classifier on a labelled holdout set."""

from pathlib import Path
import sys

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.nlp_router import NlpRouter


router = NlpRouter(ROOT / "data" / "nlp_training_data.csv")
evaluation = pd.read_csv(ROOT / "data" / "nlp_evaluation_data.csv")
predictions = [router.predict(text)["intent"] for text in evaluation["text"]]

print(f"Accuracy: {accuracy_score(evaluation['intent'], predictions):.3f}")
print("\nClassification report")
print(classification_report(evaluation["intent"], predictions, zero_division=0))
print("Confusion matrix")
labels = sorted(evaluation["intent"].unique())
print(pd.DataFrame(confusion_matrix(evaluation["intent"], predictions, labels=labels), index=labels, columns=labels))
