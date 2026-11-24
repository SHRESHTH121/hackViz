# User-Based Temporal Engine

The temporal engine converts heterogeneous enterprise events into chronological behavioral sequences.

## Intended Representation

```text
User
 └── Date
      └── Ordered Events
```

Each event retains an event type, timestamp, user/PC context and selected source-specific behavioral features.

Example:

```text
[
  [LOGON,       08:55, PC101, ...],
  [FILE_ACCESS, 09:10, PC101, ...],
  [EMAIL,       09:30, PC101, ...],
  [LOGOFF,      17:05, PC101, ...]
]
```

The representation is an event array rather than natural-language text. It will later be converted into numerical vectors or embeddings consumed by the sequence models.

## Design Goals

- preserve chronological order;
- maintain user identity/context during grouping;
- support heterogeneous event sources;
- support variable-length behavioral sequences;
- avoid label leakage into model inputs;
- provide a consistent input format for LSTM, GRU and Transformer experiments.
