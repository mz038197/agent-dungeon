# 本機開發

## 前置

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## 設定

```powershell
Copy-Item config\local.env.example "$HOME\.agent_dungeon\local.env"
notepad "$HOME\.agent_dungeon\local.env"
```

### 方式 A：免 Google OAuth（建議本機）

在 `local.env` 設定：

```ini
LOCAL_DEV_AUTH=bypass
LOCAL_DEV_EMAIL=dev@local.test
LOCAL_DEV_NAME=本地開發者
SESSION_SECRET=change-me-local-dev
PEAS_LLM_API_KEY=你的金鑰
PUBLIC_URL=http://127.0.0.1:8501
```

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` 可留空。開啟 `http://127.0.0.1:8501` 會自動以 dev 使用者進入。

### 方式 B：開發模式表單

不設 `LOCAL_DEV_AUTH=bypass`，且 Google OAuth 留空 → 登入頁顯示「開發模式登入」，手動填 email 即可。

### 方式 C：Google OAuth

填寫 `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `SESSION_SECRET`，並在 GCP Console 加 redirect `http://127.0.0.1:8501/`。詳見 [google-oauth-setup.md](./google-oauth-setup.md)。

## 啟動

```powershell
cd C:\Users\mz038\Desktop\peas-agent\agent_dungeon
uv sync
uv run streamlit run app.py
```

## 驗收

1. 本地 bypass：直接進入 Voice 關卡，無 Google 登入
2. 左欄模組地圖、中欄 Mission / Skill Forge 框線正常
3. 右欄 agent.py 預覽 + Agent 對話
4. 通關後中欄顯示 MISSION COMPLETE 與延伸技能面板

使用者資料：`%USERPROFILE%\.agent_dungeon\data\users\{google_sub}\`

## 常見錯誤

| 錯誤 | 處理 |
|------|------|
| `redirect_uri_mismatch` | GCP Console 加 `http://127.0.0.1:8501/` |
| 登入狀態驗證失敗 | 勿混用 localhost 與 127.0.0.1 |
| Agent 啟用失敗 | 檢查 `PEAS_LLM_API_KEY` |
| 修改 local.env 後仍舊行為 | 重啟 Streamlit |
