# Doc Manager V4

> **The Knowledge Compiler**: Transforming raw notes into trusted intelligence.

## Overview
Doc Manager V4 is a headless AI agent that acts as your dedicated editor. It watches your Obsidian Vault, summarizes your notes (`L1`), and synthesizes them into higher-level insights (`L2`).

## Key Features
- **Zero-UI**: Operates entirely via file system events.
- **Async Processing**: High-throughput queue system for LLM tasks.
- **Shadow Library**: Generates disposable "shadow" copies of knowledge, keeping your sources clean.
- **Human-in-the-Loop**: Integrated review system via `.review.md` files.
- **Obsidian Native**: Optimized for Obsidian's linking and tag system.

## Documentation
- [Architecture Guide](docs/Architecture.md)
- [User Guide](docs/UserGuide.md)
- [Korean Manual](MANUAL_KR.md)

## Quick Start
1. **Configure**: Copy `.env.example` to `.env` and set your API keys.
2. **Run**:
   ```bash
   docker compose up -d
   ```
3. **Use**: Write notes in `01_Sources/`. Watch magic happen in `99_Shadow_Library/`.

## License
MIT
