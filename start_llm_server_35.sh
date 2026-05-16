#!/bin/bash
# 启动 Qwen3.5-9B DeepSeek-V4 Flash Q8_0 LLM 服务
MODEL_PATH="/home/zcxx/models/Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0.gguf"
PORT=11435

/home/zcxx/anaconda3/bin/python3 -m llama_cpp.server \
    --model "$MODEL_PATH" \
    --host 0.0.0.0 --port $PORT \
    --n_ctx 512 --n_threads 8 \
    >> /tmp/llm_server_35.log 2>&1 &

echo "LLM server started on port $PORT, PID: $!"
