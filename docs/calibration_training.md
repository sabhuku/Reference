# Calibration Training Guide

## Overview
This document explains how to train calibration parameters offline using real production data.

## Why Calibration is Needed

### The Problem: Raw LLM Confidence is Unreliable
- **Overconfidence Bias**: LLMs often return high confidence (0.9+) even when incorrect
- **No Empirical Grounding**: Raw scores reflect the model's internal state, not actual accuracy
- **Tier-1 Risk**: Using raw scores for automation leads to false positives (incorrect auto-applied changes)

### The Solution: Statistical Calibration
- **Empirical Mapping**: Maps raw scores to observed accuracy rates
- **Conservative Adjustment**: Typically lowers overconfident scores
- **Tier-Based Thresholds**: Enables safe automation at higher calibrated confidence levels

## Training Data Format

Collect ground truth labels for AI suggestions:

```json
[
  {
    "raw_confidence": 0.95,
    "was_correct": true,
    "suggestion_id": 123,
    "timestamp": "2024-01-01T00:00:00Z"
  },
  {
    "raw_confidence": 0.87,
    "was_correct": false,
    "suggestion_id": 124,
    "timestamp": "2024-01-01T00:05:00Z"
  },
  ...
]
```

### How to Collect Ground Truth
1. **Shadow Mode**: Run AI suggestions without applying them
2. **Human Review**: Have experts review each suggestion
3. **Label**: Mark as `was_correct: true` if the suggestion was valid, `false` otherwise
4. **Minimum Sample Size**: Collect at least 100 samples per model version

## Method 1: Platt Scaling (Recommended)

Platt scaling fits a logistic regression model to map raw confidence → probability of correctness.

### Formula
```
P(correct) = 1 / (1 + exp(A * raw_confidence + B))
```

### Training Code
```python
from sklearn.linear_model import LogisticRegression
import json
from src.ai_remediation.calibration_service import CalibrationService, CalibrationProfile
from datetime import datetime

# Load training data
with open('training_data.json', 'r') as f:
    training_data = json.load(f)

# Prepare features and labels
X = [[d["raw_confidence"]] for d in training_data]
y = [d["was_correct"] for d in training_data]

# Fit logistic regression
model = LogisticRegression()
model.fit(X, y)

# Extract parameters
A = model.coef_[0][0]
B = model.intercept_[0]

print(f"Platt Scaling Parameters: A={A:.4f}, B={B:.4f}")

# Create calibration profile
profile = CalibrationProfile(
    model_version="gpt-4-2024-01",
    method="platt",
    parameters={"A": A, "B": B},
    created_at=datetime.utcnow().isoformat(),
    sample_size=len(training_data),
    description="Trained on production data (Jan 2024)"
)

# Save profile
service = CalibrationService()
service.save_profile(profile)
print(f"Saved calibration profile: {profile.model_version}")
```

### Validation
Use cross-validation to ensure the model generalizes:

```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"Cross-validation accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")
```

## Method 2: Isotonic Regression (Advanced)

Isotonic regression fits a monotonic step function. Use this if Platt scaling doesn't fit well.

### Training Code
```python
from sklearn.isotonic import IsotonicRegression
import json
from src.ai_remediation.calibration_service import CalibrationService, CalibrationProfile
from datetime import datetime

# Load training data
with open('training_data.json', 'r') as f:
    training_data = json.load(f)

# Prepare features and labels
X = [d["raw_confidence"] for d in training_data]
y = [d["was_correct"] for d in training_data]

# Fit isotonic regression
iso_reg = IsotonicRegression(out_of_bounds='clip')
iso_reg.fit(X, y)

# Create bins from the fitted function
bins = list(zip(iso_reg.X_thresholds_, iso_reg.y_thresholds_))

print(f"Isotonic Regression Bins: {len(bins)} bins")

# Create calibration profile
profile = CalibrationProfile(
    model_version="gpt-4-2024-01",
    method="isotonic",
    parameters={"bins": bins},
    created_at=datetime.utcnow().isoformat(),
    sample_size=len(training_data),
    description="Isotonic regression on production data (Jan 2024)"
)

# Save profile
service = CalibrationService()
service.save_profile(profile)
print(f"Saved calibration profile: {profile.model_version}")
```

## Deployment Workflow

1. **Collect Data**: Run shadow mode for 1-2 weeks, collect at least 100 labeled samples
2. **Train Model**: Use Platt scaling (or isotonic regression if needed)
3. **Validate**: Use cross-validation to ensure generalization
4. **Export Profile**: Save as JSON to `src/ai_remediation/calibration_profiles/{model_version}.json`
5. **Deploy**: Restart application to load new profile
6. **Monitor**: Track calibration deltas (raw vs calibrated) in metrics

## Monitoring Calibration

After deployment, monitor calibration effectiveness:

```python
from src.ai_remediation.metrics import AIMetricsCollector

# Query metrics
metrics = AIMetricsCollector(db_session)
events = metrics.get_events(event_type='suggestion_generated', limit=100)

# Analyze calibration deltas
deltas = [
    e.event_data['raw_confidence'] - e.event_data['calibrated_confidence']
    for e in events
    if 'calibrated_confidence' in e.event_data
]

print(f"Average calibration delta: {sum(deltas) / len(deltas):.3f}")
print(f"Max reduction: {max(deltas):.3f}")
```

## Best Practices

1. **Per-Model Profiles**: Train separate profiles for each model version (gpt-4, gpt-4-turbo, gpt-5)
2. **Regular Retraining**: Retrain every 1-3 months as model behavior evolves
3. **Conservative Default**: Use the default profile (20% reduction) until you have sufficient training data
4. **Fail-Closed**: Never disable calibration for Tier-1 automation
5. **Version Control**: Store calibration profiles in version control alongside code
