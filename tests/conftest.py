"""
Pytest配置和共享Fixture

遵循Google测试最佳实践:
- 80% 单元测试, 20% 集成测试
- 测试通过公共API, 不测试内部实现
- Given-When-Then结构
- DAMP (Descriptive And Meaningful Phrases) over DRY
"""

import os
import sys
from pathlib import Path
from typing import Generator
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============== 应用级别Fixture ==============

@pytest.fixture(scope="session")
def app():
    """创建FastAPI应用实例 (session级别，所有测试共享)"""
    from api.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="function")
def client(app) -> Generator:
    """
    创建TestClient实例 (function级别，每个测试独立)
    
    遵循原则: 测试隔离 - 每个测试获得全新的客户端实例
    """
    with TestClient(app) as test_client:
        yield test_client


# ============== 认证Fixture ==============

@pytest.fixture
def admin_headers(client) -> dict:
    """获取管理员认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers(client) -> dict:
    """获取运维人员认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "operator123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(client) -> dict:
    """获取访客认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "viewer123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============== 测试数据Fixture ==============

@pytest.fixture
def sample_device():
    """示例设备数据"""
    return {
        "name": "test-server-001",
        "ip_address": "192.168.1.100",
        "device_type": "server",
        "protocol": "snmp",
        "community": "public",
        "category": "windows",
        "location": "DataCenter-A",
        "status": "active"
    }


@pytest.fixture
def sample_workorder():
    """示例工单数据"""
    return {
        "title": "测试工单 - 服务器故障",
        "description": "服务器无法连接，需要检查",
        "priority": "high",
        "category": "hardware",
        "assignee": "operator"
    }


@pytest.fixture
def sample_alert():
    """示例告警数据"""
    return {
        "name": "CPU使用率过高",
        "severity": "warning",
        "source": "test-server-001",
        "metric": "cpu_usage",
        "threshold": 80,
        "current_value": 95
    }


# ============== Mock Fixture ==============

@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add.return_value = None
    session.commit.return_value = None
    return session


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock


# ============== 响应断言辅助 ==============

def assert_response_ok(response, data_keys=None):
    """断言响应成功 (2xx)"""
    assert response.status_code < 300, f"Expected success, got {response.status_code}: {response.text}"
    if data_keys:
        data = response.json()
        for key in data_keys:
            assert key in data, f"Expected key '{key}' in response"


def assert_response_error(response, status_code=None):
    """断言响应失败 (4xx/5xx)"""
    if status_code:
        assert response.status_code == status_code, f"Expected {status_code}, got {response.status_code}"
    else:
        assert response.status_code >= 400, f"Expected error, got {response.status_code}"


# ============== Pytest Hooks ==============

def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "unit: Unit tests (isolated, fast)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end business flow tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")


def pytest_collection_modifyitems(items):
    """自动为测试添加标记"""
    for item in items:
        # 根据测试路径自动添加标记
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath) or "flow" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        # 根据测试名称添加标记
        if "slow" in item.name or "stress" in item.name:
            item.add_marker(pytest.mark.slow)
