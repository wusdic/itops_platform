"""
BM-15 AI API路由单元测试
测试AI对话、故障排查等API端点
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.foundation.db_models.base import Base as FoundationBase
from modules.business.knowledge_base.models import Base as KBBases

# 合并所有 declarative base
import modules.business.knowledge_base.models  # 确保模块加载
all_bases = FoundationBase.__bases__ + (KBBases,)

# 测试数据库配置
TEST_DB_URL = 'sqlite:///:memory:'


@pytest.fixture
def db_engine():
    """创建测试数据库引擎（Mock模式下仅用于满足fixture依赖链）"""
    engine = create_engine(TEST_DB_URL, echo=False)
    FoundationBase.metadata.create_all(engine)
    KBBases.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """创建测试数据库会话"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_user():
    """创建模拟用户"""
    from modules.foundation.auth_manager.auth import UserStatus
    user = MagicMock()
    user.id = "u001"
    user.username = "testuser"
    user.email = "test@example.com"
    user.roles = ["admin"]
    user.status = UserStatus.ACTIVE
    user.metadata = {}
    user.last_login = datetime.now()
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    return user


@pytest.fixture
def app(db_session, mock_user):
    """创建测试FastAPI应用"""
    from api.routes.ai import router
    from api.dependencies import get_db, get_current_user, CurrentUser
    
    app = FastAPI()
    app.include_router(router, prefix="")
    
    # 覆盖依赖
    def override_get_db():
        yield db_session
    
    def override_get_current_user():
        return CurrentUser(
            user_id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            roles=mock_user.roles
        )
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestAIChatAPI:
    """AI对话接口测试"""
    
    @patch('api.start.get_llm_client')
    def test_chat_llm_unavailable(self, mock_get_client, client, mock_user):
        """测试LLM不可用时的降级处理"""
        mock_get_client.return_value = None
        
        request_data = {
            "message": "测试消息",
            "conversation_id": None,
            "stream": False
        }
        
        response = client.post("/chat", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is not None
        assert "suggestions" in data
        assert data["metadata"]["mode"] == "llm_unavailable"
    
    @patch('api.start.get_llm_client')
    def test_chat_with_conversation_id(self, mock_get_client, client, mock_user):
        """测试带会话ID的对话"""
        mock_get_client.return_value = None
        
        request_data = {
            "message": "测试消息",
            "conversation_id": "conv-123",
            "stream": False
        }
        
        response = client.post("/chat", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
    
    def test_chat_invalid_request(self, client, mock_user):
        """测试无效请求"""
        request_data = {
            "message": "",  # 消息为空
            "stream": False
        }
        
        # 空消息也会被处理，但返回降级模式
        response = client.post("/chat", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["mode"] == "llm_unavailable"


class TestConversationManagement:
    """会话管理接口测试"""
    
    def test_get_conversation(self, client, mock_user):
        """测试获取会话历史"""
        response = client.get("/conversation/conv-123?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
        assert "messages" in data
    
    def test_get_conversations_list(self, client, mock_user):
        """测试获取会话列表"""
        response = client.get("/conversations?limit=20")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_get_conversations_with_type_filter(self, client, mock_user):
        """测试按类型过滤会话"""
        response = client.get("/conversations?conversation_type=chat")
        assert response.status_code == 200
    
    def test_delete_conversation(self, client, mock_user):
        """测试删除会话"""
        response = client.delete("/conversation/conv-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestTroubleshootingAPI:
    """故障排查接口测试"""
    
    def test_troubleshoot_cpu_issue(self, client, mock_user, db_session):
        """测试CPU问题故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        # Mock session：query 返回空列表
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "CPU使用率过高，服务器负载异常",
                "device_id": 1,
                "device_name": "server-01"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "diagnosis" in data
            assert "confidence" in data
            assert "possible_causes" in data
            assert "suggested_steps" in data
            
            # 验证CPU问题被正确识别
            cpu_causes = [c for c in data["possible_causes"] if "CPU" in c or "cpu" in c.lower() or "负载" in c]
            assert len(cpu_causes) > 0
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_memory_issue(self, client, mock_user, db_session):
        """测试内存问题故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "内存泄漏导致系统变慢",
                "device_name": "db-server"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # 验证内存问题被正确识别
            memory_causes = [c for c in data["possible_causes"] if "内存" in c or "memory" in c.lower()]
            assert len(memory_causes) > 0
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_disk_issue(self, client, mock_user, db_session):
        """测试磁盘问题故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "磁盘空间不足",
                "device_ip": "192.168.1.10"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # 验证磁盘问题被正确识别
            disk_causes = [c for c in data["possible_causes"] if "磁盘" in c or "空间" in c]
            assert len(disk_causes) > 0
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_network_issue(self, client, mock_user, db_session):
        """测试网络问题故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "网络连接不通",
                "device_name": "router-01"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # 验证网络问题被正确识别
            network_causes = [c for c in data["possible_causes"] if "网络" in c or "连接" in c]
            assert len(network_causes) > 0
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_service_issue(self, client, mock_user, db_session):
        """测试服务问题故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "服务无法启动",
                "device_name": "app-server"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # 验证服务问题被正确识别
            service_causes = [c for c in data["possible_causes"] if "服务" in c or "启动" in c]
            assert len(service_causes) > 0
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_unknown_issue(self, client, mock_user, db_session):
        """测试未知问题故障排查（通用分析）"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "系统运行异常"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # 应该返回通用分析结果
            assert "diagnosis" in data
            assert "suggested_steps" in data
        finally:
            del client.app.dependency_overrides[get_db]
    
    def test_troubleshoot_with_error_logs(self, client, mock_user, db_session):
        """测试带错误日志的故障排查"""
        from unittest.mock import MagicMock
        from api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        def fake_get_db():
            yield mock_db

        client.app.dependency_overrides[get_db] = fake_get_db
        try:
            request_data = {
                "symptom": "服务异常",
                "error_logs": "Error: connection refused\nError: timeout"
            }
            
            response = client.post("/troubleshoot", json=request_data)
            assert response.status_code == 200
        finally:
            del client.app.dependency_overrides[get_db]


class TestAIEnums:
    """AI枚举测试"""
    
    def test_conversation_type_enum(self):
        """测试会话类型枚举"""
        from api.routes.ai import ConversationType
        
        assert ConversationType.CHAT.value == "chat"
        assert ConversationType.TROUBLESHOOTING.value == "troubleshooting"
        assert ConversationType.SUGGESTION.value == "suggestion"
        assert ConversationType.ANALYSIS.value == "analysis"
    
    def test_message_role_enum(self):
        """测试消息角色枚举"""
        from api.routes.ai import MessageRole
        
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"


class TestAIRequestModels:
    """AI请求模型测试"""
    
    def test_chat_request_model(self):
        """测试聊天请求模型"""
        from api.routes.ai import ChatRequest
        
        request = ChatRequest(
            message="测试消息",
            conversation_id="conv-123",
            conversation_type="chat",
            stream=False
        )
        
        assert request.message == "测试消息"
        assert request.conversation_id == "conv-123"
        assert request.stream == False
    
    def test_troubleshooting_request_model(self):
        """测试故障排查请求模型"""
        from api.routes.ai import TroubleshootingRequest
        
        request = TroubleshootingRequest(
            symptom="CPU使用率过高",
            device_name="server-01",
            error_logs="error log here"
        )
        
        assert request.symptom == "CPU使用率过高"
        assert request.device_name == "server-01"


class TestAIDebugEndpoint:
    """AI调试端点测试"""
    
    def test_chat_debug_endpoint(self, client):
        """测试调试端点存在"""
        request_data = {
            "message": "test",
            "stream": False
        }
        
        # 这个端点不依赖用户认证
        response = client.post("/chat/_debug", json=request_data)
        # 可能是500错误（因为调用外部服务），但端点本身应该可达
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
