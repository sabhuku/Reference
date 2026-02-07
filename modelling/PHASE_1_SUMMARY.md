# Phase 1 Summary Report

**Project:** Automated Reference Classification and Validation  
**Phase:** Stage 1 – Reference Type Classification  
**Status:** Complete and Locked

## 1. Phase 1 Objective
The objective of Phase 1 was to design, implement, and validate a robust reference type classification component as the first stage of a multi-stage academic referencing system.

The classifier is responsible for identifying the reference type (e.g. journal article, book, website) from raw reference strings, and for explicitly handling uncertainty via confidence-based gating. This stage is intended to operate as a safety-critical front gate for downstream processing.

## 2. Scope of Work
Phase 1 focused exclusively on:
- Reference type classification
- Confidence estimation and calibration
- Safety-oriented decision logic

Out of scope for this phase were:
- Structured field extraction
- Reference correction or rewriting
- End-user interface changes

## 3. Data Preparation
### 3.1 Dataset
A gold dataset of 400 references was constructed. 

Reference types included:
- `book`, `journal`, `conference`, `website`, `newspaper`, `thesis`, `ebook`, `image`, `other`

The dataset was:
- Class-balanced
- Manually normalised
- Augmented with adversarial/noisy variants

### 3.2 Data Hygiene
- Label noise was identified and corrected (e.g. `wesite` → `website`)
- The `unknown` label was explicitly removed from training, by design
- `unknown` is treated as a runtime outcome, not a learned class

## 4. Model Architecture
### 4.1 Feature Representation
- Word-level TF-IDF (1–2 grams) for semantic cues
- Character-level TF-IDF (3–5 grams) for formatting patterns
- Feature fusion via `FeatureUnion`

### 4.2 Classifier
- Multinomial Logistic Regression
- Class-weighted to mitigate residual imbalance
- Hyperparameter tuning via `GridSearchCV`

### 4.3 Design Rationale
This architecture was selected to prioritise:
- Determinism
- Explainability
- Auditability
- Low operational risk

## 5. Performance Results
### 5.1 Classification Performance (Test Set)
- **Accuracy:** 93%
- **Weighted F1:** 0.92
- **Macro F1:** 0.86

Errors were limited to semantically adjacent categories (e.g. conference vs journal, newspaper vs website). No high-risk misclassifications were observed.

## 6. Probability Calibration
### 6.1 Motivation
Raw classifier probabilities were found to be rank-correct but poorly calibrated, motivating explicit probability calibration before deployment.

### 6.2 Method
- Platt scaling (sigmoid calibration)
- Implemented using `CalibratedClassifierCV`
- CV-based calibration compliant with modern scikit-learn versions

### 6.3 Calibration Quality
- **Brier score (uncalibrated):** 0.108
- **Brier score (calibrated):** 0.089

This demonstrates a measurable improvement in probability reliability.

## 7. Confidence-Gated Decision Logic
Rather than learning an unknown class, uncertainty is handled explicitly via confidence thresholds.

### 7.1 Threshold Analysis
| Confidence Threshold | Precision | Coverage |
| :--- | :--- | :--- |
| 0.60 | 0.94 | 0.93 |
| 0.65 | 0.96 | 0.86 |
| 0.70 | 0.95 | 0.76 |
| 0.75 | 1.00 | 0.64 |

### 7.2 Operational Setting
- **Selected threshold:** 0.75
- **Rationale:** 
    - Zero false positives
    - Conservative hand-off to downstream stages
    - Explicit fail-closed behaviour

Predictions below threshold are routed as `unknown` for review or alternative handling.

## 8. Safety and Audit Considerations
Phase 1 was designed with safety and governance as first-class concerns:
- No silent failures
- No learned “give-up” class
- Explicit confidence gating
- Deterministic outputs
- Full reproducibility

This design supports:
- Shadow deployment
- Threshold tuning
- Post-hoc audit and explanation

## 9. Phase 1 Outcome
Phase 1 has successfully delivered:
- A production-ready reference type classifier
- Calibrated and interpretable confidence estimates
- A locked and stable Stage 1 component

No further changes to Stage 1 are recommended unless the reference distribution or taxonomy changes.

## 10. Next Phase
Phase 2 will focus on:
- Structured reference field extraction
- Type-specific parsing strategies
- Field-level confidence and validation
- Integration with compliance and remediation logic

Phase 1 provides a stable foundation for this work.
