import os
import json
import logging
import requests
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

# === 修改這裡：直接用 os.getenv 讀取 ===
AGENT_BASE = os.getenv("AI_AGENT_URL", "https://ai-agent-7s7g.onrender.com").rstrip("/")
AI_AGENT_URL = AGENT_BASE + "/chat"
logger.info(f"========== CONFIG ==========")
logger.info(f"AI_AGENT_URL = {AI_AGENT_URL}")
logger.info(f"CHANNEL_ACCESS_TOKEN set = {bool(CHANNEL_ACCESS_TOKEN)}")
logger.info(f"CHANNEL_SECRET set = {bool(CHANNEL_SECRET)}")
logger.info(f"============================")


@app.get("/")
async def root():
    return {"status": "ok", "message": "Line Bot is running", "agent_url": AI_AGENT_URL}


@app.get("/health")
async def health():
    return {"status": "healthy", "agent_url": AI_AGENT_URL}


@app.get("/ping")
async def ping():
    """Keep-alive endpoint: called externally every 10 min to prevent Render Free sleep"""
    import requests as req
    results = {}
    for url in ["https://ai-agent-7s7g.onrender.com", "https://ai-line-bot-4hhb.onrender.com"]:
        try:
            r = req.get(url, timeout=10)
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
            timeout=15,
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
    logger.info(f"ask_ai_agent CALLED: target={AI_AGENT_URL}, msg={user_message[:50]}")
    try:
        resp = requests.post(
            AI_AGENT_URL,
            json={"message": user_message, "user_id": user_id},
            timeout=30,
        )
        logger.info(f"ask_ai_agent RESPONSE: status={resp.status_code}, body={resp.text[:200]}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("reply", "抱歉，我沒理解你的意思")
        else:
            logger.error(f"Agent error: {resp.status_code} {resp.text[:300]}")
            return "系統忙碌中，請稍後再試"
    except requests.exceptions.ConnectTimeout:
        logger.error("Connection timed out")
        return "連線超時，請稍後再試"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection refused: {e}")
        return "無法連線到 AI 服務"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "系統異常，請稍後再試"


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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)