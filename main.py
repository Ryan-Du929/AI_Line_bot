import os
import json
import logging
import requests
import threading
import time
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Line Bot Webhook")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# === AI Agent URL ===
AGENT_BASE = os.getenv("AI_AGENT_URL", "https://ai-agent-7s7g.onrender.com").rstrip("/")
AI_AGENT_URL = AGENT_BASE + "/chat"

# === 要 ping 的目標（防止 Render Free 休眠）=== 
KEEP_ALIVE_TARGETS = [
    "https://ai-agent-7s7g.onrender.com",
    "https://ai-line-bot-4hhb.onrender.com",
]
KEEP_ALIVE_INTERVAL = 300  # 5 分鐘，Render Free 通常 5-15 分鐘休眠

logger.info(f"========== CONFIG ==========")
logger.info(f"AI_AGENT_URL = {AI_AGENT_URL}")
logger.info(f"CHANNEL_ACCESS_TOKEN set = {bool(CHANNEL_ACCESS_TOKEN)}")
logger.info(f"CHANNEL_SECRET set = {bool(CHANNEL_SECRET)}")
logger.info(f"Keep-alive interval: {KEEP_ALIVE_INTERVAL}s")
logger.info(f"============================")


# ── 背景 Keep-Alive 執行緒 ──────────────────────────────
def keep_alive_loop():
    """定時 ping 所有服務，防止 Render Free 方案休眠"""
    logger.info("[keep-alive] 背景執行緒啟動")
    while True:
        try:
            for url in KEEP_ALIVE_TARGETS:
                try:
                    r = requests.get(url, timeout=10)
                    logger.debug(f"[keep-alive] Ping {url} → {r.status_code}")
                except Exception as e:
                    logger.warning(f"[keep-alive] Ping {url} failed: {e}")
        except Exception as e:
            logger.error(f"[keep-alive] 迴圈錯誤: {e}")
        time.sleep(KEEP_ALIVE_INTERVAL)


# 在模組載入時啟動背景執行緒
_keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
_keep_alive_thread.start()
logger.info("[keep-alive] 背景執行緒已啟動")


# ── API Endpoints ────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Line Bot is running", "agent_url": AI_AGENT_URL}


@app.get("/health")
async def health():
    return {"status": "healthy", "agent_url": AI_AGENT_URL}


@app.get("/ping")
async def ping():
    """Keep-alive endpoint: 被外部呼叫時也順便 ping 其他服務"""
    results = {}
    for url in KEEP_ALIVE_TARGETS:
        try:
            r = requests.get(url, timeout=10)
            results[url] = r.status_code
        except Exception as e:
            results[url] = str(e)
    return {"ping": results}


@app.get("/debug/agent_test")
async def debug_agent_test():
    """內建測試：直接呼叫 ai-agent 並回傳結果"""
    try:
        resp = requests.post(
            AI_AGENT_URL,
            json={"message": "ping", "user_id": "debug_test"},
            timeout=30,
        )
        return {
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code == 200 else resp.text[:200],
            "target_url": AI_AGENT_URL,
        }
    except Exception as e:
        return {"error": str(e), "target_url": AI_AGENT_URL}


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_text = body.decode("utf-8")
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return {"status": "ok"}


def ask_ai_agent(user_message: str, user_id: str) -> str:
    """呼叫 AI Agent，如果 timeout 則重試一次（應付 Render Free 冷啟動）"""
    logger.info(f"ask_ai_agent CALLED: target={AI_AGENT_URL}, msg={user_message[:50]}")
    
    max_retries = 2  # 第一次嘗試 + 一次重試
    last_error = ""
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                AI_AGENT_URL,
                json={"message": user_message, "user_id": user_id},
                timeout=60 if attempt > 0 else 30,
                # 第一次 30 秒 timeout；重試時給 60 秒（冷啟動可能較慢）
            )
            logger.info(f"ask_ai_agent RESPONSE (attempt {attempt+1}): status={resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("reply", "抱歉，我沒理解你的意思")
                if data.get("fallback"):
                    logger.warning("AI Agent 使用了 fallback 模式")
                return reply
            else:
                last_error = f"Agent error: {resp.status_code} {resp.text[:200]}"
                logger.error(last_error)
                
        except requests.exceptions.ConnectTimeout:
            last_error = "連線超時"
            logger.warning(f"ask_ai_agent attempt {attempt+1}: {last_error}")
            if attempt < max_retries - 1:
                logger.info(f"重試中... ({attempt+1}/{max_retries})")
                time.sleep(3)  # 重試前等 3 秒
        except requests.exceptions.ConnectionError as e:
            last_error = f"連線拒絕: {e}"
            logger.warning(f"ask_ai_agent attempt {attempt+1}: {last_error}")
            if attempt < max_retries - 1:
                logger.info(f"重試中... ({attempt+1}/{max_retries})")
                time.sleep(5)
        except Exception as e:
            last_error = f"非預期錯誤: {e}"
            logger.error(f"ask_ai_agent attempt {attempt+1}: {last_error}")
            break  # 非連線錯誤不重試
    
    return "系統正在啟動中，請稍後再傳一次 🙏"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id
    logger.info(f"LINE RECEIVED from {user_id}: {user_message}")
    ai_reply = ask_ai_agent(user_message, user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=ai_reply)],
            )
        )
    logger.info(f"LINE REPLIED to {user_id}: {ai_reply}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting LINE Bot on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)