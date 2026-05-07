#!/bin/bash
# ITOps Platform 启动脚本

export CONFIG_FILE="config/dev.yaml"
export PYTHONUNBUFFERED=1
export LOG_LEVEL=INFO

echo "Starting ITOps Platform..."
echo "Config: $CONFIG_FILE"
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"

python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
