"""
BM-05 AI Copilot - LLM Client
LLM客户端 - llama.cpp GGUF集成，支持Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0等大模型
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    display_name: str
    max_tokens: int = 8192
    context_window: int = 32768
    enabled: bool = True


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """对话会话"""
    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加消息"""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.last_active = datetime.now()
        return msg
    
    def get_context(self, max_messages: int = 50) -> List[Dict[str, str]]:
        """获取上下文"""
        recent = self.messages[-max_messages:] if max_messages > 0 else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]
    
    def get_token_count(self, model: str = "qwen3.5:8b") -> int:
        """估算token数量"""
        total = 0
        for msg in self.messages:
            # 简单估算: 中文约2字符/token, 英文约4字符/token
            text = msg.content
            total += len(text) // 2
        return total


class LLMClient:
    """LLM客户端 - Ollama集成"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM客户端
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.ollama_config = config.get("ollama", {})
        self.model_config = config.get("models", {})
        self.conv_config = config.get("conversation", {})
        
        self.base_url = self.ollama_config.get("base_url", "http://localhost:11434")
        self.timeout = self.ollama_config.get("timeout", 300)
        self.retry_count = self.ollama_config.get("retry_count", 3)
        self.retry_delay = self.ollama_config.get("retry_delay", 5)
        
        self._models: Dict[str, ModelInfo] = {}
        self._conversations: Dict[str, Conversation] = {}
        self._default_model = self.model_config.get("default", "qwen3.5:8b")
        
        self._init_models()
        
    def _init_models(self):
        """初始化模型列表"""
        available = self.model_config.get("available", [])
        for m in available:
            self._models[m["name"]] = ModelInfo(
                name=m["name"],
                display_name=m.get("display_name", m["name"]),
                max_tokens=m.get("max_tokens", 8192),
                context_window=m.get("context_window", 32768),
                enabled=m.get("enabled", True)
            )
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True
        )
    
    async def check_health(self) -> Dict[str, Any]:
        """检查Ollama服务健康状态"""
        try:
            async with self._get_client() as client:
                response = await client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "status": "healthy",
                        "available_models": [m["name"] for m in models],
                        "base_url": self.base_url
                    }
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def list_models(self) -> List[ModelInfo]:
        """列出可用模型"""
        return [m for m in self._models.values() if m.enabled]
    
    async def get_model(self, name: str) -> Optional[ModelInfo]:
        """获取指定模型信息"""
        return self._models.get(name)
    
    def create_conversation(self, conversation_id: str = None, metadata: Dict[str, Any] = None) -> Conversation:
        """创建新对话"""
        if conversation_id is None:
            conversation_id = f"conv_{int(time.time() * 1000)}"
        
        conv = Conversation(
            id=conversation_id,
            metadata=metadata or {}
        )
        self._conversations[conversation_id] = conv
        return conv
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        return self._conversations.get(conversation_id)
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False
    
    def _build_payload(self, messages: List[Dict], model: str, 
                       stream: bool = True, **kwargs) -> Dict[str, Any]:
        """构建请求payload"""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        # 添加可选参数
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
            
        return payload
    
    async def chat(self, messages: List[Dict[str, str]], model: str = None,
                   temperature: float = 0.7, max_tokens: int = 8192,
                   **kwargs) -> Dict[str, Any]:
        """
        同步聊天请求
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            {"content": "...", "done": true, "model": "...", "total_duration": ...}
        """
        model = model or self._default_model
        
        for attempt in range(self.retry_count):
            try:
                payload = self._build_payload(messages, model, stream=False, 
                                              temperature=temperature, 
                                              max_tokens=max_tokens, **kwargs)
                
                async with self._get_client() as client:
                    response = await client.post("/api/chat", json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "content": result.get("message", {}).get("content", ""),
                            "done": True,
                            "model": result.get("model", model),
                            "total_duration": result.get("total_duration", 0),
                            "eval_count": result.get("eval_count", 0),
                            "eval_duration": result.get("eval_duration", 0)
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"Chat request failed: {error_msg}")
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.retry_count}")
            except Exception as e:
                logger.error(f"Chat request error: {e}")
                
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay)
                
        return {"content": "", "done": False, "error": "Max retries exceeded"}
    
    async def chat_stream(self, messages: List[Dict[str, str]], model: str = None,
                          temperature: float = 0.7, max_tokens: int = 8192,
                          **kwargs) -> AsyncGenerator[str, None]:
        """
        流式聊天请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Yields:
            流式输出的文本片段
        """
        model = model or self._default_model
        full_content = ""
        
        for attempt in range(self.retry_count):
            try:
                payload = self._build_payload(messages, model, stream=True,
                                              temperature=temperature,
                                              max_tokens=max_tokens, **kwargs)
                
                async with self._get_client() as client:
                    async with client.stream("POST", "/api/chat", json=payload) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        data = json.loads(line)
                                        if "message" in data:
                                            content = data["message"].get("content", "")
                                            full_content += content
                                            yield content
                                        if data.get("done", False):
                                            break
                                    except json.JSONDecodeError:
                                        continue
                            break
                        else:
                            error_msg = f"HTTP {response.status_code}"
                            logger.error(f"Stream request failed: {error_msg}")
                            yield f"[Error: {error_msg}]"
                            break
                            
            except httpx.TimeoutException:
                logger.warning(f"Stream timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"[Error: {str(e)}]"
                break
                
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay)
    
    async def generate(self, prompt: str, model: str = None,
                       temperature: float = 0.7, **kwargs) -> Dict[str, Any]:
        """
        生成文本（非对话模式）
        
        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            生成结果
        """
        model = model or self._default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        }
        payload.update(kwargs)
        
        try:
            async with self._get_client() as client:
                response = await client.post("/api/generate", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "content": result.get("response", ""),
                        "done": True,
                        "model": result.get("model", model)
                    }
                else:
                    return {"content": "", "done": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Generate error: {e}")
            return {"content": "", "done": False, "error": str(e)}
    
    async def generate_stream(self, prompt: str, model: str = None,
                              temperature: float = 0.7, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式生成文本
        
        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数
            
        Yields:
            流式输出的文本片段
        """
        model = model or self._default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature
        }
        payload.update(kwargs)
        
        try:
            async with self._get_client() as client:
                async with client.stream("POST", "/api/generate", json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    content = data.get("response", "")
                                    yield content
                                    if data.get("done", False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        yield f"[Error: HTTP {response.status_code}]"
        except Exception as e:
            yield f"[Error: {str(e)}]"
    
    def cleanup_expired_conversations(self, timeout: int = None):
        """清理过期对话"""
        timeout = timeout or self.conv_config.get("session_timeout", 3600)
        now = datetime.now()
        expired = []
        
        for conv_id, conv in self._conversations.items():
            age = (now - conv.last_active).total_seconds()
            if age > timeout:
                expired.append(conv_id)
        
        for conv_id in expired:
            self.delete_conversation(conv_id)
            
        return len(expired)


# 同步支持
import asyncio

class SyncLLMClient:
    """同步LLM客户端封装"""
    
    def __init__(self, config: Dict[str, Any]):
        self._async_client = LLMClient(config)
        self._loop = None
    
    def _ensure_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop
    
    def chat(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> Dict[str, Any]:
        loop = self._ensure_loop()
        return loop.run_until_complete(self._async_client.chat(messages, model, **kwargs))
    
    def chat_stream(self, messages: List[Dict[str, str]], model: str = None, **kwargs):
        loop = self._ensure_loop()
        return loop.run_until_complete(self._async_client.chat_stream(messages, model, **kwargs))
    
    def generate(self, prompt: str, model: str = None, **kwargs) -> Dict[str, Any]:
        loop = self._ensure_loop()
        return loop.run_until_complete(self._async_client.generate(prompt, model, **kwargs))
    
    def check_health(self) -> Dict[str, Any]:
        loop = self._ensure_loop()
        return loop.run_until_complete(self._async_client.check_health())


# 全局客户端实例
_global_client: Optional[LLMClient] = None


def get_llm_client(config: Dict[str, Any] = None) -> LLMClient:
    """获取全局LLM客户端"""
    global _global_client
    if _global_client is None and config is not None:
        _global_client = LLMClient(config)
    return _global_client


def init_llm_client(config: Dict[str, Any]) -> LLMClient:
    """初始化全局LLM客户端"""
    global _global_client
    _global_client = LLMClient(config)
    return _global_client
