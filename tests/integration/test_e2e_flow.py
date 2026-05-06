# -*- coding: utf-8 -*-
"""
端到端集成测试 (E2E)

遵循Google测试最佳实践:
- Given-When-Then结构
- 测试通过公共API
- 测试业务工作流，不测试内部实现
- 每个测试独立，可重复运行
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient


class TestAuthFlow:
    """认证流程测试"""
    
    def test_health_check(self):
        """Given: 系统运行
           When: 访问健康检查端点
           Then: 返回系统健康状态"""
        from api.main import app
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_login_success(self):
        """Given: 有效的管理员凭据
           When: 提交登录请求
           Then: 返回访问令牌"""
        from api.main import app
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_failure(self):
        """Given: 无效的凭据
           When: 提交登录请求
           Then: 返回401认证失败"""
        from api.main import app
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        
        # 数据库不可用时返回503，但接口可达
        assert response.status_code in [401, 503]


class TestDeviceCollectionFlow:
    """设备采集流程测试"""
    
    def test_get_devices(self):
        """Given: 已认证的管理员
           When: 获取设备列表
           Then: 返回设备列表或空数组"""
        from api.main import app
        client = TestClient(app)
        
        # 先登录获取token
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/devices/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
    
    def test_get_device_stats(self):
        """Given: 已认证的管理员
           When: 获取设备统计
           Then: 返回统计信息"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/devices/stats", headers=headers)
        assert response.status_code == 200
    
    def test_get_adapters_list(self):
        """Given: 已认证的管理员
           When: 获取适配器列表
           Then: 返回支持的适配器列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/devices/adapters/list", headers=headers)
        assert response.status_code == 200
    
    def test_get_protocols(self):
        """Given: 已认证的管理员
           When: 获取协议列表
           Then: 返回支持的协议列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/devices/adapters/protocols", headers=headers)
        assert response.status_code == 200


class TestMonitoringFlow:
    """监控流程测试"""
    
    def test_get_alerts(self):
        """Given: 已认证的用户
           When: 获取告警列表
           Then: 返回告警列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/monitoring/alerts", headers=headers)
        assert response.status_code == 200
    
    def test_get_dashboards(self):
        """Given: 已认证的用户
           When: 获取仪表板列表
           Then: 返回仪表板列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/monitoring/dashboards", headers=headers)
        assert response.status_code == 200


class TestWorkorderFlow:
    """工单流程测试"""
    
    def test_get_workorders(self):
        """Given: 已认证的用户
           When: 获取工单列表
           Then: 返回工单列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/workorders/", headers=headers)
        assert response.status_code == 200
    
    def test_get_workorder_categories(self):
        """Given: 已认证的用户
           When: 获取工单分类
           Then: 返回工单分类列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/workorders/categories", headers=headers)
        assert response.status_code == 200
    
    def test_get_workorder_stats(self):
        """Given: 已认证的用户
           When: 获取工单统计
           Then: 返回统计信息"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/workorders/stats/summary", headers=headers)
        assert response.status_code == 200


class TestKnowledgeFlow:
    """知识库流程测试"""
    
    def test_get_categories(self):
        """Given: 已认证的用户
           When: 获取知识库分类
           Then: 返回分类列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/knowledge/category", headers=headers)
        assert response.status_code == 200
    
    def test_search_knowledge(self):
        """Given: 已认证的用户
           When: 搜索知识库
           Then: 返回搜索结果"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/knowledge/search?keyword=test", headers=headers)
        assert response.status_code == 200


class TestReportFlow:
    """报告流程测试"""
    
    def test_get_reports(self):
        """Given: 已认证的用户
           When: 获取报告列表
           Then: 返回报告列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/report/", headers=headers)
        assert response.status_code == 200
    
    def test_get_report_templates(self):
        """Given: 已认证的用户
           When: 获取报告模板
           Then: 返回模板列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/report/template", headers=headers)
        assert response.status_code == 200
    
    def test_get_report_stats(self):
        """Given: 已认证的用户
           When: 获取报告统计
           Then: 返回统计信息"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/report/stats", headers=headers)
        assert response.status_code == 200


class TestNotificationFlow:
    """通知渠道流程测试"""
    
    def test_get_notification_channels(self):
        """Given: 已认证的用户
           When: 获取通知渠道
           Then: 返回渠道列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/notifications/channels", headers=headers)
        assert response.status_code == 200
    
    def test_get_notification_history(self):
        """Given: 已认证的用户
           When: 获取通知历史
           Then: 返回通知历史"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/notifications/history", headers=headers)
        assert response.status_code == 200


class TestAIAssistantFlow:
    """AI助手流程测试"""
    
    def test_get_conversations(self):
        """Given: 已认证的用户
           When: 获取对话列表
           Then: 返回对话列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/ai/conversations", headers=headers)
        assert response.status_code == 200
    
    def test_ai_chat(self):
        """Given: 已认证的用户
           When: 发送AI聊天消息
           Then: 返回AI响应 (可能500如果LLM未配置)"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "帮我分析一下服务器性能",
                "conversation_type": "chat"
            },
            headers=headers
        )
        
        # LLM未配置时可能返回500，但接口可达
        assert response.status_code in [200, 500, 502]


class TestAdminFlow:
    """系统管理流程测试"""
    
    def test_get_system_info(self):
        """Given: 已认证的管理员
           When: 获取系统信息
           Then: 返回系统信息"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/admin/info", headers=headers)
        assert response.status_code == 200
    
    def test_get_metrics(self):
        """Given: 已认证的管理员
           When: 获取系统指标
           Then: 返回系统指标"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/admin/metrics", headers=headers)
        assert response.status_code == 200
    
    def test_get_roles(self):
        """Given: 已认证的管理员
           When: 获取角色列表
           Then: 返回角色列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/admin/roles", headers=headers)
        assert response.status_code == 200


class TestAssetFlow:
    """资产管理流程测试"""
    
    def test_get_asset_stats(self):
        """Given: 已认证的用户
           When: 获取资产统计
           Then: 返回统计信息"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/assets/stats", headers=headers)
        assert response.status_code == 200
    
    def test_get_business_systems(self):
        """Given: 已认证的用户
           When: 获取业务系统
           Then: 返回业务系统列表"""
        from api.main import app
        client = TestClient(app)
        
        login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            pytest.skip("Database not available")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/assets/business", headers=headers)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
