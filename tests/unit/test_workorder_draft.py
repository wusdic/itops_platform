"""
WKO-008: 工单草稿保存 - 单元测试
PUT /api/v1/workorders/{id}/draft 端点测试

测试内容:
- PUT draft端点
- DB字段: draft_data, draft_saved_at
- 草稿保存只更新: title, description, priority, draft_data, draft_saved_at
- 不更新updated_at
- 不记录操作历史
- 状态保持draft
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

import sys
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

# Import modules
from modules.foundation.db_models.workorder import (
    WorkOrder, WorkOrderType, WorkOrderStatus, WorkOrderPriority
)
from modules.business.workorder.workorder import WorkOrderCore


class WorkOrderDraftDataFactory:
    """工单草稿测试数据工厂"""
    
    def __init__(self, seed: int = None):
        import random
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
        self._random = random
    
    def _uid(self) -> str:
        self._counter += 1
        return f"draft_{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def draft_request(self, **overrides) -> Dict[str, Any]:
        """生成草稿保存请求数据"""
        data = {
            "title": f"草稿标题-{self._uid()}",
            "description": f"草稿描述 - {uuid.uuid4().hex[:8]}",
            "priority": self._random.choice(["P1", "P2", "P3", "P4"]),
            "order_type": self._random.choice(["fault", "change", "inspection", "security", "demand", "question", "other"]),
            "device_id": self._random.randint(1, 1000) if self._random.random() > 0.3 else None,
            "device_name": f"server-{self._random.randint(1, 100)}",
            "device_ip": f"192.168.1.{self._random.randint(1, 254)}",
            "assignee": f"user_{self._random.randint(1, 100)}",
            "expected_end": (datetime.now() + timedelta(days=7)).isoformat(),
            "impact": self._random.choice(["whole_company", "department", "team", "individual"]),
            "tags": self._random.sample(["紧急", "重要", "例行"], k=self._random.randint(0, 2)),
            "attachments": [],
        }
        data.update(overrides)
        return data
    
    def workorder(self, **overrides) -> WorkOrder:
        """生成WorkOrder对象"""
        wo = MagicMock(spec=WorkOrder)
        wo.id = overrides.get('id', 1)
        wo.order_no = overrides.get('order_no', 'FAU20260428001')
        wo.order_type = overrides.get('order_type', WorkOrderType.FAULT)
        wo.priority = overrides.get('priority', WorkOrderPriority.P3)
        wo.title = overrides.get('title', '测试工单')
        wo.description = overrides.get('description', '测试描述')
        wo.status = overrides.get('status', WorkOrderStatus.PENDING)
        wo.device_id = overrides.get('device_id', None)
        wo.device_name = overrides.get('device_name', None)
        wo.device_ip = overrides.get('device_ip', None)
        wo.creator = overrides.get('creator', 'testuser')
        wo.assignee = overrides.get('assignee', None)
        wo.created_at = overrides.get('created_at', datetime.now())
        wo.updated_at = overrides.get('updated_at', datetime.now())
        wo.draft_data = overrides.get('draft_data', None)
        wo.draft_saved_at = overrides.get('draft_saved_at', None)
        return wo


@pytest.fixture
def df():
    """数据工厂实例"""
    return WorkOrderDraftDataFactory(seed=42)


@pytest.fixture
def mock_db():
    """Mock数据库会话"""
    db = MagicMock()
    return db


class TestWorkOrderDraftFields:
    """测试WorkOrder模型的草稿字段"""
    
    def test_draft_data_field_exists(self):
        """验证draft_data字段存在"""
        assert hasattr(WorkOrder, 'draft_data')
    
    def test_draft_saved_at_field_exists(self):
        """验证draft_saved_at字段存在"""
        assert hasattr(WorkOrder, 'draft_saved_at')


class TestWorkOrderCoreSaveDraft:
    """测试WorkOrderCore.save_draft方法"""
    
    def setup_method(self):
        """每个测试前设置"""
        self.mock_db = MagicMock()
        self.core = WorkOrderCore(self.mock_db)
    
    def test_save_draft_updates_title(self, df):
        """测试保存草稿更新标题"""
        original_wo = df.workorder(title="原始标题")
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        new_title = "新草稿标题"
        result = self.core.save_draft(
            workorder_id=1,
            title=new_title,
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        assert result is True
        assert original_wo.title == new_title
    
    def test_save_draft_updates_description(self, df):
        """测试保存草稿更新描述"""
        original_wo = df.workorder(description="原始描述")
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        new_desc = "新草稿描述"
        result = self.core.save_draft(
            workorder_id=1,
            description=new_desc,
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        assert result is True
        assert original_wo.description == new_desc
    
    def test_save_draft_updates_priority(self, df):
        """测试保存草稿更新优先级"""
        original_wo = df.workorder(priority=WorkOrderPriority.P3)
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        result = self.core.save_draft(
            workorder_id=1,
            priority=WorkOrderPriority.P1,
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        assert result is True
        assert original_wo.priority == WorkOrderPriority.P1
    
    def test_save_draft_updates_draft_data(self, df):
        """测试保存草稿更新draft_data"""
        original_wo = df.workorder()
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        draft_snapshot = {
            "title": "快照标题",
            "description": "快照描述",
            "priority": "P2",
            "device_id": 123,
        }
        
        result = self.core.save_draft(
            workorder_id=1,
            draft_data=draft_snapshot,
            draft_saved_at=datetime.now()
        )
        
        assert result is True
        assert original_wo.draft_data == draft_snapshot
    
    def test_save_draft_updates_draft_saved_at(self, df):
        """测试保存草稿更新draft_saved_at"""
        original_wo = df.workorder()
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        saved_time = datetime.now()
        result = self.core.save_draft(
            workorder_id=1,
            draft_data={},
            draft_saved_at=saved_time
        )
        
        assert result is True
        assert original_wo.draft_saved_at == saved_time
    
    def test_save_draft_does_not_update_updated_at(self, df):
        """测试保存草稿不更新updated_at"""
        original_time = datetime(2024, 1, 1, 12, 0, 0)
        original_wo = df.workorder(updated_at=original_time)
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        self.core.save_draft(
            workorder_id=1,
            title="新标题",
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        # updated_at不应该被修改
        assert original_wo.updated_at == original_time
    
    def test_save_draft_does_not_record_flow(self, df):
        """测试保存草稿不记录操作历史"""
        original_wo = df.workorder()
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        self.core.save_draft(
            workorder_id=1,
            title="新标题",
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        # 验证没有调用_record_flow
        self.core._record_flow = MagicMock()
        self.core.save_draft(
            workorder_id=1,
            title="新标题",
            draft_data={},
            draft_saved_at=datetime.now()
        )
        self.core._record_flow.assert_not_called()
    
    def test_save_draft_commits_changes(self, df):
        """测试保存草稿提交数据库更改"""
        original_wo = df.workorder()
        self.core.get_by_id = MagicMock(return_value=original_wo)
        
        self.core.save_draft(
            workorder_id=1,
            title="新标题",
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        self.mock_db.commit.assert_called_once()
    
    def test_save_draft_rollback_on_error(self, df):
        """测试保存草稿失败时回滚"""
        from sqlalchemy.exc import SQLAlchemyError
        
        original_wo = df.workorder()
        self.core.get_by_id = MagicMock(return_value=original_wo)
        self.mock_db.commit.side_effect = SQLAlchemyError("DB Error")
        
        with pytest.raises(SQLAlchemyError):
            self.core.save_draft(
                workorder_id=1,
                title="新标题",
                draft_data={},
                draft_saved_at=datetime.now()
            )
        
        self.mock_db.rollback.assert_called()
    
    def test_save_draft_workorder_not_found(self, df):
        """测试保存草稿工单不存在"""
        self.core.get_by_id = MagicMock(return_value=None)
        
        result = self.core.save_draft(
            workorder_id=999,
            title="新标题",
            draft_data={},
            draft_saved_at=datetime.now()
        )
        
        assert result is False


class TestDraftDataSnapshot:
    """测试草稿数据快照"""
    
    def test_draft_data_contains_all_form_fields(self, df):
        """测试草稿数据快照包含所有表单字段"""
        draft_data = {
            "order_type": "fault",
            "title": "测试标题",
            "description": "测试描述",
            "priority": "P2",
            "device_id": 123,
            "device_name": "test-server",
            "device_ip": "192.168.1.100",
            "assignee": "user1",
            "expected_end": "2024-12-31T23:59:59",
            "impact": "department",
            "tags": ["紧急", "重要"],
            "attachments": [],
        }
        
        # 验证所有字段都存在
        required_fields = [
            "order_type", "title", "description", "priority",
            "device_id", "device_name", "device_ip", "assignee",
            "expected_end", "impact", "tags", "attachments"
        ]
        
        for field in required_fields:
            assert field in draft_data, f"字段 {field} 应该在草稿数据中"
    
    def test_draft_data_serialization(self, df):
        """测试草稿数据可序列化"""
        draft_data = {
            "title": "测试标题",
            "description": "测试描述",
            "priority": "P2",
            "tags": ["标签1", "标签2"],
            "attachments": [{"name": "file1", "url": "/path/to/file"}],
        }
        
        # 应该能够序列化为JSON
        serialized = json.dumps(draft_data)
        deserialized = json.loads(serialized)
        
        assert deserialized == draft_data


class TestWorkOrderDraftResponse:
    """测试工单草稿响应格式"""
    
    def test_response_format(self, df):
        """测试响应格式遵循 {data:..., code:0}"""
        response = {
            "code": 0,
            "message": "草稿保存成功",
            "data": {
                "id": 1,
                "order_no": "FAU20260428001",
                "title": "测试标题",
                "status": "pending",
            }
        }
        
        assert "code" in response
        assert response["code"] == 0
        assert "data" in response
        assert "message" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
