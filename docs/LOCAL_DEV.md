# 本機開發

## 前置

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- GCP OAuth Web Client（redirect 含 `http://127.0.0.1:8501/`）

## 設定

```powershell
Copy-Item config\local.env.example "$HOME\.agent_dungeon\local.env"
notepad "$HOME\.agent_dungeon\local.env"
```

必填：

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `SESSION_SECRET`
- `PEAS_LLM_API_KEY`
- `PUBLIC_URL=http://127.0.0.1:8501`

## 啟動

```powershell
cd C:\Users\mz038\Desktop\peas-agent\agent_dungeon
uv sync
uv run streamlit run app.py
```

## 驗收

1. 登入卡 → Google 登入
2. 授權後回到 `/?code=...`
3. 進入 Studio，側欄有 Home
4. 右欄可「啟用 Agent」並對話

使用者資料：`%USERPROFILE%\.agent_dungeon\data\users\{google_sub}\`

## 常見錯誤

| 錯誤 | 處理 |
|------|------|
| `redirect_uri_mismatch` | GCP Console 加 `http://127.0.0.1:8501/` |
| 登入狀態驗證失敗 | 勿混用 localhost 與 127.0.0.1 |
| Agent 啟用失敗 | 檢查 `PEAS_LLM_API_KEY` |
