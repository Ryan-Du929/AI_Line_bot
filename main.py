import os
import logging
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

# Line credentials from environment variables
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


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

    logger.info(f"Received webhook request: signature={signature[:20]}...")

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Check your Channel Secret and access token.")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "ok"}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """Echo the received text message back to the user."""
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    logger.info(f"Received message from {user_id}: {user_message}")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"你說了：{user_message}")],
            )
        )

    logger.info(f"Replied to {user_id} with echo: {user_message}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)