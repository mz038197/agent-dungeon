# Google OAuth 設定

## Redirect URI

| 環境 | URI |
|------|-----|
| 本機 | `http://127.0.0.1:8501/` |
| Fly | `https://agent-dungeon.fly.dev/` |

可與 `vans_coding_router` 共用同一 OAuth Client，**追加**上述 URI 即可。

## 環境變數

| 變數 | 說明 |
|------|------|
| `GOOGLE_CLIENT_ID` | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Client Secret |
| `SESSION_SECRET` | 隨機字串，簽署 OAuth state |
| `PUBLIC_URL` | 須與瀏覽器造訪網域一致 |

本機寫入 `%USERPROFILE%\.agent_dungeon\local.env`；Fly 用 `fly secrets set`。

## Consent screen

若為 **Testing**，登入 Gmail 須在測試使用者名單內。
