# HackViz Project Journal

This journal records the development of HackViz chronologically. Each week separates the problem encountered, relevant context, key observations, the solution or decision made, and the resulting outcome. Planned work is not described as completed work.

# Week 1 — Project Setup and Finding a Suitable Dataset

## Problem Faced

At the beginning of the project, the first challenge was deciding what type of cybersecurity problem HackViz should address and finding a dataset that actually represented that problem. Several commonly used cybersecurity and log datasets were oriented toward system or application logs rather than detailed employee behavior.

We needed behavioral information such as logins, file activity, removable-device activity, email and web activity, together with a meaningful user identity and ground truth for malicious behavior. Finding all of these characteristics in one suitable dataset was difficult.

We also initially experimented with a custom synthetic dataset based on CERT-style behavior. This helped us understand the required schemas and pipeline, but we recognized that a stronger project benchmark should use the original CERT benchmark rather than relying on our own reconstruction.

## Relevant Context

The search led us to the **CERT Insider Threat Test Dataset** provided by Carnegie Mellon University's Software Engineering Institute. CERT contains multiple behavioral sources associated with users and malicious-insider scenarios.

The official source and KiltHub record were identified as the primary dataset references. We also encountered practical download/access issues while trying to obtain the large CERT releases. The answers archive was obtained successfully, while the large r4.2 release required additional download troubleshooting.

## Key Observation

The important change in direction was realizing that HackViz should not be described as a generic network intrusion detector. The project is better framed as **user-centric insider-threat behavioral anomaly detection**, because the data represents activity by authorized users and the research question concerns deviations from normal employee behavior.

## Solution

CERT r4.2 was selected as the initial primary benchmark. The project documentation was updated to distinguish the official CERT benchmark from our earlier CERT-inspired synthetic data.

We also decided that the raw CERT releases should remain outside GitHub because of their large size. Dataset documentation would instead describe the required releases, local structure and source information.

## Outcome

By the end of Week 1, the project had a clearer problem definition and a suitable benchmark direction. The next major question became novelty: simply applying an LSTM or autoencoder to sequential data would not be enough.

# Week 2 — Novelty Requirement and DeepLog Literature Review

## Problem Faced

During the early project discussion, our professor emphasized that the project needed a meaningful contribution rather than simply applying an existing deep-learning model to a dataset. This created a second problem: we needed to understand what had already been done in sequence-based anomaly detection before deciding what HackViz could contribute.

Our literature search led to **DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning** by Min Du, Feifei Li, Guineng Zheng and Vivek Srikumar.

The paper changed our understanding of the problem because it already demonstrated LSTM-based sequential anomaly detection, normal-only training, next-log-key prediction, parameter modeling, online updates and workflow-based diagnosis.

## Relevant Context

We reviewed the DeepLog paper carefully rather than treating it as a superficial reference. DeepLog learns normal execution patterns from system logs, predicts the next log key from recent history, models parameter values and supports diagnosis and online updating.

This established an important boundary for HackViz: LSTM sequence modeling, normal-only training, timestamps/parameters, online adaptation and workflow diagnosis should not be presented individually as novel contributions.

## Key Observation

The potential contribution had to come from the **problem setting, data representation, experimental design and analyst-facing output**, rather than from simply selecting a deep-learning model.

We identified several directions worth investigating:

- user-centric employee behavior instead of generic system/application execution paths;
- heterogeneous behavioral fusion across Logon, File, Device, Email and HTTP sources;
- user-based temporal sequences;
- comparison of LSTM, GRU and Transformer architectures;
- transfer learning across different CERT environments/releases;
- event/feature-level explanations for security analysts;
- evaluation using security-oriented metrics such as F1, PR-AUC and FPR.

## Solution

HackViz was therefore positioned as an **explainable and transferable user-centric insider-threat behavioral anomaly detection system**.

The planned research pipeline became:

```text
CERT Events
    ↓
Preprocessing
    ↓
Event Unification
    ↓
User → Day → Chronological Events
    ↓
Numerical Event Representations / Embeddings
    ↓
LSTM / GRU / Transformer Autoencoders
    ↓
Anomaly Score
    ↓
Explainable Alert
```

## Outcome

The project moved from the general idea of "build an anomaly detector" to a more defensible research direction. DeepLog became an important baseline for defining what HackViz would not claim as new and where our experiments could instead add value.

# Week 3 — CERT Exploratory Data Analysis

## Problem Faced

Once the CERT r4.2 data was selected, the next challenge was understanding the actual raw files before designing preprocessing. The different event sources have different schemas, feature types, cardinalities and coverage across users.

Loading and inspecting large event files also required care because the complete dataset is too large to treat as one ordinary in-memory table.

## Relevant Context

The initial EDA examined Logon, File, Device and Email data. HTTP was included in the notebook design, but the current notebook execution did not produce HTTP statistics because the active dataset configuration did not contain the HTTP entry. Therefore, no HTTP statistics were recorded as completed EDA results.

The main observed dataset sizes were:

| Source | Rows | Columns | Users | Duplicate Rows |
|---|---:|---:|---:|---:|
| Logon | 854,859 | 5 | 1,000 | 0 |
| File | 223,368 | 6 | 240 | 0 |
| Device | 405,380 | 5 | 265 | 0 |
| Email | 192,177 | 11 | 1,000 | 0 |

The EDA also showed that Logon, File and Device had no missing values, while Email had missing values concentrated in `cc` and `bcc`.

## Key Observation

The sources cannot simply be concatenated because they do not share the same schema. They need to be understood separately first and then mapped into a common event representation.

Another important observation was the high cardinality of fields such as filenames, file content, email recipients and email content. These fields require deliberate representation choices rather than blindly one-hot encoding every value.

## Solution

The EDA work was documented under `ml-service/EDA/`. The project direction became to perform source-specific cleaning and feature selection before event unification.

## Outcome

We established a factual baseline of the CERT r4.2 files being analyzed and identified the main preprocessing concerns: heterogeneous schemas, high-cardinality categorical information, missing email recipient fields and the scale of the raw data.

# Week 4 — Preprocessing and Event Unification Design

## Problem Faced

The raw sources represent different kinds of activity. A model cannot directly consume the original CSV rows from all sources because their fields and event semantics differ.

## Relevant Context

The pipeline needs a common representation while retaining the behavioral information that distinguishes event types. Timestamp information is particularly important because the eventual model input is intended to preserve behavioral order.

## Key Observation

The preprocessing layer should not attempt to make all source files identical at the raw-column level. Instead, each source should be transformed into a common event schema containing the fields needed for temporal modeling.

## Solution

The planned unified event representation is conceptually:

```text
[event_type, timestamp, user, pc, context/features]
```

Source-specific preprocessing will remove irrelevant fields, normalize timestamps, encode categorical information and normalize suitable numerical features. Large files will be processed in chunks where required.

## Outcome

The preprocessing design now provides a clear interface between raw CERT data and the temporal engine. Implementation of this layer is the next development stage rather than a result that is assumed to be complete.

# Week 5 — User-Based Temporal Engine Design

## Problem Faced

Raw logs are individual events, but the anomaly detector needs to understand behavior over time. Treating each row independently would lose the relationships between actions performed by the same user during a day.

## Relevant Context

HackViz therefore organizes activity around the user and chronological time. The intended primary unit is a user-day behavioral sequence, with sessionization available where it improves the representation.

## Key Observation

The temporal engine is the bridge between heterogeneous event processing and sequence modeling. It must preserve event order and retain enough context for downstream models without converting the data into natural-language text.

## Solution

The intended structure is:

```text
User → Date → Chronologically ordered events
```

For example:

```text
U001 / 2026-01-05
[
    [LOGON,       08:55, PC101, ...],
    [FILE_ACCESS, 09:10, PC101, ...],
    [EMAIL,       09:30, PC101, ...],
    [FILE_ACCESS, 10:15, PC101, ...],
    [LOGOFF,      17:05, PC101, ...]
]
```

This is an event array, not a sentence.

## Outcome

The temporal-engine design establishes the intended model input: chronological behavioral arrays for individual users rather than isolated records.

# Future Development Weeks

The following stages are intentionally recorded as planned work until implementation and experiments are completed:

- Event representation and embeddings
- LSTM and GRU autoencoder implementation
- Transformer autoencoder implementation
- Training and validation strategy
- Explainability layer
- CERT r4.2 baseline experiments
- CERT r4.2 → r6.2 transfer-learning experiments
- Model comparison
- Security-oriented evaluation
- Backend integration
- Streamlit analyst dashboard
- Final testing and documentation
