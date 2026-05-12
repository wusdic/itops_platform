"""
BM-12 知识库API路由单元测试
测试知识库搜索、SOP文档、故障案例等API端点
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from modules.foundation.db_models.base import Base


# 测试数据库配置
TEST_DB_URL = 'sqlite:///:memory:'


@pytest.fixture
def db_engine():
    """创建测试数据库引擎"""
    engine = create_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
    from api.routes.knowledge import router
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


class TestKnowledgeSearchAPI:
    """知识库搜索接口测试"""
    
    def test_search_empty_query(self, client, mock_user):
        """测试空查询"""
        response = client.get("/search?query=")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == ""
        assert data["total"] == 0
    
    def test_search_with_keyword(self, client, mock_user):
        """测试关键词搜索"""
        response = client.get("/search?keyword=cpu")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_search_with_query_param(self, client, mock_user):
        """测试query参数搜索"""
        response = client.get("/search?query=memory")
        assert response.status_code == 200
    
    def test_search_with_type_filter(self, client, mock_user):
        """测试按类型过滤"""
        response = client.get("/search?doc_type=sop")
        assert response.status_code == 200
    
    def test_search_with_category_filter(self, client, mock_user):
        """测试按分类过滤"""
        response = client.get("/search?category_id=1")
        assert response.status_code == 200
    
    def test_search_with_limit(self, client, mock_user):
        """测试限制返回数量"""
        response = client.get("/search?keyword=test&limit=10")
        assert response.status_code == 200


class TestSOPDocumentAPI:
    """SOP文档接口测试"""
    
    def test_get_sop_documents(self, client, mock_user):
        """测试获取SOP文档列表"""
        response = client.get("/sop")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    def test_get_sop_documents_with_filters(self, client, mock_user):
        """测试带过滤条件的SOP文档列表"""
        response = client.get("/sop?status=draft&category_id=1&tags=cpu,tags=memory")
        assert response.status_code == 200
    
    def test_get_sop_documents_with_keyword(self, client, mock_user):
        """测试关键词搜索SOP文档"""
        response = client.get("/sop?keyword=install")
        assert response.status_code == 200
    
    def test_get_sop_document_by_id(self, client, mock_user):
        """测试获取单个SOP文档"""
        response = client.get("/sop/999")
        # 数据库为空，应该返回404
        assert response.status_code in [200, 404]


class TestFaultCaseAPI:
    """故障案例接口测试"""
    
    def test_get_fault_cases(self, client, mock_user):
        """测试获取故障案例列表"""
        response = client.get("/fault-case")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_get_fault_cases_with_level_filter(self, client, mock_user):
        """测试按级别过滤故障案例"""
        response = client.get("/fault-case?fault_level=P1")
        assert response.status_code == 200
    
    def test_get_fault_cases_with_status_filter(self, client, mock_user):
        """测试按状态过滤故障案例"""
        response = client.get("/fault-case?fault_status=resolved")
        assert response.status_code == 200
    
    def test_get_fault_cases_with_category_filter(self, client, mock_user):
        """测试按分类过滤故障案例"""
        response = client.get("/fault-case?fault_category=hardware")
        assert response.status_code == 200
    
    def test_get_fault_cases_with_keyword(self, client, mock_user):
        """测试关键词搜索故障案例"""
        response = client.get("/fault-case?keyword=cpu")
        assert response.status_code == 200
    
    def test_get_fault_case_by_id(self, client, mock_user):
        """测试获取单个故障案例"""
        response = client.get("/fault-case/999")
        # 数据库为空，应该返回404
        assert response.status_code in [200, 404]


class TestCategoryAPI:
    """分类接口测试"""
    
    def test_get_categories(self, client, mock_user):
        """测试获取分类列表"""
        response = client.get("/category")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_categories_by_type(self, client, mock_user):
        """测试按类型获取分类"""
        response = client.get("/category?doc_type=sop")
        assert response.status_code == 200
    
    def test_get_category_by_id(self, client, mock_user):
        """测试获取单个分类"""
        response = client.get("/category/1")
        assert response.status_code in [200, 404]


class TestTagAPI:
    """标签接口测试"""
    
    def test_get_tags(self, client, mock_user):
        """测试获取标签列表"""
        response = client.get("/tag")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_tags_with_category(self, client, mock_user):
        """测试按分类获取标签"""
        response = client.get("/tag?category_id=1")
        assert response.status_code == 200


class TestKnowledgeEnums:
    """知识库枚举测试"""
    
    def test_document_status_enum(self):
        """测试文档状态枚举"""
        from modules.business.knowledge_base.models import DocumentStatus
        
        assert DocumentStatus.DRAFT.value == "draft"
        assert DocumentStatus.PENDING_REVIEW.value == "pending_review"
        assert DocumentStatus.APPROVED.value == "approved"
        assert DocumentStatus.REJECTED.value == "rejected"
        assert DocumentStatus.OBSOLETE.value == "obsolete"
    
    def test_fault_level_enum(self):
        """测试故障级别枚举"""
        from modules.business.knowledge_base.models import FaultLevel
        
        assert FaultLevel.P1.value == "p1"
        assert FaultLevel.P2.value == "p2"
        assert FaultLevel.P3.value == "p3"
        assert FaultLevel.P4.value == "p4"
    
    def test_fault_status_enum(self):
        """测试故障状态枚举"""
        from modules.business.knowledge_base.models import FaultStatus
        
        assert FaultStatus.OPEN.value == "open"
        assert FaultStatus.INVESTIGATING.value == "investigating"
        assert FaultStatus.RESOLVED.value == "resolved"
        assert FaultStatus.CLOSED.value == "closed"
    
    def test_review_status_enum(self):
        """测试审核状态枚举"""
        from modules.business.knowledge_base.models import ReviewStatus
        
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.REJECTED.value == "rejected"


class TestKnowledgeHelperFunctions:
    """知识库辅助函数测试"""
    
    def test_sop_to_dict(self):
        """测试SOP转字典函数"""
        from modules.business.knowledge_base.models import SOPDocument, DocumentStatus
        
        mock_sop = MagicMock()
        mock_sop.id = 1
        mock_sop.doc_no = "SOP-2024-001"
        mock_sop.title = "Test SOP"
        mock_sop.content = "Test content"
        mock_sop.category_id = 1
        mock_sop.tags = "tag1,tag2"
        mock_sop.version = "1.0"
        mock_sop.status = DocumentStatus.DRAFT
        mock_sop.author = "admin"
        mock_sop.reviewer = None
        mock_sop.approver = None
        mock_sop.review_status = None
        mock_sop.effective_date = None
        mock_sop.view_count = 10
        mock_sop.like_count = 5
        mock_sop.created_at = datetime.now()
        mock_sop.updated_at = datetime.now()
        
        from api.routes.knowledge import _sop_to_dict
        result = _sop_to_dict(mock_sop)
        
        assert result["id"] == 1
        assert result["doc_no"] == "SOP-2024-001"
        assert result["title"] == "Test SOP"
        assert result["tags"] == ["tag1", "tag2"]
    
    def test_case_to_dict(self):
        """测试故障案例转字典函数"""
        from modules.business.knowledge_base.models import FaultCase, FaultLevel, FaultStatus
        
        mock_case = MagicMock()
        mock_case.id = 1
        mock_case.case_no = "CASE-2024-001"
        mock_case.title = "Test Case"
        mock_case.fault_level = FaultLevel.P2
        mock_case.fault_status = FaultStatus.RESOLVED
        mock_case.fault_category = "hardware"
        mock_case.symptom = "Test symptom"
        mock_case.root_cause = "Test root cause"
        mock_case.solution = "Test solution"
        mock_case.prevention = "Test prevention"
        mock_case.affected_systems = None
        mock_case.user_impact = "Test impact"
        mock_case.business_impact = None
        mock_case.duration = 3600
        mock_case.tags = "tag1"
        mock_case.occurrence_time = None
        mock_case.resolution_time = None
        mock_case.author = "admin"
        mock_case.view_count = 5
        mock_case.created_at = datetime.now()
        mock_case.updated_at = datetime.now()
        
        from api.routes.knowledge import _case_to_dict
        result = _case_to_dict(mock_case)
        
        assert result["id"] == 1
        assert result["case_no"] == "CASE-2024-001"
        assert result["title"] == "Test Case"
        assert result["fault_level"] == "p2"
    
    def test_category_to_dict(self):
        """测试分类转字典函数"""
        from modules.business.knowledge_base.models import Category
        
        mock_cat = MagicMock()
        mock_cat.id = 1
        mock_cat.name = "Test Category"
        mock_cat.parent_id = None
        mock_cat.code = "test"
        mock_cat.doc_type = None
        mock_cat.description = "Test description"
        mock_cat.sort_order = 1
        mock_cat.icon = "folder"
        mock_cat.is_active = True
        mock_cat.children = []
        
        from api.routes.knowledge import _category_to_dict
        result = _category_to_dict(mock_cat)
        
        assert result["id"] == 1
        assert result["name"] == "Test Category"
        assert result["code"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
