# Literature Review

This section records the research references used to define HackViz's problem and research direction.

## DeepLog

**Min Du, Feifei Li, Guineng Zheng, Vivek Srikumar.** "DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning." CCS 2017. DOI: 10.1145/3133956.3134015.

DeepLog is an important reference for sequence-based log anomaly detection and is included in the repository as `docs/DeepLog-research_paper.pdf`.

The paper helped establish which ideas should be treated as prior work rather than claimed individually as HackViz novelty: LSTM-based sequence modeling, normal-only learning, next-log prediction, parameter modeling, online updating and workflow-based diagnosis.

HackViz therefore focuses on the insider-threat behavioral setting, heterogeneous enterprise activity, user-centric temporal representation, model comparison, transfer-learning experiments and analyst-facing explainability.
