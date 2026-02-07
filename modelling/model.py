# ==========================================
# Stage 1 Reference Type Classifier
# CLEAN & PRODUCTION-SAFE
# ==========================================

import pandas as pd
import joblib

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss


# ------------------------------------------
# 1. Load datasets
# ------------------------------------------

train_df = pd.read_csv("stage1_train.csv")
val_df   = pd.read_csv("stage1_val.csv")
test_df  = pd.read_csv("stage1_test.csv")

# ------------------------------------------
# 2. Label normalisation (CRITICAL)
# ------------------------------------------

LABEL_FIXES = {
    "wesite": "website"
}

for df in (train_df, val_df, test_df):
    df["stage_1_label"] = (
        df["stage_1_label"]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace(LABEL_FIXES)
    )

# ------------------------------------------
# 3. REMOVE 'unknown' FROM TRAINING
# ------------------------------------------
# 'unknown' is NOT a class — it is a confidence outcome

train_df = train_df[train_df["stage_1_label"] != "unknown"]
val_df   = val_df[val_df["stage_1_label"] != "unknown"]
test_df  = test_df[test_df["stage_1_label"] != "unknown"]

# ------------------------------------------
# 4. Sanity check (must pass)
# ------------------------------------------

print("Train labels:", sorted(train_df["stage_1_label"].unique()))
print("Val labels:",   sorted(val_df["stage_1_label"].unique()))
print("Test labels:",  sorted(test_df["stage_1_label"].unique()))

# ------------------------------------------
# 5. Split features / labels
# ------------------------------------------

X_train = train_df["raw_reference"]
y_train = train_df["stage_1_label"]

X_val = val_df["raw_reference"]
y_val = val_df["stage_1_label"]

X_test = test_df["raw_reference"]
y_test = test_df["stage_1_label"]

# ------------------------------------------
# 6. Feature extraction
# ------------------------------------------

word_tfidf = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95
)

char_tfidf = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 5),
    min_df=2
)

features = FeatureUnion([
    ("word_tfidf", word_tfidf),
    ("char_tfidf", char_tfidf)
])

# ------------------------------------------
# 7. Classifier
# ------------------------------------------

classifier = LogisticRegression(
    max_iter=3000,
    class_weight="balanced"
)

pipeline = Pipeline([
    ("features", features),
    ("clf", classifier)
])

# ------------------------------------------
# 8. Hyperparameter tuning (lightweight)
# ------------------------------------------

param_grid = {
    "clf__C": [0.5, 1.0, 2.0]
}

grid = GridSearchCV(
    pipeline,
    param_grid,
    cv=3,
    scoring="f1_macro",
    n_jobs=-1,
    verbose=1
)

grid.fit(X_train, y_train)

model = grid.best_estimator_

print("\nBest parameters:")
print(grid.best_params_)

# ------------------------------------------
# 9. Final sanity check (NON-NEGOTIABLE)
# ------------------------------------------

print("\nModel classes:", model.classes_)

# ------------------------------------------
# 10. Validation evaluation
# ------------------------------------------

print("\n=== Validation Set Performance ===")
val_preds = model.predict(X_val)
print(classification_report(y_val, val_preds))

# ------------------------------------------
# 11. Test evaluation
# ------------------------------------------

print("\n=== Test Set Performance ===")
test_preds = model.predict(X_test)
print(classification_report(y_test, test_preds))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, test_preds))

# ------------------------------------------
# 12. Save model
# ------------------------------------------

joblib.dump(model, "stage1_reference_classifier.pkl")
print("\nModel saved as stage1_reference_classifier.pkl")

# ------------------------------------------
# 13. Probability calibration (Platt scaling)
# ------------------------------------------
# ------------------------------------------
# 13. Probability calibration (Platt scaling)
# ------------------------------------------
# ------------------------------------------
# 13. Probability calibration (Platt scaling)
# ------------------------------------------

calibrated_model = CalibratedClassifierCV(
    estimator=pipeline,   # IMPORTANT: use full pipeline
    method="sigmoid",
    cv=5                  # internal CV for calibration
)

calibrated_model.fit(X_train, y_train)

print("\nCalibration complete (CV-based).")


# ------------------------------------------
# 14. Brier score (uncalibrated vs calibrated)
# ------------------------------------------
import numpy as np

# Uncalibrated confidences
uncal_probs = model.predict_proba(X_test)
uncal_conf = np.max(uncal_probs, axis=1)

# Calibrated confidences
cal_probs = calibrated_model.predict_proba(X_test)
cal_conf = np.max(cal_probs, axis=1)

# Correctness labels
y_pred = calibrated_model.predict(X_test)
correct = (y_pred == y_test).astype(int)

# Brier scores
brier_uncal = brier_score_loss(correct, uncal_conf)
brier_cal = brier_score_loss(correct, cal_conf)

print(f"Brier score (uncalibrated): {brier_uncal:.4f}")
print(f"Brier score (calibrated):   {brier_cal:.4f}")

print("\nThreshold analysis:")
thresholds = np.linspace(0.5, 0.9, 9)

for t in thresholds:
    accepted = cal_conf >= t
    precision = correct[accepted].mean() if accepted.any() else 0
    coverage = accepted.mean()

    print(f"Threshold {t:.2f} -> Precision {precision:.2f}, Coverage {coverage:.2f}")

# Step 15 — Threshold analysis (defensible)

print("\nThreshold analysis:")
thresholds = np.linspace(0.5, 0.9, 9)

for t in thresholds:
    accepted = cal_conf >= t
    precision = correct[accepted].mean() if accepted.any() else 0
    coverage = accepted.mean()

    print(f"Threshold {t:.2f} -> Precision {precision:.2f}, Coverage {coverage:.2f}")

# Step 16 — Inference example (FINAL behaviour)
THRESHOLD = 0.75

examples = [
    "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780.",
    "RSPCA (2024) Caring for cats and kittens. Available at: https://www.rspca.org.uk (Accessed: 1 August 2024)."
]

probs = calibrated_model.predict_proba(examples)
labels = calibrated_model.predict(examples)

for ref, label, p in zip(examples, labels, probs):
    confidence = max(p)
    final_label = label if confidence >= THRESHOLD else "unknown"

    print("\nReference:")
    print(ref)
    print(f"Predicted type: {final_label} (confidence: {confidence:.3f})")

# Step 17 — Save calibrated model
joblib.dump(calibrated_model, "stage1_reference_classifier_calibrated.pkl")
print("Calibrated model saved.")