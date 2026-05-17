"""Render 原生 ping 腳本 — 部署在 ai-line-bot 或 ai-agent 上作為定期喚醒"""
import requests
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGETS = [
    "https://ai-agent-7s7g.onrender.com",
    "https://ai-line-bot-4hhb.onrender.com",
]

def ping():
    for url in TARGETS:
        try:
            r = requests.get(url, timeout=10)
            logger.info(f"Ping {url} → {r.status_code}")
        except Exception as e:
            logger.warning(f"Ping {url} failed: {e}")

if __name__ == "__main__":
    # Render 上當 entry point: 先 ping 一次再進入循環
    ping()
    while True:
        time.sleep(540)  # 9 分鐘
        ping()
