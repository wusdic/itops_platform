"""
请求日志中间件
记录所有请求的详细信息
"""

import json
import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录请求路径、方法、耗时、状态码等信息
    """
    
    # 敏感头部列表
    SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "x-auth-token"}
    
    # 敏感参数列表
    SENSITIVE_PARAMS = {"password", "token", "secret", "api_key", "credential"}
    
    # 不记录日志的路径
    EXCLUDED_PATHS = {"/health", "/ready", "/metrics", "/favicon.ico"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求"""
        # 跳过不需要记录的路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 准备请求日志
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "query": str(request.url.query) if request.url.query else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
        }
        
        # 记录请求
        logger.info(f"Request started: {json.dumps(log_data, ensure_ascii=False)}")
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 准备响应日志
        log_data.update({
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        })
        
        # 根据状态码选择日志级别
        if response.status_code >= 500:
            logger.error(f"Request completed with error: {json.dumps(log_data, ensure_ascii=False)}")
        elif response.status_code >= 400:
            logger.warning(f"Request completed with client error: {json.dumps(log_data, ensure_ascii=False)}")
        else:
            logger.info(f"Request completed: {json.dumps(log_data, ensure_ascii=False)}")
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 优先从X-Forwarded-For获取
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # 其次从X-Real-IP获取
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 最后使用客户端地址
        if request.client:
            return request.client.host
        
        return "unknown"
