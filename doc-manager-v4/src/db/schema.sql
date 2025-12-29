-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Documents (L0 Source)
-- "Immutable Source". Only updated when file content changes.
CREATE TABLE IF NOT EXISTS documents (
    uuid UUID PRIMARY KEY,          -- UUID v7 (Time-sortable)
    path TEXT NOT NULL UNIQUE,      -- Relative path from Vault Root (e.g., "01_Sources/Note.md")
    content TEXT NOT NULL,          -- Raw content
    content_hash TEXT NOT NULL,     -- SHA256(content + path)
    category TEXT,                  -- Optional grouping (Personal, Work, etc.)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Prompt Versions
-- "Code as Configuration". Managed by prompt.md files.
CREATE TABLE IF NOT EXISTS prompt_versions (
    prompt_id UUID PRIMARY KEY,
    category TEXT NOT NULL,         -- Links to document category
    content TEXT NOT NULL,          -- The System Prompt
    model_config JSONB NOT NULL,    -- { "model": "llama3", "temperature": 0.7 }
    active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. L1 Versions (Summaries)
-- "Disposable Shadows". Can be rebuilt at any time.
CREATE TABLE IF NOT EXISTS l1_versions (
    l1_id UUID PRIMARY KEY,
    source_uuid UUID REFERENCES documents(uuid),
    version INT NOT NULL,           -- Incremental Version Number
    prompt_id UUID REFERENCES prompt_versions(prompt_id),
    model_id TEXT,                  -- The specific model used (snapshot)
    content TEXT NOT NULL,          -- The AI Summary
    status TEXT CHECK (status IN ('ACTIVE', 'SUPERSEDED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partial index to ensure only one ACTIVE L1 per document
-- (PostgreSQL supports unique indexes with WHERE clauses)
DROP INDEX IF EXISTS idx_unique_active_l1;
CREATE UNIQUE INDEX idx_unique_active_l1 ON l1_versions (source_uuid) WHERE status = 'ACTIVE';


-- 4. L1 Reviews (Human Feedback)
-- "The Asset". Human judgment never deleted.
CREATE TABLE IF NOT EXISTS l1_reviews (
    review_id UUID PRIMARY KEY,
    l1_id UUID REFERENCES l1_versions(l1_id),
    rating TEXT CHECK (rating IN ('PENDING', 'GOOD', 'OK', 'BAD')),
    decision TEXT CHECK (decision IN ('PENDING', 'ACCEPT', 'REBUILD', 'DISCARD')),
    issues TEXT[],                  -- Array of tags: ["Missing Context", "Hallucination"]
    notes TEXT,                     -- Freeform feedback
    reviewer TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. L1 Embeddings (Vector Search)
CREATE TABLE IF NOT EXISTS l1_embeddings (
    l1_id UUID PRIMARY KEY REFERENCES l1_versions(l1_id),
    embedding vector(384)           -- Adjust dimension based on model (all-MiniLM-L6-v2 is 384)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_l1_source ON l1_versions(source_uuid);
CREATE INDEX IF NOT EXISTS idx_l1_status ON l1_versions(status);

-- 6. L2 Versions (Clusters/Insights)
CREATE TABLE IF NOT EXISTS l2_versions (
    l2_id UUID PRIMARY KEY,
    title TEXT,                     -- Generated Title
    content TEXT NOT NULL,          -- The Synthesis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. L2 Members (Mapping L2 -> L1)
CREATE TABLE IF NOT EXISTS l2_members (
    l2_id UUID REFERENCES l2_versions(l2_id),
    l1_id UUID REFERENCES l1_versions(l1_id),
    PRIMARY KEY (l2_id, l1_id)
);

-- 8. L2 Embeddings (Optional, for L2->L3 or Search)
CREATE TABLE IF NOT EXISTS l2_embeddings (
    l2_id UUID PRIMARY KEY REFERENCES l2_versions(l2_id),
    embedding vector(384)
);

