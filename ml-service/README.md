# ML Service

The Python ML service contains the data pipeline and sequence-modeling components of HackViz.

```text
Raw CERT data
    ↓
EDA / data understanding
    ↓
preprocessing
    ↓
event unification
    ↓
temporal-engine
    ↓
representations
    ↓
models
    ↓
training
    ↓
inference
    ↓
explainability
    ↓
evaluation
```

## Modules

- `EDA/` — exploratory analysis and documented dataset findings
- `preprocessing/` — source cleaning, timestamp normalization, feature preparation and event unification
- `temporal-engine/` — user/day chronological behavioral sequences
- `representations/` — numerical event representations and embeddings
- `models/` — LSTM, GRU and Transformer autoencoders
- `training/` — training and transfer-learning workflows
- `inference/` — anomaly scoring and thresholding
- `explainability/` — analyst-facing explanations
- `evaluation/` — model and transfer-learning evaluation
