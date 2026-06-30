#!/bin/sh
set -eu

uv run python -c "from agent_dungeon.core.env_loader import bootstrap_environment; from agent_dungeon.core.bootstrap_config import bootstrap_shared_config; bootstrap_environment(); bootstrap_shared_config()"

exec uv run agent-dungeon \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true
