"""
错误处理中间件
统一处理应用中的错误和异常
"""

import logging
import traceback
from typing import Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    捕获并统一处理应用中的异常
    """
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        try:
            return await call_next(request)
        except Exception as exc:
            return await self._handle_exception(request, exc)
    
    async def _handle_exception(
        self,
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """处理异常"""
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 根据异常类型生成响应
        if isinstance(exc, HTTPException):
            return self._handle_http_exception(exc, request_id)
        
        if isinstance(exc, StarletteHTTPException):
            return self._handle_starlette_exception(exc, request_id)
        
        if isinstance(exc, RequestValidationError):
            return self._handle_validation_error(exc, request_id)
        
        # 其他异常
        return self._handle_generic_exception(exc, request, request_id)
    
    def _handle_http_exception(
        self,
        exc: HTTPException,
        request_id: str,
    ) -> JSONResponse:
        """处理HTTP异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "Error",
                "details": exc.detail if not isinstance(exc.detail, str) else None,
                "request_id": request_id,
            },
        )
    
    def _handle_starlette_exception(
        self,
        exc: StarletteHTTPException,
        request_id: str,
    ) -> JSONResponse:
        """处理Starlette HTTP异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request_id,
            },
        )
    
    def _handle_validation_error(
        self,
        exc: RequestValidationError,
        request_id: str,
    ) -> JSONResponse:
        """处理请求验证错误"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "details": errors,
                "request_id": request_id,
            },
        )
    
    def _handle_generic_exception(
        self,
        exc: Exception,
        request: Request,
        request_id: str,
    ) -> JSONResponse:
        """处理通用异常"""
        # 记录完整的错误信息
        logger.error(
            f"Unhandled exception: {exc}\n"
            f"Path: {request.url.path}\n"
            f"Method: {request.method}\n"
            f"Request ID: {request_id}\n"
            f"Traceback:\n{traceback.format_exc()}"
        )
        
        # 根据环境返回不同级别的错误信息
        is_debug = request.app.debug if hasattr(request.app, "debug") else False
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": str(exc) if is_debug else "An unexpected error occurred",
                "request_id": request_id,
            } if is_debug else {
                "error": "Internal Server Error",
                "request_id": request_id,
            },
        )


def create_error_response(
    status_code: int,
    message: str,
    details: dict = None,
    request_id: str = None,
) -> JSONResponse:
    """创建错误响应"""
    content = {
        "error": message,
        "request_id": request_id,
    }
    if details:
        content["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)


def validation_error_response(
    errors: list,
    request_id: str = None,
) -> JSONResponse:
    """创建验证错误响应"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": errors,
            "request_id": request_id,
        },
    )
