# Agent Dungeon

教室用 **Streamlit + peas-agent-core** 闖關 App，支援 **Google OAuth** 與 **Fly.io** 部署。

## 本機開發

```powershell
cd C:\Users\mz038\Desktop\peas-agent\agent_dungeon
Copy-Item config\local.env.example "$HOME\.agent_dungeon\local.env"
# 編輯 GOOGLE_CLIENT_ID、GOOGLE_CLIENT_SECRET、SESSION_SECRET、PEAS_LLM_API_KEY
uv sync
uv run streamlit run app.py
```

瀏覽器：`http://127.0.0.1:8501/`（請與 `PUBLIC_URL` 一致，建議用 127.0.0.1）

GCP OAuth redirect URI 須包含：`http://127.0.0.1:8501/`

詳見 [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md)。

## 測試

```powershell
uv run pytest
```

## Fly 部署

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1
```

詳見 [`docs/deploy-fly.md`](docs/deploy-fly.md)。
