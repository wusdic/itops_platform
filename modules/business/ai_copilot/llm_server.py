"""
BM-05 AI Copilot - LLM Server (llama-cpp-python)
模拟 Ollama API，兼容现有 llm_client.py
直接加载 GGUF 模型，无需 Ollama 二进制

KV cache bug 应对策略：
- 单 worker 线程，避免并发触发 re-evaluate
- 推理超时后在当前请求内 reload 模型 + 重试一次
- 模型加载后 KV cache 状态干净，可继续服务
"""

import json
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from flask import Flask, request, jsonify, Response
import llama_cpp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

_llama_model: Optional[llama_cpp.Llama] = None
_model_path: Optional[str] = None
_model_name: str = "qwen3.5-9b-deepseek-v4-flash-q8_0"
_executor: Optional[ThreadPoolExecutor] = None
_parent_pid: int = os.getpid()
_max_tokens_per_request: int = 32  # 限制每次最大 token 数，防止触发 llama.cpp KV cache bug
INFERENCE_TIMEOUT: int = 30


def load_model(model_path: str, n_ctx: int = 2048, n_threads: int = 1) -> llama_cpp.Llama:
    """加载 GGUF 模型（强制重建，清除 KV cache 损坏状态）"""
    global _llama_model, _model_path

    # 先释放旧模型
    if _llama_model is not None:
        try:
            del _llama_model
        except Exception:
            pass
        _llama_model = None
        _model_path = None

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
    _model_name = os.path.basename(model_path).replace(".gguf", "")
    logger.info(f"Model loaded successfully: {model_path}")
    return _llama_model


def _do_chat_completion(messages, temperature, max_tokens, stop):
    """在独立线程中执行推理"""
    global _llama_model
    result = _llama_model.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
        stream=False,
    )
    return result


def _do_generate(prompt, temperature, max_tokens):
    """在独立线程中执行推理"""
    global _llama_model
    result = _llama_model(prompt, max_tokens=max_tokens, temperature=temperature, stream=False)
    return result


def _reload_model_in_worker():
    """在工作线程中重新加载模型"""
    global _model_path
    if not _model_path:
        return
    logger.info("Reloading model in worker thread...")
    load_model(_model_path, n_ctx=2048, n_threads=8)
    logger.info("Model reloaded in worker thread")


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
    global _llama_model, _model_path

    if _llama_model is None:
        return jsonify({"error": "model not loaded"}), 503

    payload = request.get_json()
    if not payload:
        return jsonify({"error": "empty payload"}), 400

    messages = payload.get("messages", [])
    model = payload.get("model", _model_name)
    temperature = payload.get("temperature", 0.7)
    max_tokens = min(payload.get("max_tokens", 256), _max_tokens_per_request)
    stream = payload.get("stream", False)

    if not messages:
        return jsonify({"error": "no messages"}), 400

    # 第一次推理
    start = time.time()
    try:
        future = _executor.submit(_do_chat_completion, messages, temperature, max_tokens,
                                 ["<|user|>", "<|end|>", "<|im_end|>"])
        result = future.result(timeout=INFERENCE_TIMEOUT)
    except FuturesTimeoutError:
        elapsed = time.time() - start
        logger.warning(f"Chat timeout after {elapsed:.1f}s — reloading model and retrying once")

        # reload 模型（在工作线程中）
        try:
            reload_future = _executor.submit(_reload_model_in_worker)
            reload_future.result(timeout=60)  # 等待 reload 完成
        except FuturesTimeoutError:
            logger.error("Model reload timed out — giving up")
            return jsonify({"error": "model reload timeout, please retry"}), 504
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            return jsonify({"error": f"model reload failed: {e}"}), 504

        # 重试一次
        try:
            future = _executor.submit(_do_chat_completion, messages, temperature, max_tokens,
                                     ["<|user|>", "<|end|>", "<|im_end|>"])
            result = future.result(timeout=INFERENCE_TIMEOUT)
        except FuturesTimeoutError:
            logger.error("Retry also timed out — model may need manual restart")
            return jsonify({"error": "inference retry timeout, please retry later"}), 504

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

    if stream:
        def simulate_stream():
            for char in content:
                yield f"data: {json.dumps({'model': model, 'message': {'role': 'assistant', 'content': char}, 'done': False})}\n"
            yield f"data: {json.dumps({'model': model, 'message': {'role': 'assistant', 'content': ''}, 'done': True, 'eval_count': len(content), 'eval_duration': 0})}\n"
        return Response(simulate_stream(), mimetype="application/x-ndjson")
    else:
        return jsonify({
            "model": model,
            "message": {"role": "assistant", "content": content},
            "done": True,
            "total_duration": 0,
            "eval_count": result.get("usage", {}).get("completion_tokens", 0),
            "eval_duration": 0,
        })


@app.route("/api/generate", methods=["POST"])
def generate():
    """生成接口 — Ollama /api/generate 兼容"""
    global _llama_model, _model_path

    if _llama_model is None:
        return jsonify({"error": "model not loaded"}), 503

    payload = request.get_json()
    if not payload:
        return jsonify({"error": "empty payload"}), 400

    prompt = payload.get("prompt", "")
    model = payload.get("model", _model_name)
    temperature = payload.get("temperature", 0.7)
    stream = payload.get("stream", False)
    max_tokens = min(payload.get("options", {}).get("num_predict", 256), _max_tokens_per_request)

    if not prompt:
        return jsonify({"error": "no prompt"}), 400

    start = time.time()
    try:
        future = _executor.submit(_do_generate, prompt, temperature, max_tokens)
        result = future.result(timeout=INFERENCE_TIMEOUT)
    except FuturesTimeoutError:
        elapsed = time.time() - start
        logger.warning(f"Generate timeout after {elapsed:.1f}s — reloading model and retrying once")

        try:
            reload_future = _executor.submit(_reload_model_in_worker)
            reload_future.result(timeout=60)
        except FuturesTimeoutError:
            logger.error("Model reload timed out — giving up")
            return jsonify({"error": "model reload timeout, please retry"}), 504
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            return jsonify({"error": f"model reload failed: {e}"}), 504

        try:
            future = _executor.submit(_do_generate, prompt, temperature, max_tokens)
            result = future.result(timeout=INFERENCE_TIMEOUT)
        except FuturesTimeoutError:
            logger.error("Retry also timed out — model may need manual restart")
            return jsonify({"error": "inference retry timeout, please retry later"}), 504

    except Exception as e:
        logger.error(f"Generate error: {e}")
        return jsonify({"error": str(e)}), 500

    content = result["choices"][0]["text"]

    if stream:
        def simulate_stream():
            for char in content:
                yield f"data: {json.dumps({'response': char, 'done': False})}\n"
            yield f"data: {json.dumps({'response': '', 'done': True})}\n"
        return Response(simulate_stream(), mimetype="application/x-ndjson")
    else:
        return jsonify({"model": model, "response": content, "done": True})


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    if _llama_model is None:
        return jsonify({"status": "no model loaded"}), 503
    return jsonify({"status": "healthy", "model": _model_name})


@app.route("/reload", methods=["POST"])
def reload_model():
    """手动触发模型重载"""
    global _model_path
    if not _model_path:
        return jsonify({"error": "no model loaded"}), 503
    try:
        reload_future = _executor.submit(_reload_model_in_worker)
        reload_future.result(timeout=60)
        return jsonify({"status": "reloaded successfully"})
    except FuturesTimeoutError:
        return jsonify({"error": "reload timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_server(model_path: str, host: str = "0.0.0.0", port: int = 11434,
                 n_ctx: int = 2048, n_threads: int = 1):
    """启动服务"""
    global _executor, _model_path
    _model_path = model_path
    load_model(model_path, n_ctx=n_ctx, n_threads=n_threads)
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm_infer")
    logger.info(f"LLM Server starting on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True,
            passthrough_errors=False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <model.gguf> [port] [n_ctx] [n_threads]")
        sys.exit(1)

    model_path = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 11434
    n_ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
    n_threads = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    start_server(model_path, port=port, n_ctx=n_ctx, n_threads=n_threads)
