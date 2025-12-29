# Doc Manager V4+: Technical Master Plan
> **Target Architecture**: UI-less Backend, PostgreSQL + pgvector, Human-in-the-Loop Learning Pipeline

## 1. System Architecture
V4 operates on a **Compiler/Builder pattern** enhanced with a **Feedback Loop**.

### 1.1 Core Components
1.  **The Watcher (Input Monitor)**
    *   **Role**: Detects events in `01_Notes` (L0) and `_Shadow_Library` (Reviews).
    *   **Logic**: Calculates `FileHash`. If changed, updates DB `documents`. If review changed, updates DB `l1_reviews`.
2.  **The Indexer (State of Truth)**
    *   **Engine**: PostgreSQL + pgvector.
    *   **Role**: Stores L0 content, L1 versions, Reviews, and Embeddings.
    *   **Principle**: "DB is the memory; Files are the projection."
3.  **The Builder (AI Engine)**
    *   **Trigger**: Queue-based (triggered by Watcher or Rebuild signal).
    *   **L1 Builder**: Uses LLM (llama.cpp/ollama) to summarize L0.
    *   **L2 Builder**: Clusters L1s using embeddings and summarizes groups.
4.  **The Exporter (Shadow Writer)**
    *   **Role**: Projects DB state to `_Shadow_Library` as Markdown files.
    *   **Rule**: Always creates new versions; never overwrites history blindly.

### 1.2 Tech Stack
*   **Language**: Python 3.10+
*   **Database**: PostgreSQL 16+ with `pgvector` extension
*   **LLM Backend**: `llama.cpp` (server mode) or `ollama` (for VL)
*   **Libraries**: `watchdog`, `psycopg2`, `openai` (client), `streamlit` (monitoring only)

### 1.3 Directory Layout (Obsidian Interface)
```text
/ (Vault Root)
├── 01_Sources/           # [Immutable L0]
│   ├── Personal/
│   ├── Work/
│   └── Assets/
│
├── 90_Configuration/     # [Control Plane]
│   ├── A_Prompts/        # prompt.md (Active), prompt_alias.md
│   └── B_System/         # model_config.json
│
└── 99_Shadow_Library/    # [Disposable Output]
    ├── L1/               # Summaries + Reviews
    └── L2/               # Insights + Reviews
```

## 2. Database Schema (PostgreSQL)

### 2.1 Core Tables
```sql
-- L0 (Source)
CREATE TABLE documents (
    uuid UUID PRIMARY KEY, -- v7
    path TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    hash TEXT NOT NULL,
    updated_at TIMESTAMP
);

-- Prompt Management
CREATE TABLE prompt_versions (
    prompt_id UUID PRIMARY KEY,
    category TEXT,
    content TEXT,
    model_config JSONB, -- { "model": "llama3", "temp": 0.7 }
    active BOOLEAN
);

-- L1 (Summaries)
CREATE TABLE l1_versions (
    l1_id UUID PRIMARY KEY,
    source_uuid UUID REFERENCES documents(uuid),
    version INT,
    prompt_id UUID,
    content TEXT,
    status TEXT CHECK (status IN ('ACTIVE', 'SUPERSEDED')),
    created_at TIMESTAMP
);

-- Reviews (Human Feedback)
CREATE TABLE l1_reviews (
    review_id UUID PRIMARY KEY,
    l1_id UUID REFERENCES l1_versions(l1_id),
    rating TEXT CHECK (rating IN ('GOOD', 'OK', 'BAD')),
    decision TEXT CHECK (decision IN ('ACCEPT', 'REBUILD', 'DISCARD')),
    issues TEXT[],
    notes TEXT
);

-- Embeddings
CREATE TABLE l1_embeddings (
    l1_id UUID REFERENCES l1_versions(l1_id),
    embedding vector(768)
);
```

## 3. Construction Roadmap (Phases)

### Phase 1: Foundation (Infrastructure)
*   [ ] Set up PostgreSQL + pgvector.
*   [ ] Implement `FSWatcher` to sync `documents` table (UPSERT).
*   [ ] Verify UUID v7 generation.

### Phase 2: L1 Pipeline (The Engine)
*   [ ] Implement `PromptLoader` (reads `prompt.md` config).
*   [ ] Connect `LLMClient` (llama.cpp adapter).
*   [ ] Build `L1Builder`: L0 -> LLM -> L1 Version -> DB.
*   [ ] Implement `EmbeddingGenerator` -> `l1_embeddings`.

### Phase 3: Review Loop (Human-in-the-Loop)
*   [ ] Implement `ReviewWatcher` (parses `.review.md`).
*   [ ] Sync reviews to `l1_reviews`.
*   [ ] Implement **Rebuild Logic**:
    *   If `decision == REBUILD`: Mark old `SUPERSEDED`, trigger new Build Job.
    *   New Version inherits context but starts fresh.

### Phase 4: L2 Construction (Intelligence)
*   [ ] Implement Similarity Search (Cosine Similarity > 0.9 / > 0.5).
*   [ ] Build `L2Builder` for Clusters.

### Phase 5: Learning Extraction (The Asset)
*   [ ] Export SFT Dataset (L0 -> Active L1).
*   [ ] Export Preference Pairs (L0 -> Good L1 vs Bad L1).
*   [ ] Prompt Evolution Analysis (Aggregated Issue Tags).
