# HackViz

## Explainable, Transfer-Learning-Enabled Intrusion Detection for Behavioral Anomalies

HackViz is a college software engineering project for UCS503 at Thapar Institute of Engineering and Technology. The system explores behavior-based intrusion detection using unsupervised sequence autoencoders, with a focus on explainability, transfer learning, and reducing cold-start time for new users and systems.

## Problem

Traditional SIEM systems commonly rely on static rules that can miss sophisticated behavioral attacks and generate large numbers of false positives. HackViz models normal activity as sequences of events and identifies sessions whose behavior deviates significantly from learned patterns.

## Approach

The project compares three sequence autoencoder architectures:

1. **LSTM/GRU Autoencoder** — baseline model for local and short-range sequence patterns.
2. **Transformer Autoencoder** — self-attention for long-range dependencies.
3. **Hybrid LSTM + Attention** — combines sequential order modeling with long-range attention.

The primary evaluation dataset is the **CERT Insider Threat Test Dataset**. HDFS/LogHub-style logs may be used only for early pipeline sanity checks because they do not represent the project's primary insider-threat setting.

## Key Ideas

- Unsupervised anomaly detection using reconstruction error
- Explainability through attention and event-level analysis
- Transfer learning to reduce the cold-start requirement
- Human-in-the-loop analyst review rather than automatic blocking
- Empirical comparison of LSTM, Transformer, and hybrid architectures

## Planned Architecture

```text
Enterprise Logs
      |
      v
Spring Boot Backend
  - Ingestion
  - Session Windowing
  - RBAC
  - Audit Logging
      |
      v
Python ML Service
  - Preprocessing
  - LSTM/GRU AE
  - Transformer AE
  - Hybrid AE
  - Anomaly Scoring
  - Explainability
      |
      v
Streamlit Analyst Dashboard
  - Alert Ranking
  - Session Timeline
  - Attention Visualization
  - Confirm / Dismiss Feedback
```

## Evaluation

Primary metric:

- F1-score on held-out CERT test data

Secondary metrics:

- False-positive rate at day 5, 10, and 20
- Transfer learning vs. training from scratch
- Inference latency
- Training time
- Explainability usefulness
- Analyst-perceived clarity

## Project Status

The project has completed the initial requirements/proposal and architecture planning phase. Current development is focused on the data ingestion, preprocessing, session construction, and machine-learning pipeline.

## Important Limitations

Reconstruction error indicates that behavior is unfamiliar; it does not prove that an activity is malicious. Transfer learning reduces cold-start requirements but does not eliminate the need for entity-specific adaptation. The CERT dataset is synthetic and therefore may not perfectly represent real enterprise environments.

## Technology Stack

- Java / Spring Boot
- Python
- PyTorch
- Streamlit
- CERT Insider Threat Dataset

## Repository Structure

```text
hackViz/
├── README.md
├── .gitignore
├── docs/
│   ├── project-proposal/
│   ├── requirements/
│   ├── uml/
│   ├── dfd/
│   ├── progress-report/
│   └── literature-review/
├── backend/
│   └── spring-boot/
├── ml-service/
│   ├── preprocessing/
│   ├── models/
│   ├── training/
│   ├── inference/
│   └── explainability/
├── dashboard/
│   └── streamlit/
├── tests/
└── notebooks/
```

## Disclaimer

HackViz is an academic project and is not intended to replace production security monitoring or incident-response systems.
