---
name: bio-architect
description: Query and manage personalized bioinformatics data - DNA, bloodwork, supplements, protocols, and derived insights
---

# Bio-Architect

Standalone, self-contained scripts for personalized bioinformatics data.
Each script is independently executable with zero dependencies between scripts.

## Instructions

- **Default to `--json` flag** for all commands when processing data
- **IMPORTANT**: **Don't read scripts unless absolutely needed** - instead, use `<script.py> --help` to understand options and then call the script with `uv run <script.py> <options>` to get the data you need.
- All scripts work from any directory (use absolute paths internally)
- Start with query scripts to read data, use storage scripts to persist knowledge

## Available Scripts

### `cli/databases/dna.py`
**When to use:** Query SNP details, find high-impact genetic variants, list genosets, or explore genes

### `cli/databases/bloodwork.py`
**When to use:** View recent lab results, track biomarker trends over time, or find flagged markers

### `cli/databases/protocol.py`
**When to use:** View current supplement protocol, check protocol history, or list supplements

### `cli/databases/supplements.py`
**When to use:** Query supplement labels and ingredients

### `cli/databases/knowledge.py`
**When to use:** Store and query knowledge entries with tags and links 

## Architecture

- **Self-Contained:** Each script includes all necessary code
- **Emergent Discovery:** Insights grow as more connections are discovered

## Quick Start

All scripts support `--help` and `--json`:

```bash
uv run .claude/skills/bio-architect/scripts/dna.py --help
uv run .claude/skills/bio-architect/scripts/dna.py snp rs1801133 --json
```
