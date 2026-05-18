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
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Line Bot Direct LLM")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ── LLM 直接設定 ──────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-ai/deepseek-v4-flash")

# ── Keep-Alive ────────────────────────────────────────────
KEEP_ALIVE_TARGETS = [
    "https://ai-line-bot-4hhb.onrender.com",
]
KEEP_ALIVE_INTERVAL = 240  # 4 分鐘

logger.info(f"========== CONFIG ==========")
logger.info(f"LLM configured: {bool(OPENAI_API_KEY)}")
logger.info(f"LLM model: {OPENAI_MODEL}")
logger.info(f"============================")


# ── Keep-Alive Thread ────────────────────────────────────
def keep_alive_loop():
    while True:
        for url in KEEP_ALIVE_TARGETS:
            try:
                requests.get(url, timeout=10)
            except:
                pass
        time.sleep(KEEP_ALIVE_INTERVAL)

threading.Thread(target=keep_alive_loop, daemon=True).start()


# ── API ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "LINE Bot Direct LLM", "version": "5.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "llm_configured": bool(OPENAI_API_KEY)}

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


@app.get("/test_llm")
async def test_llm():
    """測試 LLM 連線（不需要 LINE signature）"""
    try:
        reply = call_llm_direct("說一句簡單的嗨就好")
        return {"status": "ok", "reply": reply}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def call_llm_direct(message: str) -> str:
    """直接 call NVIDIA NIM / DeepSeek，跳過 AI Agent server"""
    if not OPENAI_API_KEY:
        return "系統尚未設定完成，請稍後再試 🙏"
    
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "你是 Lucas，一個 AI agent 團隊的首腦。簡潔回覆繁體中文。"},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=256,
    )
    return response.choices[0].message.content.strip()


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id
    logger.info(f"LINE from {user_id}: {user_message}")
    
    try:
        reply = call_llm_direct(user_message)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        reply = "我正在處理你的訊息，請稍後再傳一次 🙏"
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=reply)],
            )
        )
    logger.info(f"Replied: {reply[:50]}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)