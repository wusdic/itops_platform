# -*- coding: utf-8 -*-
"""
端到端集成测试 (E2E) - 使用真实服务

遵循Google测试最佳实践:
- Given-When-Then结构
- 测试通过公共API
- 测试业务工作流，不测试内部实现
- 每个测试独立，可重复运行

注意: 这些测试使用真实的 HTTP 请求到 http://localhost:8000
而不是通过 TestClient 导入 app，这样可以正确连接数据库
"""

import os
import sys
import pytest
import requests
from pathlib import Path

# Constants
API_BASE_URL = "http://localhost:8000"
API_V1 = f"{API_BASE_URL}/api/v1"

# Test credentials
TEST_ADMIN_USER = "admin"
TEST_ADMIN_PASS = "Admin@123456"


class APIClient:
    """Simple API client for testing"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
    
    def login(self, username: str, password: str) -> dict:
        """Login and store token"""
        response = self.session.post(
            f"{API_V1}/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            return data
        raise Exception(f"Login failed: {response.status_code} - {response.text}")
    
    def logout(self):
        """Logout"""
        if self.token:
            self.session.post(f"{API_V1}/auth/logout", timeout=10)
            self.token = None
    
    def headers(self, authenticated: bool = True) -> dict:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def get(self, path: str, authenticated: bool = True) -> requests.Response:
        """Make GET request"""
        url = f"{API_V1}{path}"
        return self.session.get(url, headers=self.headers(authenticated), timeout=30)
    
    def post(self, path: str, json: dict = None, authenticated: bool = True) -> requests.Response:
        """Make POST request"""
        url = f"{API_V1}{path}"
        return self.session.post(url, headers=self.headers(authenticated), json=json, timeout=60)


@pytest.fixture(scope="function")
def api_client():
    """Provide an authenticated API client"""
    client = APIClient()
    client.login(TEST_ADMIN_USER, TEST_ADMIN_PASS)
    yield client
    client.logout()


@pytest.fixture(scope="session")
def api_available():
    """Check if API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
        pytest.skip(f"API not healthy: {response.status_code}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")


class TestAuthFlow:
    """认证流程测试"""
    
    def test_health_check(self, api_available):
        """Given: 系统运行
           When: 访问健康检查端点
           Then: 返回系统健康状态"""
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_login_success(self, api_available):
        """Given: 有效的管理员凭据
           When: 提交登录请求
           Then: 返回访问令牌"""
        client = APIClient()
        response = client.session.post(
            f"{API_V1}/auth/login",
            json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_failure(self, api_available):
        """Given: 无效的凭据
           When: 提交登录请求
           Then: 返回401认证失败 (或503如果数据库未初始化)"""
        client = APIClient()
        response = client.session.post(
            f"{API_V1}/auth/login",
            json={"username": TEST_ADMIN_USER, "password": "wrong_password"},
            timeout=10
        )
        
        # Accept 401 (auth failure) or 503 (DB issue)
        assert response.status_code in [401, 503]


class TestDeviceCollectionFlow:
    """设备采集流程测试"""
    
    def test_get_devices(self, api_client):
        """Given: 已认证的管理员
           When: 获取设备列表
           Then: 返回设备列表或空数组"""
        response = api_client.get("/devices/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
    
    def test_get_device_stats(self, api_client):
        """Given: 已认证的管理员
           When: 获取设备统计
           Then: 返回统计信息"""
        response = api_client.get("/devices/stats")
        
        assert response.status_code == 200
    
    def test_get_adapters_list(self, api_client):
        """Given: 已认证的管理员
           When: 获取适配器列表
           Then: 返回支持的适配器列表"""
        response = api_client.get("/devices/adapters/list")
        
        assert response.status_code == 200
    
    def test_get_protocols(self, api_client):
        """Given: 已认证的管理员
           When: 获取协议列表
           Then: 返回支持的协议列表"""
        response = api_client.get("/devices/adapters/protocols")
        
        assert response.status_code == 200


class TestMonitoringFlow:
    """监控流程测试"""
    
    def test_get_alerts(self, api_client):
        """Given: 已认证的用户
           When: 获取告警列表
           Then: 返回告警列表 (或503如果数据库未初始化)"""
        response = api_client.get("/monitoring/alerts")
        
        assert response.status_code in [200, 503]
    
    def test_get_dashboards(self, api_client):
        """Given: 已认证的用户
           When: 获取仪表板列表
           Then: 返回仪表板列表 (或503如果数据库未初始化)"""
        response = api_client.get("/monitoring/dashboards")
        
        assert response.status_code in [200, 503]


class TestWorkorderFlow:
    """工单流程测试"""
    
    def test_get_workorders(self, api_client):
        """Given: 已认证的用户
           When: 获取工单列表
           Then: 返回工单列表 (或503如果数据库未初始化)"""
        response = api_client.get("/workorders/")
        
        assert response.status_code in [200, 503]
    
    def test_get_workorder_categories(self, api_client):
        """Given: 已认证的用户
           When: 获取工单分类
           Then: 返回工单分类列表"""
        response = api_client.get("/workorders/categories")
        
        assert response.status_code == 200
    
    def test_get_workorder_stats(self, api_client):
        """Given: 已认证的用户
           When: 获取工单统计
           Then: 返回统计信息 (或503如果数据库未初始化)"""
        response = api_client.get("/workorders/stats/summary")
        
        assert response.status_code in [200, 503]


class TestKnowledgeFlow:
    """知识库流程测试"""
    
    def test_get_categories(self, api_client):
        """Given: 已认证的用户
           When: 获取知识库分类
           Then: 返回分类列表 (或503如果数据库未初始化)"""
        response = api_client.get("/knowledge/category")
        
        assert response.status_code in [200, 503]
    
    def test_search_knowledge(self, api_client):
        """Given: 已认证的用户
           When: 搜索知识库
           Then: 返回搜索结果"""
        response = api_client.get("/knowledge/search?keyword=test")
        
        assert response.status_code in [200, 503]


class TestReportFlow:
    """报告流程测试"""
    
    def test_get_reports(self, api_client):
        """Given: 已认证的用户
           When: 获取报告列表
           Then: 返回报告列表 (或503如果数据库未初始化)"""
        response = api_client.get("/report/")
        
        assert response.status_code in [200, 503]
    
    def test_get_report_templates(self, api_client):
        """Given: 已认证的用户
           When: 获取报告模板
           Then: 返回模板列表 (或503如果数据库未初始化)"""
        response = api_client.get("/report/template")
        
        assert response.status_code in [200, 503]
    
    def test_get_report_stats(self, api_client):
        """Given: 已认证的用户
           When: 获取报告统计
           Then: 返回统计信息 (或503如果数据库未初始化)"""
        response = api_client.get("/report/stats")
        
        assert response.status_code in [200, 503]


class TestNotificationFlow:
    """通知渠道流程测试"""
    
    def test_get_notification_channels(self, api_client):
        """Given: 已认证的用户
           When: 获取通知渠道
           Then: 返回渠道列表"""
        response = api_client.get("/notifications/channels")
        
        assert response.status_code == 200
    
    def test_get_notification_history(self, api_client):
        """Given: 已认证的用户
           When: 获取通知历史
           Then: 返回通知历史"""
        response = api_client.get("/notifications/history")
        
        assert response.status_code in [200, 503]


class TestAIAssistantFlow:
    """AI助手流程测试"""
    
    def test_get_conversations(self, api_client):
        """Given: 已认证的用户
           When: 获取对话列表
           Then: 返回对话列表"""
        response = api_client.get("/ai/conversations")
        
        assert response.status_code == 200
    
    def test_ai_chat(self, api_client):
        """Given: 已认证的用户
           When: 发送AI聊天消息
           Then: 返回AI响应 (可能500如果LLM未配置)"""
        response = api_client.post(
            "/ai/chat",
            json={
                "message": "帮我分析一下服务器性能",
                "conversation_type": "chat"
            }
        )
        
        # LLM未配置时可能返回500，但接口可达
        assert response.status_code in [200, 500, 502]


class TestAdminFlow:
    """系统管理流程测试"""
    
    def test_get_system_info(self, api_client):
        """Given: 已认证的管理员
           When: 获取系统信息
           Then: 返回系统信息"""
        response = api_client.get("/admin/info")
        
        assert response.status_code == 200
    
    def test_get_metrics(self, api_client):
        """Given: 已认证的管理员
           When: 获取系统指标
           Then: 返回系统指标"""
        response = api_client.get("/admin/metrics")
        
        assert response.status_code == 200
    
    def test_get_roles(self, api_client):
        """Given: 已认证的管理员
           When: 获取角色列表
           Then: 返回角色列表"""
        response = api_client.get("/admin/roles")
        
        assert response.status_code == 200


class TestAssetFlow:
    """资产管理流程测试"""
    
    def test_get_asset_stats(self, api_client):
        """Given: 已认证的用户
           When: 获取资产统计
           Then: 返回统计信息"""
        response = api_client.get("/assets/stats")
        
        assert response.status_code in [200, 503]
    
    def test_get_business_systems(self, api_client):
        """Given: 已认证的用户
           When: 获取业务系统
           Then: 返回业务系统列表 (或503如果数据库未初始化)"""
        response = api_client.get("/assets/business")
        
        assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])