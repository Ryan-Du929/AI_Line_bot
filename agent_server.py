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

    reply = f"收到你的訊息了：{user_message}（這是 AI Agent 的回覆）"

    return {"reply": reply, "user_id": user_id}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("agent_server:app", host="0.0.0.0", port=port, reload=True)