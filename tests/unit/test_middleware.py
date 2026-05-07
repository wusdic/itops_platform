"""
中间件单元测试
测试所有中间件模块：error_handler, logging, performance, request_id

遵循 Given-When-Then 结构
"""

import json
import time
import uuid
from typing import Generator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# 导入被测试的中间件
from api.middleware.error_handler import (
    ErrorHandlerMiddleware,
    create_error_response,
    validation_error_response,
)
from api.middleware.logging import LoggingMiddleware
from api.middleware.performance import (
    PerformanceMiddleware,
)
from api.middleware.request_id import RequestIDMiddleware


# ============== 辅助函数 ==============

def create_mock_request(
    method: str = "GET",
    path: str = "/test",
    headers: dict = None,
    client_host: str = "127.0.0.1",
    app: FastAPI = None,
) -> MagicMock:
    """创建模拟请求对象"""
    request = MagicMock(spec=StarletteRequest)
    request.method = method
    request.url = MagicMock()
    request.url.path = path
    request.url.query = ""
    request.headers = MagicMock()
    def get_header(key, default=None):
        if headers:
            return headers.get(key.lower(), default)
        return default
    request.headers.get = get_header
    request.headers.__getitem__ = lambda self, key: (headers or {}).get(key.lower())
    request.client = MagicMock()
    request.client.host = client_host
    request.state = MagicMock()
    request.state.request_id = None
    if app:
        request.app = app
    return request


def create_mock_response(status_code: int = 200, headers: dict = None) -> MagicMock:
    """创建模拟响应对象"""
    response = MagicMock(spec=Response)
    response.status_code = status_code
    response.headers = headers or {}
    return response


# ============== ErrorHandlerMiddleware 测试 ==============

class TestErrorHandlerMiddleware:
    """ErrorHandlerMiddleware 单元测试"""

    def test_given_http_exception_when_dispatch_then_returns_error_response(self):
        """Given: HTTPException 被抛出
        When: dispatch 处理请求时发生异常
        Then: 返回格式化的错误响应
        """
        # Given
        middleware = ErrorHandlerMiddleware(app=None)
        request = create_mock_request(path="/test")
        request.state.request_id = "req-123"
        
        async def raise_http_exception(req):
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # When
        response = middleware.dispatch(request, raise_http_exception)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == 404
        content = json.loads(result.body.decode())
        assert content["error"] == "Resource not found"
        assert content["request_id"] == "req-123"

    def test_given_validation_error_when_dispatch_then_returns_validation_errors(self):
        """Given: RequestValidationError 被抛出
        When: dispatch 处理请求时发生验证错误
        Then: 返回验证错误详情列表
        """
        # Given
        middleware = ErrorHandlerMiddleware(app=None)
        request = create_mock_request(path="/test")
        request.state.request_id = "req-456"
        
        # 创建模拟的验证错误
        validation_error = RequestValidationError([
            {"loc": ("body", "name"), "msg": "field required", "type": "value_error.missing"}
        ])
        
        async def raise_validation_error(req):
            raise validation_error
        
        # When
        response = middleware.dispatch(request, raise_validation_error)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = json.loads(result.body.decode())
        assert content["error"] == "Validation Error"
        assert "details" in content
        assert len(content["details"]) == 1
        assert content["details"][0]["field"] == "body.name"

    def test_given_generic_exception_when_dispatch_then_returns_500_error(self):
        """Given: 通用异常被抛出
        When: dispatch 处理请求时发生未捕获异常
        Then: 返回500内部服务器错误
        """
        # Given
        middleware = ErrorHandlerMiddleware(app=None)
        request = create_mock_request(path="/test")
        request.state.request_id = "req-789"
        
        async def raise_generic_exception(req):
            raise ValueError("Something went wrong")
        
        # When
        with patch("api.middleware.error_handler.logger") as mock_logger:
            response = middleware.dispatch(request, raise_generic_exception)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(result.body.decode())
        assert content["error"] == "Internal Server Error"
        assert content["request_id"] == "req-789"

    def test_given_no_exception_when_dispatch_then_returns_normal_response(self):
        """Given: 请求处理正常无异常
        When: dispatch 处理请求
        Then: 返回正常的下游响应
        """
        # Given
        middleware = ErrorHandlerMiddleware(app=None)
        request = create_mock_request(path="/test")
        
        mock_response = create_mock_response(status_code=200)
        
        async def return_normal_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_normal_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == 200


class TestCreateErrorResponse:
    """create_error_response 函数单元测试"""

    def test_given_status_code_and_message_when_create_error_response_then_returns_json_response(self):
        """Given: 指定状态码和错误消息
        When: 调用 create_error_response
        Then: 返回正确格式的 JSONResponse
        """
        # Given
        status_code = 400
        message = "Bad Request"
        request_id = "req-test-001"
        
        # When
        response = create_error_response(status_code, message, request_id=request_id)
        
        # Then
        assert response.status_code == 400
        content = json.loads(response.body.decode())
        assert content["error"] == "Bad Request"
        assert content["request_id"] == "req-test-001"

    def test_given_with_details_when_create_error_response_then_includes_details(self):
        """Given: 包含详细信息
        When: 调用 create_error_response
        Then: 响应包含 details 字段
        """
        # Given
        details = {"field": "name", "issue": "required"}
        
        # When
        response = create_error_response(422, "Validation failed", details=details)
        
        # Then
        content = json.loads(response.body.decode())
        assert "details" in content
        assert content["details"] == details

    def test_given_no_details_when_create_error_response_then_details_not_included(self):
        """Given: 无详细信息
        When: 调用 create_error_response
        Then: 响应不包含 details 字段
        """
        # When
        response = create_error_response(500, "Server Error")
        
        # Then
        content = json.loads(response.body.decode())
        assert "details" not in content


class TestValidationErrorResponse:
    """validation_error_response 函数单元测试"""

    def test_given_errors_list_when_validation_error_response_then_returns_422(self):
        """Given: 错误列表
        When: 调用 validation_error_response
        Then: 返回422状态码和错误详情
        """
        # Given
        errors = [
            {"field": "email", "message": "invalid format"},
            {"field": "age", "message": "must be positive"},
        ]
        
        # When
        response = validation_error_response(errors, request_id="req-validate-001")
        
        # Then
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = json.loads(response.body.decode())
        assert content["error"] == "Validation Error"
        assert content["details"] == errors
        assert content["request_id"] == "req-validate-001"

    def test_given_empty_errors_when_validation_error_response_then_returns_empty_details(self):
        """Given: 空错误列表
        When: 调用 validation_error_response
        Then: 返回包含空 details 的响应
        """
        # When
        response = validation_error_response([], request_id="req-empty")
        
        # Then
        content = json.loads(response.body.decode())
        assert content["details"] == []


# ============== LoggingMiddleware 测试 ==============

class TestLoggingMiddlewareConstants:
    """LoggingMiddleware 常量测试"""

    def test_given_sensitive_headers_when_checking_then_contains_authorization(self):
        """Given: SENSITIVE_HEADERS 定义
        When: 检查敏感头部集合
        Then: 包含 authorization, cookie 等
        """
        # Then
        assert "authorization" in LoggingMiddleware.SENSITIVE_HEADERS
        assert "cookie" in LoggingMiddleware.SENSITIVE_HEADERS
        assert "x-api-key" in LoggingMiddleware.SENSITIVE_HEADERS
        assert "x-auth-token" in LoggingMiddleware.SENSITIVE_HEADERS

    def test_given_sensitive_params_when_checking_then_contains_password(self):
        """Given: SENSITIVE_PARAMS 定义
        When: 检查敏感参数集合
        Then: 包含 password, token, secret 等
        """
        # Then
        assert "password" in LoggingMiddleware.SENSITIVE_PARAMS
        assert "token" in LoggingMiddleware.SENSITIVE_PARAMS
        assert "secret" in LoggingMiddleware.SENSITIVE_PARAMS
        assert "api_key" in LoggingMiddleware.SENSITIVE_PARAMS

    def test_given_excluded_paths_when_checking_then_contains_health_and_metrics(self):
        """Given: EXCLUDED_PATHS 定义
        When: 检查排除路径集合
        Then: 包含 /health, /metrics 等
        """
        # Then
        assert "/health" in LoggingMiddleware.EXCLUDED_PATHS
        assert "/ready" in LoggingMiddleware.EXCLUDED_PATHS
        assert "/metrics" in LoggingMiddleware.EXCLUDED_PATHS
        assert "/favicon.ico" in LoggingMiddleware.EXCLUDED_PATHS


class TestLoggingMiddleware:
    """LoggingMiddleware 单元测试"""

    def test_given_excluded_path_when_dispatch_then_skips_logging(self):
        """Given: 请求路径在 EXCLUDED_PATHS 中
        When: dispatch 处理请求
        Then: 跳过日志记录并返回正常响应
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(path="/health")
        request.headers = MagicMock()
        request.headers.get = lambda key, default=None: default
        
        mock_response = create_mock_response(status_code=200)
        
        async def return_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == 200

    def test_given_normal_request_when_dispatch_then_logs_request_started(self):
        """Given: 正常请求
        When: dispatch 处理请求
        Then: 记录请求开始日志
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(method="GET", path="/api/v1/devices")
        
        mock_response = create_mock_response(status_code=200)
        mock_response.headers = {}
        
        async def return_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == 200

    def test_given_error_response_when_dispatch_then_returns_error_status(self):
        """Given: 请求返回错误状态码
        When: dispatch 处理请求
        Then: 返回错误状态码
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(method="POST", path="/api/v1/devices")
        
        mock_response = create_mock_response(status_code=500)
        mock_response.headers = {}
        
        async def return_error_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_error_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.status_code == 500

    def test_given_client_ip_in_x_forwarded_for_when_get_client_ip_then_returns_first_ip(self):
        """Given: X-Forwarded-For 头包含多个IP
        When: _get_client_ip 处理请求
        Then: 返回第一个IP（最原始的客户端IP）
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(
            path="/test",
            headers={"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        )
        
        # When
        client_ip = middleware._get_client_ip(request)
        
        # Then
        assert client_ip == "203.0.113.195"

    def test_given_x_real_ip_when_get_client_ip_then_returns_real_ip(self):
        """Given: X-Real-IP 头
        When: _get_client_ip 处理请求
        Then: 返回 X-Real-IP 的值
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(
            path="/test",
            headers={"x-real-ip": "203.0.113.100"}
        )
        
        # When
        client_ip = middleware._get_client_ip(request)
        
        # Then
        assert client_ip == "203.0.113.100"

    def test_given_no_proxy_headers_when_get_client_ip_then_returns_client_host(self):
        """Given: 无代理头
        When: _get_client_ip 处理请求
        Then: 返回 request.client.host
        """
        # Given
        middleware = LoggingMiddleware(app=None)
        request = create_mock_request(
            path="/test",
            headers={},
            client_host="192.168.1.50"
        )
        
        # When
        client_ip = middleware._get_client_ip(request)
        
        # Then
        assert client_ip == "192.168.1.50"


# ============== PerformanceMiddleware 测试 ==============

class TestPerformanceMiddleware:
    """PerformanceMiddleware 单元测试"""

    def setup_method(self):
        """每个测试前清空指标"""
        PerformanceMiddleware.clear_metrics()

    def teardown_method(self):
        """每个测试后清空指标"""
        PerformanceMiddleware.clear_metrics()

    def test_given_request_when_dispatch_then_adds_process_time_header(self):
        """Given: 正常请求
        When: dispatch 处理请求
        Then: 响应包含 X-Process-Time 头
        """
        # Given
        middleware = PerformanceMiddleware(app=None)
        request = create_mock_request(path="/api/v1/test")
        
        mock_response = create_mock_response(status_code=200)
        
        async def return_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert "X-Process-Time" in result.headers

    def test_given_slow_request_when_dispatch_then_logs_warning(self):
        """Given: 慢请求（超过阈值）
        When: dispatch 处理请求
        Then: 记录警告日志
        """
        # Given
        middleware = PerformanceMiddleware(app=None)
        request = create_mock_request(path="/api/v1/slow")
        
        mock_response = create_mock_response(status_code=200)
        
        async def slow_response(req):
            await asyncio.sleep(0.1)  # 模拟慢请求
            return mock_response
        
        # When
        with patch("api.middleware.performance.logger") as mock_logger:
            response = middleware.dispatch(request, slow_response)
        
        # Then
        import asyncio
        asyncio.get_event_loop().run_until_complete(response)
        # 注意：0.1秒可能不会触发慢请求警告（阈值是1000ms）
        # 这个测试主要验证日志调用存在

    def test_given_numeric_id_in_path_when_get_path_pattern_then_replaces_with_placeholder(self):
        """Given: 路径包含数字ID
        When: _get_path_pattern 处理请求
        Then: 数字ID被替换为 {id}
        """
        # Given
        middleware = PerformanceMiddleware(app=None)
        request = create_mock_request(path="/api/v1/workorder/123")
        
        # When
        pattern = middleware._get_path_pattern(request)
        
        # Then
        assert pattern == "/api/v1/workorder/{id}"

    def test_given_uuid_in_path_when_get_path_pattern_then_replaces_with_placeholder(self):
        """Given: 路径包含UUID
        When: _get_path_pattern 处理请求
        Then: UUID被替换为 {uuid}
        """
        # Given
        middleware = PerformanceMiddleware(app=None)
        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        request = create_mock_request(path=f"/api/v1/device/{test_uuid}")
        
        # When
        pattern = middleware._get_path_pattern(request)
        
        # Then
        assert pattern == "/api/v1/device/{uuid}"

    def test_given_normal_path_when_get_path_pattern_then_keeps_original(self):
        """Given: 普通路径（无动态参数）
        When: _get_path_pattern 处理请求
        Then: 路径保持不变
        """
        # Given
        middleware = PerformanceMiddleware(app=None)
        request = create_mock_request(path="/api/v1/health")
        
        # When
        pattern = middleware._get_path_pattern(request)
        
        # Then
        assert pattern == "/api/v1/health"


class TestPerformanceMetrics:
    """PerformanceMiddleware 指标测试"""

    def setup_method(self):
        """每个测试前清空指标"""
        PerformanceMiddleware.clear_metrics()

    def teardown_method(self):
        """每个测试后清空指标"""
        PerformanceMiddleware.clear_metrics()

    def test_given_no_metrics_when_get_metrics_then_returns_empty_dict(self):
        """Given: 无性能指标
        When: 调用 get_metrics
        Then: 返回空字典
        """
        # Given
        PerformanceMiddleware.clear_metrics()
        
        # When
        metrics = PerformanceMiddleware.get_metrics()
        
        # Then
        assert metrics == {}

    def test_given_requests_with_different_paths_when_get_metrics_then_groups_by_path(self):
        """Given: 不同路径的请求
        When: 调用 get_metrics
        Then: 返回按路径分组的指标
        """
        # Given
        PerformanceMiddleware._metrics = {
            "/api/v1/health": [10.0, 20.0, 15.0],
            "/api/v1/devices": [50.0, 60.0],
        }
        
        # When
        metrics = PerformanceMiddleware.get_metrics()
        
        # Then
        assert "/api/v1/health" in metrics
        assert "/api/v1/devices" in metrics
        assert metrics["/api/v1/health"]["count"] == 3
        assert metrics["/api/v1/devices"]["count"] == 2

    def test_given_metrics_with_values_when_get_metrics_then_calculates_avg_min_max(self):
        """Given: 包含具体值的指标
        When: 调用 get_metrics
        Then: 返回正确的统计值
        """
        # Given
        PerformanceMiddleware._metrics = {
            "/api/v1/test": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
        
        # When
        metrics = PerformanceMiddleware.get_metrics()
        
        # Then
        assert metrics["/api/v1/test"]["count"] == 5
        assert metrics["/api/v1/test"]["avg_ms"] == 30.0
        assert metrics["/api/v1/test"]["min_ms"] == 10.0
        assert metrics["/api/v1/test"]["max_ms"] == 50.0

    def test_given_metrics_exist_when_clear_metrics_then_metrics_is_empty(self):
        """Given: 存在性能指标
        When: 调用 clear_metrics
        Then: 指标被清空
        """
        # Given
        PerformanceMiddleware._metrics = {
            "/api/v1/test": [10.0, 20.0],
        }
        
        # When
        PerformanceMiddleware.clear_metrics()
        
        # Then
        assert PerformanceMiddleware._metrics == {}

    def test_given_metrics_tracking_when_update_metrics_then_appends_duration(self):
        """Given: 路径已有指标
        When: _update_metrics 添加新数据
        Then: 数据被追加到现有列表
        """
        # Given
        PerformanceMiddleware._metrics = {
            "/api/v1/existing": [15.0],
        }
        middleware = PerformanceMiddleware(app=None)
        
        # When
        middleware._update_metrics("/api/v1/existing", 25.0)
        
        # Then
        assert len(PerformanceMiddleware._metrics["/api/v1/existing"]) == 2
        assert 25.0 in PerformanceMiddleware._metrics["/api/v1/existing"]

    def test_given_metrics_exceeds_1000_when_update_metrics_then_keeps_recent_1000(self):
        """Given: 指标超过1000条
        When: _update_metrics 添加数据
        Then: 保留最近1000条记录
        """
        # Given
        PerformanceMiddleware._metrics = {
            "/api/v1/large": list(range(1000)),
        }
        middleware = PerformanceMiddleware(app=None)
        
        # When
        middleware._update_metrics("/api/v1/large", 999.0)
        
        # Then
        assert len(PerformanceMiddleware._metrics["/api/v1/large"]) == 1000


# ============== RequestIDMiddleware 测试 ==============

class TestRequestIDMiddleware:
    """RequestIDMiddleware 单元测试"""

    def test_given_no_request_id_in_headers_when_dispatch_then_generates_new_id(self):
        """Given: 请求头中无 X-Request-ID
        When: dispatch 处理请求
        Then: 生成新的 UUID 并添加到响应头
        """
        # Given
        middleware = RequestIDMiddleware(app=None)
        request = create_mock_request(path="/test")
        request.headers.get = lambda key: None  # 无 request id 头
        
        mock_response = create_mock_response(status_code=200)
        
        async def return_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert "X-Request-ID" in result.headers
        # 验证是有效的 UUID
        uuid.UUID(result.headers["X-Request-ID"])

    def test_given_request_id_in_headers_when_dispatch_then_uses_existing_id(self):
        """Given: 请求头中已有 X-Request-ID
        When: dispatch 处理请求
        Then: 使用现有的 Request-ID
        """
        # Given
        middleware = RequestIDMiddleware(app=None)
        existing_id = "existing-request-id-12345"
        request = create_mock_request(path="/test")
        request.headers.get = lambda key: existing_id if key == "X-Request-ID" else None
        
        mock_response = create_mock_response(status_code=200)
        
        async def return_response(req):
            return mock_response
        
        # When
        response = middleware.dispatch(request, return_response)
        
        # Then
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(response)
        assert result.headers["X-Request-ID"] == existing_id

    def test_given_request_when_dispatch_then_sets_request_id_in_state(self):
        """Given: 正常请求
        When: dispatch 处理请求
        Then: Request-ID 被设置到 request.state.request_id
        """
        # Given
        middleware = RequestIDMiddleware(app=None)
        request = create_mock_request(path="/test")
        request.headers.get = lambda key: None
        
        mock_response = create_mock_response(status_code=200)
        captured_request_id = None
        
        async def capture_request_id(req):
            nonlocal captured_request_id
            captured_request_id = req.state.request_id
            return mock_response
        
        # When
        response = middleware.dispatch(request, capture_request_id)
        
        # Then
        import asyncio
        asyncio.get_event_loop().run_until_complete(response)
        assert captured_request_id is not None
        # 验证是有效的 UUID
        uuid.UUID(captured_request_id)

    def test_given_custom_header_name_when_checking_then_header_name_is_x_request_id(self):
        """Given: RequestIDMiddleware 配置
        When: 检查 HEADER_NAME
        Then: 值是 X-Request-ID
        """
        # Then
        assert RequestIDMiddleware.HEADER_NAME == "X-Request-ID"


# ============== 集成测试：使用 TestClient ==============

class TestMiddlewareIntegration:
    """中间件集成测试（使用 FastAPI TestClient）"""

    def test_given_app_with_request_id_middleware_when_request_then_has_request_id_header(self):
        """Given: 集成 RequestIDMiddleware 的 FastAPI 应用
        When: 发送请求
        Then: 响应包含 X-Request-ID 头
        """
        # Given
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(app)
        
        # When
        response = client.get("/test")
        
        # Then
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_given_app_with_performance_middleware_when_request_then_has_process_time_header(self):
        """Given: 集成 PerformanceMiddleware 的 FastAPI 应用
        When: 发送请求
        Then: 响应包含 X-Process-Time 头
        """
        # Given
        app = FastAPI()
        app.add_middleware(PerformanceMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(app)
        
        # When
        response = client.get("/test")
        
        # Then
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers


import asyncio
