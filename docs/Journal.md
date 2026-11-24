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

Our literature search led us to **DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning** by Min Du, Feifei Li, Guineng Zheng and Vivek Srikumar.

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

# Week 5 — Temporal Engine and How to Feed Behaviour to the Model

## Problem Faced

The first major implementation problem was building the temporal engine: deciding how raw events should be grouped and ordered before they are analysed. The same activity can be organised in very different ways — per person, per day, per session, or as a moving window of recent events — and the choice directly affects what the model can and cannot notice.

The problem became sharper once we decided to use a large language model for the assessment. An LLM cannot be given an employee's entire history: on our CPU-only laptops the practical context window is about 4,096 tokens, and every additional event makes inference slower.

## Relevant Context

We considered the main grouping options:

- **Person-wise (full history):** keeps all context for one employee, but is far too long for the model and mixes old and recent behaviour.
- **Day-wise (user-day blocks):** matches the user → day → events plan from Week 2, but fixed day boundaries split sequences that cross midnight, such as a late-evening export session, and say nothing about whether the day was normal for that person.
- **Fixed-size event windows:** easy to compute, but ignore who the person is and what they usually do.

## Key Observation

The grouping must always be **per person**, because the same action means different things for different roles: a developer on GitHub is routine, an intern on an HR salary page is not. Within one person, the model needs two kinds of context at once: a **summary of what is normal for them** and the **recent sequence of events in order**.

## Solution

The temporal engine was designed around three parts:

1. **Behavioural baseline per employee:** a compact summary of their history instead of raw events — observation period, active days, events and downloads per day, event-type distribution, usual working hours (5th–95th percentile in local time), top domains, website categories, removable-media events and external e-mails.
2. **Chronological analysis window:** up to 35 new live events plus up to 15 preceding events for context, each written as one compact line with event ID, local time, source (historical or live), type, domain, path and a few safe details. The event sequence also needs a consistent numerical/token representation so that the Transformer can learn temporal patterns rather than treating the input as an unordered collection.
3. **Incremental batching:** a new analysis is triggered per employee after 5 new events or 90 seconds of inactivity, tracked by a per-employee cursor so that the same events are not analysed twice.

## Outcome

Behaviour is now prepared per person, in chronological order, together with that person's normal pattern. The chronological event windows provide the sequential input for the separately implemented decoder-only Transformer anomaly detector, while the compact employee context and detection evidence are used later by Qwen for explanation. Keeping these stages separate avoids treating the LLM context window as the input mechanism for the detection model.

# Week 6 — Analysing E-mail and File Content

## Problem Faced

The e-mail and file sources raised a separate problem. Detecting suspicious e-mails or documents properly would mean reading their **content**, which would need either a second LLM or a dedicated text-preprocessing and classification pipeline for e-mail bodies and file contents.

## Relevant Context

The Week 3 EDA had already shown that e-mail content, recipients, filenames and file content are high-cardinality text fields. Running an LLM over every e-mail and document is not feasible on our hardware: one model call already takes about a minute or more on the CPU, and the CERT e-mail source alone has 192,177 rows. Reading message and document contents is also highly privacy-sensitive, and a monitoring tool should collect as little as possible.

## Key Observation

Much of the risk signal is available from **metadata** without reading content: who an e-mail is sent to (internal, external or personal mailbox), how many attachments it carries and how large it is, which files are copied and where to, and whether a downloaded file has a sensitive-looking name. A separate content model would add cost and privacy risk for comparatively little benefit at this stage.

## Solution

We chose a metadata-only design:

- E-mails are represented by recipient domain, number of recipients, number of attachments and size — never subject or body.
- File activity is represented by path or filename, activity type (open, write, copy) and destination (for example removable media).
- Rule-based indicators use sensitive-filename keywords (payroll, salary, confidential, customer, export and similar) and personal-mailbox domains to highlight risky combinations, such as a sensitive download followed by file-sharing or personal e-mail activity.
- Content analysis with a separate model was recorded as future work.

## Outcome

E-mail and file behaviour contributes to the assessment without a second model and without reading any content. This also kept the Chrome extension simple and privacy-preserving: it collects only navigation and download metadata.

# Week 7 — Choosing the Right Architecture

## Problem Faced

We had to choose the architecture for detection and for the overall system. The research plan from Week 2 proposed LSTM, GRU and Transformer-based sequence models, but each option had different trade-offs in implementation time, training data, hardware and — most importantly for analysts — explainability. We ultimately implemented a separate decoder-only Transformer for anomaly detection from scratch, rather than relying on Qwen or another pretrained language model to detect anomalies.

## Relevant Context

- **A sequence model trained from scratch** can learn temporal patterns in employee activity and provide a detection signal, but it requires us to design the event representation, sequence construction, model architecture, training objective and anomaly-scoring procedure ourselves. Unlike using a pretrained model, there are no learned weights to reuse, so the model must learn useful patterns from the available behavioural data.
- **Rule-based indicators** are transparent and useful as supporting signals, but are brittle on their own and cannot flexibly learn temporal relationships across events.
- **Qwen2.5-3B-Instruct**, used separately as a local explainability model, can interpret the detector's output in the context of role and history and explain it in plain language, but it can be inconsistent or invent evidence if its output is not checked.

The system also had to run fully locally on a 16 GB CPU-only laptop, with no cloud APIs.

## Key Observation

The key architectural decision was to separate **detection** from **explainability**. The decoder-only Transformer is responsible for learning behavioural sequences and identifying anomalies; Qwen is responsible for converting the detector's result and supporting context into an analyst-readable explanation. This avoids conflating a generative LLM's explanation with the model that actually detects anomalous activity.

## Solution

We implemented a two-model analysis pipeline, with rule-based indicators as supporting signals:

- **Anomaly detection:** a decoder-only Transformer architecture was implemented from scratch and trained for sequential employee-behaviour anomaly detection. It is a separate detection model; it is not Qwen and does not depend on Qwen to produce its anomaly signal.
- **Explainability:** Qwen2.5-3B-Instruct runs locally through Ollama and receives the detection result, relevant activity evidence and employee context to generate a human-readable explanation and recommended action. Qwen is not the anomaly detector.
- **Reliability:** the explanation stage must return a strict JSON structure (anomaly flag, risk level, confidence, reason, evidence event IDs, recommended action), which is validated before anything is saved. Evidence is checked against the supplied activity records.
- **System:** Chrome Manifest V3 extension → FastAPI backend → PostgreSQL → background analysis worker → decoder-only Transformer detection → Qwen via Ollama for explanation → React dashboard.

The earlier LSTM/GRU comparison remained outside the implemented pipeline; the Transformer was the sequence architecture carried forward.

## Outcome

The architecture was fixed as two distinct model stages. The decoder-only Transformer had been implemented for anomaly detection, while Qwen remained the local language model for explaining the resulting alerts. This corrected the earlier plan: Transformer implementation was no longer future work.

# Week 8 — Getting Users for Mock Demo Data

## Problem Faced

To demonstrate and test the system we needed realistic employee activity, both historical and live. We could not monitor real employees, and it was difficult to find people to act as users and generate enough varied demo data across different roles.

## Relevant Context

The full CERT releases are large, are not live, and do not match the browser-activity format collected by our extension. A meaningful demonstration needed several roles with a history of normal behaviour, plus some behaviour an investigator might want to look at — without inventing alerts.

## Key Observation

The historical data and the live data could be solved separately: historical behaviour could be generated synthetically and reproducibly, while live activity only needs whoever is presenting to browse normally with the extension paired to an employee.

## Solution

- **Synthetic historical dataset:** a seeded generator creates 10 fictional employees in different roles (HR, two developers, finance, management intern, project manager, system administrator, data analyst, sales, research intern) with 4,891 CERT-style events across 8 event types. It is byte-for-byte reproducible from seed 42. Some employees behave in ways worth reviewing — for example an evening of restricted-file exports followed by a file-sharing visit — but **no event is labelled** and no alert is pre-generated.
- **Live demo users:** any team member can act as an employee by pairing the Chrome extension after confirming a monitoring notice; the dashboard also allows adding new employees.
- **Automated browsing for tests:** an end-to-end script drives a real Chrome browser with the extension installed to generate genuine browsing and download activity.

## Outcome

The demo no longer depends on recruiting outside users. It starts from 10 fictional employees with a realistic history, and live activity comes from real browsing during the demonstration.

# Week 9 — Implementation and Environment Problems

## Problem Faced

Building the backend and integrating the two-model pipeline exposed several practical problems:

- Implementing a Transformer from scratch was substantially more involved than loading a pretrained model. We had to make the event representation and sequence preparation consistent with the model, define how chronological context is presented, and implement the decoder-only architecture and its training path rather than relying on pretrained weights.
- Training the Transformer was a separate challenge from writing its architecture. The model had to learn useful patterns from employee activity sequences, while the data was heterogeneous, highly imbalanced and constrained by the available normal-behaviour examples. Sequence length, batching, training time and CPU memory/compute limits all affected the practical training process. A model that runs forward successfully is not necessarily a model that has learned a useful anomaly signal, so training behaviour and resulting scores needed to be inspected rather than assuming implementation meant successful learning.
- Windows Smart App Control blocked the unsigned DLLs of a portable PostgreSQL build, so the database could not initialise.
- The Qwen model download repeatedly stalled because of connection resets.
- Qwen sometimes cited event IDs that were not part of the supplied data, and its explanation had to be reliable enough to store.
- A failed or timed-out analysis must not cause events to be skipped.

## Relevant Context

PostgreSQL was mandatory for the project (no SQLite fallback). All inference runs on the CPU, so a single analysis takes about a minute or more, and it must never block event collection.

## Key Observation

The two model stages have different failure modes and must be treated separately. The Transformer needs a sound training process and a meaningful detection signal; Qwen's generated explanation cannot simply be trusted, so every field has to be checked and every piece of evidence must point to a real activity record. Long inference also means analysis has to run in the background.

## Solution

- Implemented the decoder-only Transformer as a separate detection component rather than treating Qwen as the detector. The from-scratch implementation required the event-to-sequence preparation and model training workflow to be developed alongside the architecture. Training was constrained by the size and imbalance of behavioural data and by CPU-only compute, making sequence length, batch sizing and training duration practical considerations. The detector's output is kept distinct from the explanation generated by Qwen.
- Installed the official, code-signed PostgreSQL 16 installer instead of the portable build; resumed the Qwen model download until it completed.
- Ollama is called with a JSON schema and low temperature. Responses are validated (risk level, confidence range, consistency between anomaly flag and risk level); evidence IDs not in the supplied records are removed and recorded, and an anomaly without valid evidence is rejected, with one corrective retry.
- A single background worker runs analyses; the assessment and the cursor update are saved in one database transaction, so after any failure the same events are retried later instead of being skipped.

## Outcome

Events are ingested immediately, analysis runs in the background, and every saved alert is schema-valid and cites only real events.

# Week 10 — Evaluating Performance

## Problem Faced

Evaluating the system was difficult. There was no labelled ground truth for live browser activity, the model's answers are not perfectly deterministic, and its confidence value is not a calibrated probability, so standard accuracy metrics could not be computed meaningfully. We also needed to know whether analysis was fast enough on a CPU.

## Relevant Context

The system has several layers that can fail independently: data validation, storage, the extension, Transformer-based detection, Qwen explainability and the dashboard. The detection model and the explanation model require different forms of evaluation: the former must be assessed on its anomaly-detection behaviour, while the latter must be checked for faithful, evidence-grounded explanations.

## Key Observation

Evaluation had to be split into three parts: **correctness** of the system (automated tests), **quality** of the assessments (role-aware scenarios with known intent, checked by reading the model's real output), and **performance** (measured analysis time).

## Solution

- 54 automated tests: validation and evidence checks, indicators, API and database behaviour, dataset reproducibility, and 9 tests that run real inference with the model.
- A 27-step end-to-end test with a real Chrome browser and the extension, plus 8 dashboard checks.
- Scenario tests revealed a real weakness: with the first prompt, the model rated a finance analyst downloading payroll, bank-account and salary files and then visiting wetransfer.com as **low** risk (confidence 0.95). Adding a short rubric defining low, medium and high risk — without overriding the model's answer — changed this to **high** (0.85), while normal developer browsing stayed **low** (0.95) and a management intern browsing HR salary pages was rated **medium** (0.75).
- Analysis time was measured at 60.7–134.2 seconds per assessment on the CPU.

## Outcome

All automated tests passed (54/54, 27/27 and 8/8). Detection precision and recall for the implemented Transformer on the official labelled CERT benchmark have not yet been measured; this remains future work. Passing integration tests demonstrates that the pipeline runs, not that the detector has achieved a particular benchmark accuracy.

# Week 11 — Integration, Testing and Documentation

## Problem Faced

The final week was spent integrating the components and fixing problems found during testing:

- Current versions of Chrome no longer accept the `--load-extension` flag, so the extension could not be loaded for automated testing in the usual way.
- Role matching used plain keyword search, so short keywords such as "hr" matched inside unrelated words, and developers were treated as expected users of identity-administration portals.
- Dashboard issues: status indicators showed red before the first status check, charts were drawn mid-animation, and the profile chart showed live events in the historical colour.
- The repository still contained the old pipeline skeleton and several outdated branches.

## Relevant Context

The project had to be demonstrable end to end: open the dashboard, pair the extension, browse, and receive a real model assessment with evidence.

## Key Observation

Most of the remaining issues only appeared when the whole system ran together with real data and a real browser, which made the end-to-end test essential.

## Solution

- The end-to-end test loads the extension through Chrome's DevTools pipe.
- Role matching uses whole words, and IT administration was separated from cloud consoles.
- Dashboard fixes: neutral status until the first check, animations disabled, and activity charts split by source.
- The repository was restructured: the new application replaced the old skeleton, all earlier documentation was preserved under `docs/` (including `docs/legacy/`), and outdated branches were removed after their unique documentation was saved.
- README, technical guide and test results were written.

## Outcome

The complete workflow runs end to end on a CPU-only laptop, and data persists across a backend restart.

# Remaining Work

The following items are still planned and are not yet implemented:

- Further refinement and systematic evaluation of the implemented decoder-only Transformer detector, including controlled comparisons with LSTM and GRU baselines
- Preprocessing and evaluation on the official CERT r4.2 benchmark, and r4.2 → r6.2 transfer-learning experiments
- Precision, recall, PR-AUC and false-positive-rate evaluation against labelled insider scenarios
- Content analysis of e-mails and files with a separate model, if privacy requirements allow
- Authentication and access control for analysts, and deployment beyond a single machine
