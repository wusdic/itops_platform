#!/bin/bash
# 启动 Qwen3.5-9B-DeepSeek-V4-Flash Q8_0 LLM 服务（端口 11435）
# 直接用 python3 单进程 + threaded=True（主线程推理，新请求排队等待）

set -e

MODEL_PATH="${1:-/tmp/model_cache_35/qwen3.5-9b-deepseek-v4-flash-q8_0.gguf}"
PORT="${2:-11435}"
N_CTX="${3:-8192}"
N_THREADS="${4:-1}"

PID_FILE="/tmp/llm_server_35.pid"
LOG_FILE="/tmp/llm_server_35.log"

# 如果服务已运行则跳过
if curl -s --max-time 3 http://127.0.0.1:${PORT}/health >/dev/null 2>&1; then
    echo "[LLM 35] Already running on port ${PORT}"
    exit 0
fi

# 清理旧PID
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill "$OLD_PID" 2>/dev/null || true
    rm -f "$PID_FILE"
fi

echo "[LLM 35] Starting..."
echo "  模型: $MODEL_PATH"
echo "  端口: $PORT"
echo "  n_ctx: $N_CTX"
echo "  线程: $N_THREADS"

cd /home/zcxx/.hermes/projects/itops_platform

# 使用 exec 让 Python 进程替代当前 shell，systemd Type=simple 就能正确跟踪 PID
exec python3 modules/business/ai_copilot/llm_server.py \
    "$MODEL_PATH" \
    "$PORT" \
    "$N_CTX" \
    "$N_THREADS" \
    >> "$LOG_FILE" 2>&1
