"""
BM-05 AI Copilot - LLM Server (llama-cpp-python)
模拟 Ollama API，兼容现有 llm_client.py
直接加载 GGUF 模型，无需 Ollama 二进制
"""

import json
import logging
import time
from typing import Optional

from flask import Flask, request, jsonify, Response
import llama_cpp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

_llama_model: Optional[llama_cpp.Llama] = None
_model_path: Optional[str] = None
_model_name: str = "qwen3.6-27b-q4-k-m"


def load_model(model_path: str, n_ctx: int = 4096, n_threads: int = 16) -> llama_cpp.Llama:
    """加载 GGUF 模型"""
    global _llama_model, _model_path
    if _llama_model is not None and _model_path == model_path:
        logger.info(f"Model already loaded: {model_path}")
        return _llama_model

    logger.info(f"Loading model: {model_path} (n_ctx={n_ctx}, n_threads={n_threads})")
    _llama_model = llama_cpp.Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_threads_batch=n_threads,
        use_mlock=True,
        use_mmap=False,
        offload_kqv=False,
        flash_attention=False,
    )
    _model_path = model_path
    logger.info(f"Model loaded successfully: {model_path}")
    return _llama_model


@app.route("/api/tags", methods=["GET"])
def list_models():
    """列出可用模型 — Ollama /api/tags 兼容"""
    return jsonify({
        "models": [{
            "name": _model_name,
            "model": _model_name,
            "size": 0,
            "modified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }]
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """聊天接口 — Ollama /api/chat 兼容"""
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "empty payload"}), 400

    messages = payload.get("messages", [])
    model = payload.get("model", _model_name)
    temperature = payload.get("temperature", 0.7)
    max_tokens = payload.get("max_tokens", 4096)
    stream = payload.get("stream", False)

    if not messages:
        return jsonify({"error": "no messages"}), 400

    try:
        if stream:
            def generate():
                try:
                    for piece in _llama_model.create_chat_completion(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop=["<|user|>", "<|end|>", "<|im_end|>"],
                        stream=True,
                    ):
                        delta = piece.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "") or ""
                        if content:
                            yield f"data: {json.dumps({'model': model, 'message': {'role': 'assistant', 'content': content}, 'done': False})}\n"
                    yield f"data: {json.dumps({'model': model, 'message': {'role': 'assistant', 'content': ''}, 'done': True, 'eval_count': 0, 'eval_duration': 0})}\n"
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n"
            return Response(generate(), mimetype="application/x-ndjson")
        else:
            result = _llama_model.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=["<|user|>", "<|end|>", "<|im_end|>"],
                stream=False,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            return jsonify({
                "model": model,
                "message": {"role": "assistant", "content": content},
                "done": True,
                "total_duration": 0,
                "eval_count": result.get("usage", {}).get("completion_tokens", 0),
                "eval_duration": 0,
            })
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """生成接口 — Ollama /api/generate 兼容"""
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "empty payload"}), 400

    prompt = payload.get("prompt", "")
    model = payload.get("model", _model_name)
    temperature = payload.get("temperature", 0.7)
    stream = payload.get("stream", False)
    max_tokens = payload.get("options", {}).get("num_predict", 4096)

    if not prompt:
        return jsonify({"error": "no prompt"}), 400

    try:
        if stream:
            def generate_stream():
                for piece in _llama_model(prompt, max_tokens=max_tokens, temperature=temperature, stream=True):
                    token = piece["choices"][0].get("text", "")
                    yield f"data: {json.dumps({'response': token, 'done': False})}\n"
                yield f"data: {json.dumps({'response': '', 'done': True})}\n"
            return Response(generate_stream(), mimetype="application/x-ndjson")
        else:
            result = _llama_model(prompt, max_tokens=max_tokens, temperature=temperature, stream=False)
            content = result["choices"][0]["text"]
            return jsonify({"model": model, "response": content, "done": True})
    except Exception as e:
        logger.error(f"Generate error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    if _llama_model is None:
        return jsonify({"status": "no model loaded"}), 503
    return jsonify({"status": "healthy", "model": _model_name})


def start_server(model_path: str, host: str = "0.0.0.0", port: int = 11434,
                 n_ctx: int = 4096, n_threads: int = 16):
    """启动服务"""
    load_model(model_path, n_ctx=n_ctx, n_threads=n_threads)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <model.gguf> [port] [n_ctx] [n_threads]")
        sys.exit(1)

    model_path = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 11434
    n_ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 4096
    n_threads = int(sys.argv[4]) if len(sys.argv) > 4 else 16

    start_server(model_path, port=port, n_ctx=n_ctx, n_threads=n_threads)
