# Fly.io 部署

## 事前

- `flyctl auth login`
- 建立 volume：`fly volumes create peas_data --region sin --size 1 --app agent-dungeon`
- GitHub repo secret：`FLY_API_TOKEN`（push 自動 deploy，見下方）

## Secrets

```powershell
Copy-Item config\fly.secrets.env.example "$HOME\.agent_dungeon\fly.secrets.env"
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1
```

套用 secrets（不 deploy）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1 -SecretsOnly
```

## 部署

### 手動

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1
```

`--ha=false` 避免雙機器但只有一個 volume。

### 自動（GitHub Actions）

`git push origin main` → [`.github/workflows/fly-deploy.yml`](../.github/workflows/fly-deploy.yml) → `flyctl deploy`。

一次性設定 deploy token：

```powershell
flyctl tokens create deploy -x 999999h --app agent-dungeon
```

GitHub → repo **Settings → Secrets and variables → Actions** → 新增 `FLY_API_TOKEN`（貼上 token）。

Secrets（OAuth、LLM API key 等）仍在本機改 `%USERPROFILE%\.agent_dungeon\fly.secrets.env` 後跑 `-SecretsOnly`；CI 只負責 deploy 程式碼，不會覆寫 Fly secrets。

## GCP redirect（正式）

```
https://agent-dungeon.fly.dev/
```

與 `fly.toml` 的 `PUBLIC_URL` 一致。

## 學生資料與設定（volume）

持久化目錄：`PEAS_AGENT_HOME=/data/peas-agent`（Fly volume `peas_data`）。

| 路徑 | 用途 |
|------|------|
| `config.json` | **課程 infra**（LLM base URL/model、token_budget、dream…）；Agent 面板 **不**再寫入 reasoning |
| `tts.json` | 僅作 **首次 seed** 來源；各生實際設定在 `users/{google_sub}/tts.json` |
| `users/{google_sub}/preferences.json` | 該生 **推理深度** 等 UI 偏好 |
| `users/{google_sub}/effective_config.json` | 程式 merge 產物；`Agent.create(config_path=…)` 讀取 |
| `users/{google_sub}/workspace/sessions/` | 對話 jsonl |

**首次登入**：若該生尚無 `tts.json` / `preferences.json`，會 **一次性** 從當下共用檔複製 seed，之後只讀寫自己的檔案。

**部署 core 依賴**：本專案 `peas-agent-core` 從 GitHub 安裝。若改動 core API（例如 `Agent.create(config_path=…)`），需先 **push peas-agent-core**，再在 agent_dungeon 執行 `uv lock` 更新 `uv.lock` 後 deploy。
