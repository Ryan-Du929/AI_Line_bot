import os
import json
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "unknown"


@app.get("/")
async def root():
    return {"status": "ok", "agent": "AI Agent is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat")
async def chat(req: ChatRequest):
    user_message = req.message
    user_id = req.user_id
    logger.info(f"Received from {user_id}: {user_message}")
    logger.debug(f"Full request: message={user_message!r}, user_id={user_id!r}")

    try:
        reply = process_message(user_message)
        logger.info(f"Replying to {user_id}: {reply}")
        return {"reply": reply, "user_id": user_id}
    except Exception as e:
        logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
        return {"reply": "系統內部錯誤，請稍後再試", "user_id": user_id}


@app.post("/chat_debug")
async def chat_debug(req: Request):
    """Debug endpoint to see raw request."""
    body = await req.body()
    headers = dict(req.headers)
    logger.info(f"Raw request body: {body}")
    logger.info(f"Raw request headers: {headers}")
    return {"received": True, "body_length": len(body)}


def process_message(message: str) -> str:
    msg = message.strip()

    greetings = ["你好", "嗨", "hello", "hi", "hey", "哈囉", "早安", "晚安", "下午好"]
    if any(msg.startswith(g) or msg == g for g in greetings):
        return "你好！我是你的 AI 工作助手，有什麼需要幫忙的嗎？"

    if msg in ["help", "說明", "功能", "?"]:
        return (
            "我可以幫你處理以下工作：\n"
            "• 開發任務（寫程式、改程式碼）\n"
            "• 檔案操作（讀取、編輯、建立檔案）\n"
            "• 資訊查詢（搜尋網路、讀文件）\n"
            "• 問題討論與分析\n\n"
            "直接把需求告訴我就好！"
        )

    if msg in ["status", "狀態", "檢查"]:
        return "系統正常運行中 ✅\n所有服務都在線上。"

    return (
        f"收到你的訊息了。\n\n"
        f"你說：{message}\n\n"
        f"我目前正在處理中，請告訴我更具體的需求，"
        f"例如：「幫我查資料」「寫一支 Python 爬蟲」「分析這段文字」……"
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("agent_server:app", host="0.0.0.0", port=port, reload=False,
                log_level="info", access_log=True)