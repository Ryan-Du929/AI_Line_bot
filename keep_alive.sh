#!/bin/bash
# 每 10 分鐘 ping 兩個服務防止 Render Free 休眠
while true; do
  curl -s --max-time 10 https://ai-agent-7s7g.onrender.com/ > /dev/null 2>&1
  curl -s --max-time 10 https://ai-line-bot-4hhb.onrender.com/ > /dev/null 2>&1
  sleep 540  # 9 分鐘
done
