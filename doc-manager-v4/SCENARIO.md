# Doc Manager V4+: User Scenarios & Story Board

## Core Scenes (Workflows)

### SCENE 1: Introduction of a New Note (L0)
1.  **User**: Writes a new note `01_Sources/MyThoughts.md` (or any subfolder).
    *   Adds `uuid: <seven-uuid>` to the YAML frontmatter.
2.  **Watcher**: Detects `CREATED` event in `01_Sources`.
    *   Calculates hash.
    *   Inserts into DB `documents`.
    *   Pushes job `BUILD_L1(uuid)` to **Queue**.
3.  **Builder**: Pops job.
    *   Loads L0 content.
    *   Selects active `Prompt` for the note's category.
    *   Calls LLM (L1 Generation).
4.  **System**:
    *   Saves L1 to DB (`l1_versions`, `v1`).
    *   Generates Embedding -> DB.
    *   Writes `99_Shadow_Library/L1/MyThoughts.L1.md`.

### SCENE 2: The Review Loop (Human Feedback)
1.  **User**: Opens `99_Shadow_Library/L1/MyThoughts.L1.md` in Obsidian.
    *   Thinks: "This summary misses the point."
2.  **System**: Automatically created a template `MyThoughts.L1.review.md`.
3.  **User**: Edits `MyThoughts.L1.review.md`.
    *   Sets `rating: BAD`.
    *   Sets `decision: REBUILD`.
    *   Adds note: "Focus more on the business implications."
4.  **Watcher**: Detects change in `.review.md`.
    *   Updates `l1_reviews` table.
5.  **Rebuild Trigger**:
    *   System sees `decision: REBUILD`.
    *   Marks L1 `v1` as `SUPERSEDED`.
    *   Pushes job `BUILD_L1(uuid)` to **Queue**.

### SCENE 3: The Rebirth (Rebuild)
1.  **Builder**: Pops job.
    *   Retries generation (possibly with higher temperature or modified prompt if dynamic prompting is enabled).
2.  **System**:
    *   Creates L1 `v2`.
    *   Saves to DB, Embeds, Writes file.
    *   **Crucial**: The `v1` review remains linked to `v1`. `v2` starts with a fresh (empty) review template.
3.  **User**: Checks updated `MyThoughts.L1.md`.
    *   "Perfect."
    *   User sets `v2.review.md` -> `rating: GOOD`, `decision: ACCEPT`.

### SCENE 4: Prompt Evolution (Meta-Learning)
1.  **Analyst (User/System)**: Queries DB for all `BAD` ratings.
2.  **Insight**: Finds 60% of `BAD` reviews contain tag "Missing Business View".
3.  **Action**:
    *   User creates `90_Configuration/Prompts/business_v2.md` (alias).
    *   Tests on a few docs.
    *   Renames to `90_Configuration/Prompts/prompt.md` (Active).
4.  **Effect**:
    *   Future builds use the new prompt.
    *   System quality improves over time.

### SCENE 5: Learning Asset Extraction
1.  **Data Engineer**: Needs a dataset to fine-tune a small local model.
2.  **Action**: Runs `Export Preference Pairs`.
3.  **Output**: `preference_dataset.jsonl`
    ```json
    {
      "prompt": "Summarize this...",
      "chosen": "<Content of L1 v2 (GOOD)>",
      "rejected": "<Content of L1 v1 (BAD)>"
    }
    ```
4.  **Result**: A high-quality, domain-specific dataset created "for free" during daily work.
