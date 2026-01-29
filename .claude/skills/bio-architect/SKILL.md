# Bio-Architect

CLI scripts for querying personalized bioinformatics data.
Each script is independently executable.

## Instructions

- **Default to `--json` flag** for all commands when processing data
- **IMPORTANT**: **Don't read scripts unless absolutely needed** - instead, use `<script.py> --help` to understand options and then call the script with `uv run cli/databases/<script.py> <options>` to get the data you need
- All scripts work from the project root directory

## Available Scripts

| Script | Description |
|--------|-------------|
| `bloodwork.py` | Query lab reports, biomarkers, flagged results |
| `dna.py` | Query DNA tests, SNPs, gene data |
| `knowledge.py` | Store and query knowledge entries with tags and links |
| `protocol.py` | Query supplement protocols and schedules |
| `supplements.py` | Query supplement labels and ingredients |

## Quick Start

```bash
# List available commands for any script
uv run cli/databases/bloodwork.py --help

# Query with JSON output
uv run cli/databases/bloodwork.py --json list
uv run cli/databases/dna.py --json high-impact
uv run cli/databases/knowledge.py --json list
```
