import os
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    message: str
    user_id: str = "unknown"


@app.get("/")
async def root():
    return {"status": "ok", "agent": "AI Agent v3.0", "version": "3.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}


@app.post("/chat")
async def chat(req: ChatRequest):
    user_message = req.message
    user_id = req.user_id
    logger.info(f"[v3.0.0] Received from {user_id}: {user_message}")
    try:
        reply = process_message(user_message)
        return {"reply": reply, "user_id": user_id, "version": "3.0.0"}
    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        return {"reply": "抱歉，處理時發生錯誤", "user_id": user_id, "version": "3.0.0"}


def process_message(message: str) -> str:
    msg = message.strip()
    greetings = ["你好", "嗨", "hello", "hi", "hey", "哈囉", "早安", "晚安", "下午好"]
    if any(msg.startswith(g) or msg == g for g in greetings):
        return "[v3.0.0] 你好！我是你的 AI 工作助手，有什麼需要幫忙的嗎？"
    if msg in ["help", "說明", "功能", "?", "ping"]:
        return "[v3.0.0] 系統正常！收到你的 ping ✅"
    if msg in ["status", "狀態", "檢查"]:
        return "[v3.0.0] 系統正常運行中 ✅ 所有服務都在線上。"
    return f"[v3.0.0] 收到！你說：{message}"


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("agent_server:app", host="0.0.0.0", port=port, reload=False)