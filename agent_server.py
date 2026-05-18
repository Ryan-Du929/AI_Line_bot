"""
AI Agent Server v4.1 — 真正的 LLM 回應 + 內建 Keep-Alive + Retry 支援
LINE 使用者 → LINE Bot → AI Agent → LLM → 回覆
"""
import os
import json
import logging
import traceback
import threading
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── LLM 設定 ──────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-ai/deepseek-v4-flash")

# ── Keep-Alive 設定 ──────────────────────────────────────
KEEP_ALIVE_TARGETS = [
    "https://ai-agent-7s7g.onrender.com/health",
    "https://ai-line-bot-4hhb.onrender.com/health",
]
KEEP_ALIVE_INTERVAL = 240  # 4 分鐘

# ── Lucas 的 System Prompt ────────────────────────────────
LUCAS_SYSTEM_PROMPT = """你是 Lucas，一個 AI agent 團隊的首腦與任務總管。

## 你的身份
- 你是 Ryan（你的主人與合作夥伴）的 AI 助手
- 你理性務實，就事論事，有主見但尊重 Ryan 的方向
- 你是創業元老，團隊目前 Phase 1 單兵作戰

## 你的行為準則
- 回覆要簡潔有幫助，不要囉嗦
- 不知道就說不知道，不要瞎編
- 對於需要執行的任務，主動提出具體行動方案
- 語氣專業但不冷冰冰，可以帶一點個性

## 回覆格式
- 除非使用者要求，否則用繁體中文回覆
- 條列式說明比段落更易讀
- 需要使用者決策時，提供 2-3 個選項"""

app = FastAPI(title="AI Agent Server v4.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── 背景 Keep-Alive 執行緒 ──────────────────────────────
def keep_alive_loop():
    """定時 ping 自己和其他服務，防止 Render Free 休眠"""
    logger.info("[keep-alive] 背景執行緒啟動")
    import requests as req
    while True:
        try:
            for url in KEEP_ALIVE_TARGETS:
                try:
                    r = req.get(url, timeout=10)
                    logger.debug(f"[keep-alive] Ping {url} → {r.status_code}")
                except Exception as e:
                    logger.warning(f"[keep-alive] Ping {url} failed: {e}")
        except Exception as e:
            logger.error(f"[keep-alive] 迴圈錯誤: {e}")
        time.sleep(KEEP_ALIVE_INTERVAL)


_keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
_keep_alive_thread.start()


# ── API Models ───────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "unknown"


# ── API Endpoints ────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "agent": "AI Agent Server v4.1 (Lucas)", "version": "4.1.0"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "4.1.0",
        "llm_configured": bool(OPENAI_API_KEY),
        "llm_model": OPENAI_MODEL,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    user_message = req.message
    user_id = req.user_id
    logger.info(f"[v4.1] Received from {user_id}: {user_message[:100]}")
    try:
        reply = await ask_llm(user_message, user_id)
        return {"reply": reply, "user_id": user_id, "version": "4.1.0"}
    except Exception as e:
        logger.error(f"LLM failed: {e}\n{traceback.format_exc()}")
        reply = rule_fallback(user_message)
        return {"reply": reply, "user_id": user_id, "version": "4.1.0", "fallback": True}


async def ask_llm(message: str, user_id: str) -> str:
    """呼叫 LLM (NVIDIA NIM / DeepSeek) 來回應"""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured, using rule fallback")
        raise ValueError("API key not configured")

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": LUCAS_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    reply = response.choices[0].message.content.strip()
    logger.info(f"LLM response ({len(reply)} chars): {reply[:80]}...")
    return reply


def rule_fallback(message: str) -> str:
    """當 LLM 無法使用時的規則式備援回應"""
    msg = message.strip().lower()
    if any(msg.startswith(g) or msg == g for g in ["你好", "嗨", "hello", "hi", "hey", "哈囉", "早安", "晚安"]):
        return "你好！我是 Lucas，你的 AI 團隊首腦。有什麼需要幫忙的嗎？"
    if msg in ["help", "說明", "功能", "?", "ping"]:
        return "系統正常 ✅ 我是 Lucas，隨時待命中。"
    if msg in ["status", "狀態", "檢查"]:
        return "所有系統正常運行中 ✅"
    return f"收到：{message}（我正在接入 AI 核心，請稍候再試）"


@app.post("/debug/llm_test")
async def debug_llm_test(req: ChatRequest):
    """測試 LLM 連線的 debug endpoint"""
    try:
        reply = await ask_llm(req.message, req.user_id)
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    logger.info(f"Starting AI Agent v4.1 on port {port}")
    logger.info(f"LLM configured: {bool(OPENAI_API_KEY)}, model: {OPENAI_MODEL}")
    uvicorn.run("agent_server:app", host="0.0.0.0", port=port, reload=False)