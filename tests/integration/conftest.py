"""
集成测试专用 conftest

提供集成测试级别的 fixture：
- 完整 FastAPI 应用上下文（绕过真实数据库连接）
- 认证辅助
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# App Fixture
# ============================================================================

@pytest.fixture(scope="module")
def app():
    """创建 FastAPI 应用（module 级共享）"""
    
    # Mock DatabaseManager - 项目没有 redis_client 模块
    db_mock = MagicMock()
    db_engine_mock = MagicMock()
    db_mock._engine = db_engine_mock
    db_mock._session_factory = MagicMock()
    db_mock._connected = True
    db_mock.get_session.return_value = MagicMock()
    db_mock.execute_query.return_value = MagicMock(fetchall=MagicMock(return_value=[]))
    db_mock.execute_command.return_value = MagicMock(rowcount=0)
    db_mock.setup.return_value = None
    
    # Mock engine's connect
    db_engine_mock.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
    db_engine_mock.connect.return_value.__exit__ = MagicMock(return_value=False)
    
    with patch("modules.foundation.db_models.base.DatabaseManager", return_value=db_mock):
        with patch("modules.foundation.db_models.base._db_manager", db_mock):
            with patch("modules.foundation.db_models.base.get_engine", return_value=db_engine_mock):
                # 延迟导入避免触发模块级连接
                from api.main import app as fastapi_app
                yield fastapi_app


@pytest.fixture(scope="module")
def client(app):
    """创建 TestClient"""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


# ============================================================================
# 认证辅助
# ============================================================================

@pytest.fixture
def admin_token(client) -> str:
    """获取管理员 token"""
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "***"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("access_token", "mock_admin_token")
    except Exception:
        pass
    return "mock_admin_token"


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """获取管理员认证头"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_headers() -> dict:
    """运维人员认证头"""
    return {"Authorization": "Bearer mock_operator_token"}


@pytest.fixture
def viewer_headers() -> dict:
    """访客认证头"""
    return {"Authorization": "Bearer mock_viewer_token"}


# ============================================================================
# 响应断言
# ============================================================================

def assert_response_ok(response, data_keys=None):
    """断言响应成功 (2xx)"""
    assert response.status_code < 300, f"Expected success, got {response.status_code}: {response.text[:200]}"
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
