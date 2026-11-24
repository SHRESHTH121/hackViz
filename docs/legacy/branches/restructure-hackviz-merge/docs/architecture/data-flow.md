# HackViz Data Flow

```text
Raw CERT Sources
      ↓
Source-specific preprocessing
      ↓
Common event schema
      ↓
User-based temporal grouping
      ↓
Chronological user-day event arrays
      ↓
Numerical representations / embeddings
      ↓
Sequence autoencoder
      ↓
Reconstruction-based anomaly score
      ↓
Threshold
      ↓
Alert + explanation
```

Ground-truth labels are kept separate from model inputs and are used for evaluation in the main unsupervised anomaly-detection setup.
