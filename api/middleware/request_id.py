"""
请求ID跟踪中间件
为每个请求生成唯一ID，便于日志追踪
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    为每个请求生成唯一的X-Request-ID
    """
    
    HEADER_NAME = "X-Request-ID"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求"""
        # 获取或生成请求ID
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 将请求ID存储到请求状态中
        request.state.request_id = request_id
        
        # 处理请求
        response = await call_next(request)
        
        # 在响应头中添加请求ID
        response.headers[self.HEADER_NAME] = request_id
        
        return response
