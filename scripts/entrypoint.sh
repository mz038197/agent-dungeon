#!/bin/sh
set -eu

python -c "from env_loader import bootstrap_environment; from bootstrap_config import bootstrap_shared_config, apply_config_override; bootstrap_environment(); bootstrap_shared_config(); apply_config_override()"

exec uv run streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true
