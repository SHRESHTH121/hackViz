# CERT r4.2 — Exploratory Data Analysis

This README records the EDA findings from the CERT r4.2 behavioral datasets analyzed in the current EDA notebook.

## Dataset Overview

| Dataset | Rows | Columns | Null Values | Duplicate Rows | Unique Users |
|---|---:|---:|---:|---:|---:|
| `logon.csv` | 854,859 | 5 | 0 | 0 | 1,000 |
| `file.csv` | 223,368 | 6 | 0 | 0 | 240 |
| `device.csv` | 405,380 | 5 | 0 | 0 | 265 |
| `email.csv` | 192,177 | 11 | 274,?* | 0 | 1,000 |
| `http.csv` | Not analyzed in the current notebook | — | — | — | — |

\* Email missing values occur in `cc` and `bcc`. The exact column-wise counts are documented below.

---

## 1. Logon Dataset

### Basic Information

- **Rows:** 854,859
- **Columns:** 5
- **Null values:** 0
- **Duplicate rows:** 0
- **Users:** 1,000
- **PCs:** 1,003
- **Unique timestamps:** 338,041

### Columns

| Column | Data Type | Unique Values | Completely Unique? | Description |
|---|---|---:|:---:|---|
| `id` | object | 854,859 | Yes | Unique event identifier |
| `date` | object | 338,041 | No | Event timestamp |
| `user` | object | 1,000 | No | User associated with the event |
| `pc` | object | 1,003 | No | Computer associated with the event |
| `activity` | object | 2 | No | Logon or Logoff activity |

### Most Frequent Values

- Most frequent user: `WPR0368` — 3,470 events
- Most frequent PC: `PC-4124` — 25,514 events
- Most frequent activity: `Logon` — 470,591 events
- Most frequent timestamp: `01/05/2010 08:00:00` — 61 events

---

## 2. File Dataset

### Basic Information

- **Rows:** 223,368
- **Columns:** 6
- **Null values:** 0
- **Duplicate rows:** 0
- **Users:** 240
- **PCs:** 907
- **Unique timestamps:** 216,704

### Columns

| Column | Data Type | Unique Values | Completely Unique? | Description |
|---|---|---:|:---:|---|
| `id` | object | 223,368 | Yes | Unique event identifier |
| `date` | object | 216,704 | No | Event timestamp |
| `user` | object | 240 | No | User associated with the event |
| `pc` | object | 907 | No | Computer associated with the event |
| `filename` | object | 223,368 | Yes | Filename associated with the event |
| `content` | object | 211,871 | No | Content information associated with the file event |

### Most Frequent Values

- Most frequent user: `HSB0196` — 5,380 events
- Most frequent PC: `PC-8001` — 5,380 events
- Most frequent timestamp: `04/14/2010 14:43:32` — 13 events
- Most frequent content value: `FF-D8` — 11,498 events

---

## 3. Device Dataset

### Basic Information

- **Rows:** 405,380
- **Columns:** 5
- **Null values:** 0
- **Duplicate rows:** 0
- **Users:** 265
- **PCs:** 971
- **Unique timestamps:** 399,631

### Columns

| Column | Data Type | Unique Values | Completely Unique? | Description |
|---|---|---:|:---:|---|
| `id` | object | 405,380 | Yes | Unique event identifier |
| `date` | object | 399,631 | No | Event timestamp |
| `user` | object | 265 | No | User associated with the event |
| `pc` | object | 971 | No | Computer associated with the event |
| `activity` | object | 2 | No | Connect or Disconnect activity |

### Most Frequent Values

- Most frequent user: `AJF0370` — 8,502 events
- Most frequent PC: `PC-3640` — 7,801 events
- Most frequent activity: `Connect` — 203,339 events
- Most frequent timestamp: `07/09/2010 09:48:08` — 4 events

---

## 4. Email Dataset

### Basic Information

- **Rows:** 192,177
- **Columns:** 11
- **Null values:** 273,491 across all column cells
- **Duplicate rows:** 0
- **Users:** 1,000
- **PCs:** 1,000
- **Unique timestamps:** 173,260

### Missing Values

| Column | Missing Values | Missing Percentage |
|---|---:|---:|
| `id` | 0 | 0.000% |
| `date` | 0 | 0.000% |
| `user` | 0 | 0.000% |
| `pc` | 0 | 0.000% |
| `to` | 0 | 0.000% |
| `cc` | 112,685 | 58.636% |
| `bcc` | 160,806 | 83.676% |
| `from` | 0 | 0.000% |
| `size` | 0 | 0.000% |
| `attachments` | 0 | 0.000% |
| `content` | 0 | 0.000% |

The missing values are concentrated in `cc` and `bcc`. These fields are not present for many emails.

### Columns

| Column | Data Type | Unique Values | Completely Unique? |
|---|---|---:|:---:|
| `id` | object | 192,177 | Yes |
| `date` | object | 173,260 | No |
| `user` | object | 1,000 | No |
| `pc` | object | 1,000 | No |
| `to` | object | 72,613 | No |
| `cc` | object | 21,723 | No |
| `bcc` | object | 612 | No |
| `from` | object | 1,999 | No |
| `size` | int64 | 42,122 | No |
| `attachments` | int64 | 10 | No |
| `content` | object | 192,177 | Yes |

### Numeric Information

**Email size**

- Mean: 29,962.72
- Standard deviation: 9,985.95
- Minimum: 6,834
- 25th percentile: 22,820
- Median: 28,409
- 75th percentile: 35,414
- Maximum: 106,941

**Attachments**

- Mean: 0.4486
- Standard deviation: 1.1139
- Minimum: 0
- Median: 0
- Maximum: 9

### Most Frequent Values

- Most frequent user: `MSS0001` — 858 emails
- Most frequent PC: `PC-3952` — 858 emails
- Most frequent recipient in `to`: one recipient appears 230 times
- Most frequent `cc` value: one address appears 307 times
- Most frequent `bcc` value: one address appears 374 times
- Most frequent sender in `from`: one sender appears 471 times
- Most frequent date: `01/19/2010 13:04:30` — 14 emails

---

## 5. HTTP Dataset

The current EDA notebook contains an HTTP EDA section, but the execution did not produce HTTP statistics because `HTTP` was not present in the active `DATASETS` configuration. Therefore, no HTTP row count, null count, duplicate count, user count, or unique-value statistics are recorded here.

---

## Overall Observations

- The Logon, File and Device datasets contain **no missing values** and **no duplicate rows** in the analyzed data.
- The Email dataset contains no duplicate rows, but `cc` and `bcc` have substantial missing values.
- Event IDs are completely unique in all four analyzed datasets.
- Timestamps are not completely unique, meaning multiple events can occur at the same timestamp.
- User coverage differs across event sources: Logon and Email contain 1,000 users, while File contains 240 and Device contains 265 users.
- Several fields have very high cardinality, especially filenames, file content, email recipients and email content.
- The EDA statistics in this document are based on the current CERT r4.2 files and the executed EDA notebook.