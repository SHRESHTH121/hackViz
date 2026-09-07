# HackViz System Architecture

## High-Level Architecture

```text
CERT / Enterprise Behavioral Logs
                ↓
        Data & Preprocessing Layer
                ↓
         Event Unification Layer
                ↓
       User-Based Temporal Engine
                ↓
    Numerical Event Representation
                ↓
          ML Model Layer
        ┌───────┼────────┐
        ↓       ↓        ↓
      LSTM     GRU   Transformer
        └───────┼────────┘
                ↓
          Anomaly Scoring
                ↓
          Explainability
                ↓
       Analyst-Facing Dashboard
```

The architecture is intentionally modular so that the temporal representation remains consistent while different sequence models are evaluated fairly.

## Core Data Flow

Raw source events are first processed independently. The resulting events are mapped to a common representation, grouped by user and time, ordered chronologically, converted into numerical vectors/embeddings and passed to the selected sequence autoencoder.

The model produces an anomaly score. The score is thresholded and the resulting alert is enriched with the events/features responsible for the unusual behavior before being presented to an analyst.
