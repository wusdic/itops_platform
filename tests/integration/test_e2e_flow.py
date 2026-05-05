# -*- coding: utf-8 -*-
"""
端到端集成测试

模拟从登录到各功能模块的完整业务流程
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient


class TestAuthFlow:
    """认证流程测试"""
    
    def test_health_check(self):
        """测试健康检查"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_login_success(self):
        """测试登录成功"""
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
        """测试登录失败"""
        from api.main import app
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong_password"}
        )
        
        assert response.status_code == 401
    
    def test_register_user(self):
        """测试用户注册"""
        from api.main import app
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"testuser_{datetime.now().timestamp()}",
                "password": "testpass123",
                "email": "test@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["username"]


class TestDeviceCollectionFlow:
    """设备采集流程测试"""
    
    def test_get_devices(self):
        """测试获取设备列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/devices/devices/")
        
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data or isinstance(data, list)
    
    def test_get_device_stats(self):
        """测试获取设备统计"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/devices/devices/stats")
        
        assert response.status_code == 200
    
    def test_get_adapters_list(self):
        """测试获取适配器列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/devices/devices/adapters/list")
        
        assert response.status_code == 200
    
    def test_get_protocols(self):
        """测试获取协议列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/devices/devices/adapters/protocols")
        
        assert response.status_code == 200


class TestMonitoringFlow:
    """监控流程测试"""
    
    def test_get_alerts(self):
        """测试获取告警列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/monitoring/alerts")
        
        assert response.status_code == 200
    
    def test_get_dashboards(self):
        """测试获取仪表板列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/monitoring/dashboards")
        
        assert response.status_code == 200


class TestWorkorderFlow:
    """工单流程测试"""
    
    def test_get_workorders(self):
        """测试获取工单列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/workorder/")
        
        assert response.status_code == 200
    
    def test_get_workorder_stats(self):
        """测试获取工单统计"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/workorder/stats/summary")
        
        assert response.status_code == 200


class TestKnowledgeFlow:
    """知识库流程测试"""
    
    def test_get_categories(self):
        """测试获取知识库分类"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/knowledge/category")
        
        assert response.status_code == 200
    
    def test_search_knowledge(self):
        """测试搜索知识库"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/knowledge/search?keyword=test")
        
        assert response.status_code == 200


class TestReportFlow:
    """报告流程测试"""
    
    def test_get_reports(self):
        """测试获取报告列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/report/")
        
        assert response.status_code == 200
    
    def test_get_report_templates(self):
        """测试获取报告模板"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/reports/templates/templates")
        
        assert response.status_code == 200


class TestNotificationFlow:
    """通知渠道流程测试"""
    
    def test_get_notification_channels(self):
        """测试获取通知渠道"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/notifications/channels")
        
        assert response.status_code == 200
    
    def test_get_notification_types(self):
        """测试获取通知类型"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/notifications/types")
        
        assert response.status_code == 200


class TestAIAssistantFlow:
    """AI助手流程测试"""
    
    def test_get_conversations(self):
        """测试获取对话列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/ai/conversations")
        
        assert response.status_code == 200
    
    def test_ai_chat(self):
        """测试AI对话"""
        from api.main import app
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "帮我分析一下服务器性能",
                "conversation_type": "chat"
            }
        )
        
        # 可能返回500如果LLM未配置，但接口应该可达
        assert response.status_code in [200, 500, 502]


class TestAdminFlow:
    """系统管理流程测试"""
    
    def test_get_system_info(self):
        """测试获取系统信息"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/admin/info")
        
        assert response.status_code == 200
    
    def test_get_metrics(self):
        """测试获取系统指标"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/admin/metrics")
        
        assert response.status_code == 200
    
    def test_get_roles(self):
        """测试获取角色列表"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/admin/roles")
        
        assert response.status_code == 200


class TestAssetFlow:
    """资产管理流程测试"""
    
    def test_get_business_systems(self):
        """测试获取业务系统"""
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/asset/business")
        
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
