# Line Bot Webhook — Echo Server

使用 Python FastAPI + LINE Messaging API SDK 打造的輕量級 Webhook 接收器，具備基本的 Echo 回聲功能。

---

## 目錄結構

```
line_bot/
├── main.py              # FastAPI 主程式（Webhook 端點）
├── requirements.txt     # Python 依賴套件
├── .env.example         # 環境變數範本
└── README.md            # 本文件
```

---

## 在 LINE Developers 後台需申請的金鑰

| 項目 | 說明 | 從哪裡取得 |
|------|------|------------|
| **Channel Secret** | 用來驗證 Webhook 請求是否來自 LINE | LINE Developers Console → 你的 Provider → Channel → **Basic Settings** 頁面 |
| **Channel Access Token** | 用來呼叫 LINE Messaging API（回覆訊息） | 同頁面下方，點擊 **Issue** 產生（或使用 **Long-lived** / **Short-lived** token） |

> ⚠️ **一定要啟用 Webhook：** 在 **Messaging API** 頁籤中，將 **Webhook settings** 的 **Use webhook** 設為 **Enabled**，並在 **Webhook URL** 欄位填入你的公開網址（見下方 Cloudflare Tunnel 說明）。

---

## 如何啟動

### 1. 安裝依賴

```bash
cd /app/workspace/line_bot
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入你在 LINE Developers 後台取得的金鑰：

```
LINE_CHANNEL_ACCESS_TOKEN=你的ChannelAccessToken
LINE_CHANNEL_SECRET=你的ChannelSecret
PORT=8000
```

### 3. 啟動伺服器

```bash
python main.py
```

伺服器預設在 `http://0.0.0.0:8000` 監聽，Webhook 端點為 `/webhook`。

---

## 搭配 Cloudflare Tunnel 對外公開

Line 要求 Webhook URL 必須是 **HTTPS** 且可從外部存取。Cloudflare Tunnel 是最簡單的解決方案。

### 安裝 cloudflared

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux (x86_64)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

### 啟動 Tunnel（無需註冊，臨時模式）

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare 會產生一個類似 `https://xxxx-xxxx-xxxx.trycloudflare.com` 的隨機網址。

### 設定 LINE Webhook URL

1. 回到 [LINE Developers Console](https://developers.line.biz/console/)
2. 進入你的 **Provider** → **Channel** → **Messaging API** 頁籤
3. 在 **Webhook settings** 的 **Webhook URL** 欄位填入：
   ```
   https://xxxx-xxxx-xxxx.trycloudflare.com/webhook
   ```
4. 點擊 **Verify** — 如果顯示 **Success** 代表連線成功
5. 將 **Use webhook** 設為 **Enabled**
6. 點擊 **Apply**

---

## 測試

1. 將你的 Line Bot 加入好友（或掃描 Messaging API 頁面上的 QR Code）
2. 傳送任何文字訊息給 Bot
3. Bot 會回覆：`你說了：{你的訊息}`

---

## API 端點一覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/` | 根路徑，回傳服務狀態 |
| `GET` | `/health` | 健康檢查 |
| `POST` | `/webhook` | LINE 的 Webhook 端點（由 LINE Platform 呼叫） |

---

## 注意事項

- **Channel Secret** 和 **Channel Access Token** 請勿外流或 commit 到版本控制
- 生產環境建議使用 **Long-lived token** 並定期更換
- 若使用雲端服務（Render / Railway / Fly.io），可將環境變數設定在該平台，不需要 `.env`
- 本地開發時若只想測試 API，可用 `curl` 直接打在 `localhost:8000/health` 確認服務是否活著# Keep-alive marker
