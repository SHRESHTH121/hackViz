# HackViz

## Explainable User-Centric Insider-Threat Behavioral Anomaly Detection

HackViz is an academic cybersecurity and machine-learning project focused on detecting unusual employee behavior from heterogeneous enterprise activity logs. The project uses the CERT Insider Threat Test Dataset and investigates whether sequence-based deep-learning models can learn normal user behavior and identify anomalous user-day activity.

The central idea is to move from isolated raw log records to a **user-centric temporal representation**:

```text
Raw CERT Events
      ↓
Data Understanding / EDA
      ↓
Preprocessing
      ↓
Event Unification
      ↓
User-Based Temporal Engine
      ↓
Chronological User-Day Event Arrays
      ↓
Numerical Event Representations / Embeddings
      ↓
LSTM / GRU / Transformer Autoencoders
      ↓
Anomaly Score
      ↓
Thresholding
      ↓
Explainable Security Alert
```

## Research Problem

Employees and other authorized users generate large volumes of legitimate activity across authentication, files, removable devices, email and web activity. Static rules can struggle to distinguish unusual behavior from normal variation.

HackViz investigates an unsupervised/normal-behavior approach in which models learn behavioral patterns primarily from normal activity. Ground-truth labels supplied with CERT are reserved for evaluation in the main anomaly-detection experiments rather than turning the entire problem into simple supervised classification.

## What Makes HackViz Different

The project does not claim that LSTM-based anomaly detection, normal-only training, sequence prediction, online adaptation, or workflow diagnosis are individually novel. These ideas have important prior work, including DeepLog.

HackViz instead investigates their application and combination for a different setting:

- **User-centric insider-threat behavior** rather than generic system/application execution logs.
- **Heterogeneous behavioral fusion** across Logon, File, Device, Email and HTTP sources.
- **User-based temporal modeling** that organizes events as chronological behavioral sequences for each user and day.
- **Architecture comparison** between LSTM, GRU and Transformer autoencoders under the same preprocessing and evaluation setup.
- **Transfer learning** across CERT environments/releases to study adaptation with limited behavioral history.
- **Analyst-facing explainability** that identifies influential events/features behind an anomaly score.
- **Security-oriented evaluation** using F1, precision, recall, PR-AUC, FPR, inference latency and training cost.

## Expected ML Pipeline

### 1. Raw Data

The primary benchmark is the CERT Insider Threat Test Dataset. Initial work focuses on CERT r4.2, with r6.2 planned for transfer/generalization experiments.

### 2. Data Understanding and EDA

Each source is examined independently for schema, data types, missing values, duplicate rows, cardinality, timestamp behavior and feature distributions before it is combined with other sources.

### 3. Preprocessing

Source-specific preprocessing will:

- retain behaviorally useful fields;
- remove identifiers or fields that do not contribute useful behavioral information;
- normalize timestamps into a common representation;
- encode categorical variables;
- normalize suitable numerical features;
- process large files in memory-efficient chunks where required.

### 4. Event Unification

Different CERT sources are mapped into a common event representation so that a user's activities can be ordered on the same timeline.

Conceptually:

```text
[event_type, timestamp, user, pc, context/features]
```

### 5. User-Based Temporal Engine

Events are grouped by user and date, then sorted chronologically. The temporal engine produces behavioral sequences rather than treating individual CSV rows as independent observations.

Example:

```text
User: U001
Date: 2026-01-05

[
    [LOGON,        08:55, PC101, ...],
    [FILE_ACCESS,  09:10, PC101, ...],
    [EMAIL,        09:30, PC101, ...],
    [FILE_ACCESS,  10:15, PC101, ...],
    [LOGOFF,       17:05, PC101, ...]
]
```

This is an **event array**, not a natural-language sentence.

### 6. Numerical Representation / Embeddings

Categorical event types and contextual information are converted into numerical representations suitable for neural sequence models. The exact representation will be finalized during implementation and experimentation.

### 7. Sequence Autoencoders

The same processed sequences will be supplied to three model families:

1. **LSTM Autoencoder** — captures ordered sequential dependencies.
2. **GRU Autoencoder** — provides a lighter recurrent alternative.
3. **Transformer Autoencoder** — investigates attention-based modeling of longer-range dependencies.

A hybrid LSTM + attention architecture may also be evaluated where justified by the experiments and implementation scope.

### 8. Anomaly Scoring

For the autoencoder approach, reconstruction behavior will be converted into an anomaly score. A threshold is then used to classify sufficiently unusual sequences as anomalous.

An anomaly score indicates behavioral unfamiliarity; it does not by itself prove malicious intent.

### 9. Explainability

The final system is intended to present analysts with the events and features that contributed to an alert, together with an interpretable user timeline. Attention-based explanations will be used only where the selected architecture provides meaningful attention information.

## Experimental Design

The comparison should keep preprocessing, temporal grouping, sequence construction and evaluation splits consistent across model families.

Planned experiments include:

```text
CERT r4.2
   ├── Train / evaluate model from scratch
   │
   └── Learn transferable behavioral representation
                  ↓
              CERT r6.2
                  ↓
          Fine-tune / evaluate
```

The transfer experiment is intended to measure whether learned behavioral representations reduce adaptation requirements when moving to a different CERT environment with substantially rarer insider-threat activity.

## Evaluation

The primary evaluation will consider:

- F1-score
- Precision
- Recall
- PR-AUC
- False Positive Rate (FPR)
- False Negative Rate (FNR)
- Inference latency
- Training time/cost
- Transfer learning versus training from scratch
- Explainability usefulness/clarity

Because insider-threat data is highly imbalanced, accuracy alone will not be treated as the main measure of success.

## Dataset

HackViz uses the **CERT Insider Threat Test Dataset** from Carnegie Mellon University's Software Engineering Institute.

Official source: https://www.sei.cmu.edu/library/insider-threat-test-dataset/

Official KiltHub record: https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247

The raw CERT releases are several gigabytes in size and are intentionally not stored in this repository. See `Dataset/README.md` for dataset details and the expected local layout.

## Literature Foundation

A major early reference for the project is:

**Min Du, Feifei Li, Guineng Zheng, Vivek Srikumar. "DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning." CCS 2017. DOI: 10.1145/3133956.3134015.**

The paper helped define the boundary between established sequence-based log anomaly detection techniques and the research direction investigated by HackViz. The supplied paper is retained in `docs/DeepLog-research_paper.pdf`.

## Repository Structure

```text
hackViz/
├── README.md
├── .gitignore
│
├── Dataset/
│   └── README.md
│
├── docs/
│   ├── Journal.md
│   ├── DeepLog-research_paper.pdf
│   ├── project-proposal/
│   ├── requirements/
│   ├── literature-review/
│   ├── architecture/
│   └── reports/
│
├── ml-service/
│   ├── README.md
│   ├── EDA/
│   ├── preprocessing/
│   ├── temporal-engine/
│   ├── representations/
│   ├── models/
│   ├── training/
│   ├── inference/
│   ├── explainability/
│   └── evaluation/
│
├── backend/
│   └── spring-boot/
│
├── dashboard/
│   └── streamlit/
│
├── tests/
└── notebooks/
```

The directories are being introduced progressively as implementation begins. Empty directories may contain a `.gitkeep` file so the intended architecture remains visible in GitHub.

## Technology Stack

- Python
- PyTorch
- Java / Spring Boot
- Streamlit
- CERT Insider Threat Test Dataset

## Project Status

Current work is centered on understanding the CERT data, establishing a reproducible preprocessing pipeline, defining the user-based temporal engine and preparing the sequence representation that will be shared by the model experiments.

The model results, transfer-learning results and final explainability claims will be added only after they have been experimentally validated.

## Limitations

- CERT is a synthetic insider-threat benchmark and may not represent every real enterprise environment.
- Anomaly detection identifies unusual behavior, not intent.
- Transfer learning does not eliminate the need for adaptation to a new environment or user population.
- The quality of the system depends strongly on temporal representation, feature selection and evaluation design.

## Academic Disclaimer

HackViz is an academic project. It is intended for research and educational purposes and should not be treated as a replacement for production security monitoring, incident response or organizational security controls.
