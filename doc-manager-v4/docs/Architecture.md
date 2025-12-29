# Architecture & Technical Reference

## System Overview
Doc Manager V4 is a **Headless Knowledge Compiler** that runs alongside your Obsidian Vault. It uses a file-system watcher to detect changes in your source notes (`01_Sources`), processes them through an LLM pipeline, and outputs structured summaries and insights back into your Vault (`99_Shadow_Library`).

## Core Components

### 1. The Watcher (`watcher.py`)
- **Role**: The sensory organ of the system.
- **Mechanism**: user `watchdog` to listen for `CREATE`, `MODIFY`, `MOVE` events.
- **Async Queue**: To prevent blocking the main thread, all heavy tasks (LLM generation, database writes) are pushed to a thread-safe `Queue`. A background `Worker` thread consumes these tasks sequentially.
- **Debouncing**: Rapid file saves are debounced to prevent duplicate builds.

### 2. The Builders (`l1_builder.py`, `l2_builder.py`)
- **L1 Builder**:
    - Generates summaries for individual documents.
    - Matches source category to specific prompts (e.g., `prompts/coding.md` for `01_Sources/Coding/*`).
    - Creates Shadow Files (`[L1] ...md`) and Review Templates (`.review.md`).
    - **Optimization**: Centralized tag sanitization and Obsidian link generation.
- **L2 Builder**:
    - Synthesizes multiple L1 summaries into higher-level insights.
    - Triggered by scheduled jobs (e.g., Cron) or manual requests via Dashboard.

### 3. Data Layer
- **PostgreSQL + pgvector**:
    - Stores Document versions, L1/L2 summaries, and Vector Embeddings.
    - Tables: `documents`, `l1_versions`, `l1_reviews`, `l2_clusters`.
- **Atomic Operations**: Uses UUIDv7 for time-sortable unique IDs.

### 4. Shadow Library
- **Philosophy**: "Immutable Source, Disposable Shadow".
- **Structure**: Mirrors the source directory structure for easy navigation.
- **Auto-Refresh**: The system aggressively manages file permissions (User 1000) and directory modify times to ensure Obsidian UI updates instantly.

## Data Flow

1. **Input**: User saves `Note.md` in `01_Sources`.
2. **Event**: Watcher detects change -> Pushes `BuildTask` to Queue.
3. **Processing**: Worker picks up task -> Calls `L1Builder`.
4. **Generation**: `L1Builder` fetches prompt -> Calls LLM (llama.cpp) -> Generates Summary & Tags.
5. **Storage**: Summary saved to DB -> Embedding created -> Shadow File written to `99_Shadow_Library`.
6. **Feedback**: User edits `.review.md` -> Watcher detects change -> Updates DB -> Triggers Rebuild if requested.

## Directory Structure
```
/app
├── 01_Sources/          # Read-Only Input
├── 90_Configuration/    # Prompts & Settings
│   ├── Prompts/         # Markdown-based prompts
│   └── prompt_config.md # Category mapping
└── 99_Shadow_Library/   # System Output (Read/Write)
```
