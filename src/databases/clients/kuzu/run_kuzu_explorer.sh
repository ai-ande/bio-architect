#!/usr/bin/env bash
# Start Kuzu Explorer for the bio-architect knowledge graph

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DB_DIR="$REPO_ROOT/data/databases/kuzu"
DB_FILE="$DB_DIR/bio_graph"

PORT="${1:-8000}"

echo "Starting Kuzu Explorer on http://localhost:$PORT"
echo "Database: $DB_FILE"
echo "Press Ctrl+C to stop"
echo ""

docker run -p "$PORT:8000" \
  -v "$DB_DIR:/database" \
  -e KUZU_FILE=bio_graph \
  --rm kuzudb/explorer:latest
