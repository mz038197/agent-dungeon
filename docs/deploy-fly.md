# Fly.io 部署

## 事前

- `flyctl auth login`
- 建立 volume：`fly volumes create peas_data --region sin --size 1 --app agent-dungeon`

## Secrets

```powershell
Copy-Item config\fly.secrets.env.example "$HOME\.agent_dungeon\fly.secrets.env"
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1
```

## 部署

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1
```

`--ha=false` 避免雙機器但只有一個 volume。

## GCP redirect（正式）

```
https://agent-dungeon.fly.dev/
```

與 `fly.toml` 的 `PUBLIC_URL` 一致。
