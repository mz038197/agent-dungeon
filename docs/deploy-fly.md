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
