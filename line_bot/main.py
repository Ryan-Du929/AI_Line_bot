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

# AI Agent API - 從環境變數讀取，若無則用 Render 上的 ai-agent 服務
APP_VERSION = "v2.1.0"

AI_AGENT_URL = os.getenv("AI_AGENT_URL", "https://ai-agent-7s7g.onrender.com/chat")
logger.info(f"[{APP_VERSION}] AI_AGENT_URL configured as: {AI_AGENT_URL}")


@app.get("/")
async def root():
    return {"status": "ok", "message": "Line Bot is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


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
    logger.info(f"[{APP_VERSION}] Sending to AI_AGENT_URL: {AI_AGENT_URL}")
    """Send user message to AI Agent and get reply."""
    try:
        resp = requests.post(
            AI_AGENT_URL,
            json={"message": user_message, "user_id": user_id},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("reply", "抱歉，我沒理解你的意思")
        else:
            logger.error(f"AI Agent error: {resp.status_code} {resp.text}")
            return "系統忙碌中，請稍後再試"
    except requests.exceptions.Timeout:
        logger.error("AI Agent request timed out")
        return "處理時間過長，請稍後再試"
    except Exception as e:
        logger.error(f"AI Agent request failed: {e}")
        return "連線異常，請稍後再試"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    logger.info(f"Received from {user_id}: {user_message}")

    # 交給 AI Agent 處理
    ai_reply = ask_ai_agent(user_message, user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=ai_reply)],
            )
        )

    logger.info(f"Replied to {user_id}: {ai_reply}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)