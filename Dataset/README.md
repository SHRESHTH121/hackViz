# Datasets

HackViz uses the **CERT Insider Threat Test Dataset** as the primary benchmark for insider-threat and behavioral-anomaly detection.

## Datasets Used

### CERT r4.2

CERT r4.2 is used as the initial training dataset. The model learns general employee behavioral patterns from enterprise activity logs and is evaluated against the malicious-insider ground truth provided with the dataset.

### CERT r6.2

CERT r6.2 is used as a transfer-learning and generalization dataset. After learning behavioral representations from CERT r4.2, the model is transferred and fine-tuned on r6.2 to evaluate its ability to generalize to a different environment with substantially rarer insider-threat activity.

## Planned Experimental Setup

```text
CERT r4.2
    ↓
Data preprocessing
    ↓
Behavioral / temporal feature extraction
    ↓
Model pretraining
    ↓
LSTM / Transformer / Hybrid models
    ↓
Transfer learning
    ↓
CERT r6.2
    ↓
Fine-tuning and evaluation
```

The initial anomaly-detection experiments will primarily learn normal behavioral patterns. The CERT ground-truth answer files are used for evaluation rather than treating the problem as a simple supervised classification task.

## Official Dataset

The official CERT Insider Threat Test Dataset is provided by Carnegie Mellon University's Software Engineering Institute (CMU SEI).

**Official source:** https://www.sei.cmu.edu/library/insider-threat-test-dataset/

**Download repository (CMU KiltHub):** https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247

The raw CERT datasets are **not stored in this GitHub repository** because the official releases are several gigabytes in size. Users should download the required releases directly from the official CMU source and place them in the local data directory described by the project documentation.

## Ground Truth

The CERT `answers` archive provides ground-truth information about the synthetic malicious-insider scenarios. It is used to evaluate anomaly-detection results using metrics such as:

- Precision
- Recall
- F1-score
- PR-AUC
- False Positive Rate (FPR)
- False Negative Rate (FNR)

## Local Dataset Structure

The recommended local structure is:

```text
HackViz/
└── data/
    └── raw/
        ├── cert_r4.2/
        ├── cert_r6.2/
        └── answers/
```

Raw CERT data should remain local and should not be committed to GitHub.
