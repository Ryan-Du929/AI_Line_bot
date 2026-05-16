import os
import json
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Server")


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

    # 解析訊息，根據關鍵字回應
    reply = process_message(user_message)

    logger.info(f"Replying to {user_id}: {reply}")
    return {"reply": reply, "user_id": user_id}


def process_message(message: str) -> str:
    """Process incoming message and generate reply."""
    msg = message.strip()

    # 基本問候
    greetings = ["你好", "嗨", "hello", "hi", "hey", "哈囉", "早安", "晚安", "下午好"]
    if any(msg.startswith(g) or msg == g for g in greetings):
        return "你好！我是你的 AI 工作助手，有什麼需要幫忙的嗎？"

    # 說明
    if msg in ["help", "說明", "功能", "?"]:
        return (
            "我可以幫你處理以下工作：\n"
            "• 開發任務（寫程式、改程式碼）\n"
            "• 檔案操作（讀取、編輯、建立檔案）\n"
            "• 資訊查詢（搜尋網路、讀文件）\n"
            "• 問題討論與分析\n\n"
            "直接把需求告訴我就好！"
        )

    # 狀態查詢
    if msg in ["status", "狀態", "檢查"]:
        return "系統正常運行中 ✅\n所有服務都在線上。"

    # 預設回覆
    return (
        f"收到你的訊息了。\n\n"
        f"你說：{message}\n\n"
        f"我目前正在處理中，請告訴我更具體的需求，"
        f"例如：「幫我查資料」「寫一支 Python 爬蟲」「分析這段文字」……"
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("agent_server:app", host="0.0.0.0", port=port, reload=True)