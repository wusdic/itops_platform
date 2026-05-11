#!/bin/bash
# LLM Server 启动脚本 (llama-cpp-python)
# 用法: ./start_llm_server.sh [模型路径] [端口] [n_ctx] [n_threads]

set -e

MODEL_PATH="${1:-/tmp/model_cache/unsloth/Qwen3___6-27B-GGUF/Qwen3.6-27B-Q4_K_M.gguf}"
PORT="${2:-11434}"
N_CTX="${3:-2048}"
N_THREADS="${4:-1}"

PID_FILE="/tmp/llm_server.pid"

# 如果服务已运行则退出
if curl -s http://127.0.0.1:${PORT}/health >/dev/null 2>&1; then
    echo "[LLM Server] Already running on port ${PORT}"
    exit 0
fi

# 如果有旧PID文件，清理
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill "$OLD_PID" 2>/dev/null || true
    rm -f "$PID_FILE"
fi

echo "[LLM Server] Starting..."
echo "  模型: $MODEL_PATH"
echo "  端口: $PORT"
echo "  上下文: $N_CTX tokens"
echo "  线程: $N_THREADS"

cd /home/zcxx/.hermes/projects/itops_platform

nohup python3 modules/business/ai_copilot/llm_server.py \
    "$MODEL_PATH" \
    "$PORT" \
    "$N_CTX" \
    "$N_THREADS" \
    > /tmp/llm_server.log 2>&1 &

echo $! > "$PID_FILE"
echo "[LLM Server] PID $! started. Log: /tmp/llm_server.log"
