# User Guide

## Introduction
Doc Manager V4 is an automated system that turns your raw notes into structured knowledge. It works in the background, watching your Obsidian Vault.

## Getting Started

### 1. Installation
Ensure Docker is installed.
```bash
docker compose up -d
```

### 2. Monitoring
- **Dashboard**: http://localhost:8506
- **Logs**: `docker logs -f ross-doc-manager-v4-watcher`

## Workflows

### A. Creating a New Document
1. Create a markdown file in `01_Sources/Category/Title.md`.
2. The system will detect it and generate a summary in `99_Shadow_Library/L1/Category/[L1] Title.md`.
3. **Draft Mode**: To prevent generation, add `draft: true` to the frontmatter.
   ```yaml
   ---
   draft: true
   ---
   ```

### B. Reviewing & Refining
1. Navigate to `99_Shadow_Library/L1/...`.
2. You will see a `[L1] Title.md` (the summary) and `[L1] Title.review.md` (the feedback form).
3. Open the `.review.md` file.
   - Set `rating: BAD` if unsatisfied.
   - Add detailed `issues` or notes.
   - Sets `decision: REBUILD` to trigger a regeneration (future feature).
   - Sets `decision: ACCEPT` to finalize.

### C. Manual Refinement (Shadow Sync)
If you prefer to edit the summary directly:
1. Open the `[L1] Title.md` file.
2. Edit the text as you wish.
3. Save the file.
4. The system detects the manual edit, updates the database, and flags it as `manual_refinement: true`. This preserves your edits as the "Golden Source".

### D. L2 Insights (Clustering)
- The system periodically clusters L1 summaries into L2 Insights.
- You can trigger this manually via the Dashboard.

## Troubleshooting
- **Files not appearing?**
  - Press `Ctrl + R` (Reload App) in Obsidian.
  - Verification: Check Docker logs.
