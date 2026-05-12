"""
WKO-008: Work Order Draft Save - TDD Tests
工单草稿保存功能测试
使用 DataFactory 生成测试数据
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any

import sys
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

# Import modules directly to avoid full app init
import importlib.util

def load_module_directly(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

workorder_draft_module = load_module_directly(
    "workorder_draft",
    "/home/zcxx/.hermes/projects/itops_platform/modules/business/workorder/workorder_draft.py"
)

WorkOrderDraftManager = workorder_draft_module.WorkOrderDraftManager
WorkOrderDraft = workorder_draft_module.WorkOrderDraft
DraftStatus = workorder_draft_module.DraftStatus
SLATracker = workorder_draft_module.SLATracker


# ============== DataFactory for Work Order Draft Tests ==============

class WorkOrderDraftDataFactory:
    """
    工单草稿测试数据工厂
    遵循 DataFactory 原则生成真实感数据
    """

    def __init__(self, seed: int = None):
        import random
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
        self._random = random

    def _uid(self) -> str:
        """生成唯一ID"""
        self._counter += 1
        return f"draft_{self._counter}_{uuid.uuid4().hex[:8]}"

    def ip_address(self, network: str = "192.168.1") -> str:
        """生成随机IP地址"""
        return f"{network}.{self._random.randint(1, 254)}"

    def hostname(self) -> str:
        """生成随机主机名"""
        prefixes = ["web", "app", "db", "cache", "proxy", "lb", "storage", "node"]
        return f"{self._random.choice(prefixes)}-{self._random.choice(['prod', 'dev', 'test'])}-{self._random.randint(1,99):02d}"

    def draft(self, **overrides) -> dict:
        """生成工单草稿数据"""
        order_types = ["fault", "change", "inspection", "security", "demand", "question", "other"]
        priorities = ["P1", "P2", "P3", "P4"]
        impacts = ["whole_company", "department", "team", "individual"]

        data = {
            "draft_id": f"draft-{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{self._uid()}",
            "username": f"user_{self._counter}",
            "order_type": self._random.choice(order_types),
            "title": f"草稿-{self._uid()}",
            "description": f"草稿描述 - {uuid.uuid4().hex[:8]}",
            "priority": self._random.choice(priorities),
            "device_id": self._random.randint(1, 1000) if self._random.random() > 0.3 else None,
            "device_name": self.hostname(),
            "device_ip": self.ip_address(),
            "assignee": f"operator_{self._uid()}" if self._random.random() > 0.5 else None,
            "expected_end": (datetime.now() + timedelta(days=self._random.randint(1, 7))).isoformat(),
            "impact": self._random.choice(impacts),
            "tags": self._random.sample(["紧急", "重要", "例行", "变更", "巡检"], k=self._random.randint(0, 3)),
            "attachments": [],
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_auto_save": False,
            "last_auto_save": None,
        }
        data.update(overrides)
        return data

    def draft_list(self, count: int = 5) -> list:
        """批量生成工单草稿数据"""
        return [self.draft() for _ in range(count)]


@pytest.fixture
def draft_factory() -> WorkOrderDraftDataFactory:
    """草稿数据工厂实例"""
    return WorkOrderDraftDataFactory(seed=42)


@pytest.fixture
def df() -> WorkOrderDraftDataFactory:
    """简短版本的工厂实例"""
    return WorkOrderDraftDataFactory()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = MagicMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = 1
    redis.keys.return_value = []
    return redis


class TestWorkOrderDraftDataFactory:
    """WorkOrderDraftDataFactory 测试"""

    def test_draft_generation(self, draft_factory):
        """测试草稿数据生成"""
        draft = draft_factory.draft()

        assert draft is not None
        assert 'draft_id' in draft
        assert 'user_id' in draft
        assert 'username' in draft
        assert 'title' in draft
        assert 'priority' in draft
        assert 'order_type' in draft

    def test_draft_priority_values(self, df):
        """测试优先级值"""
        for _ in range(10):
            draft = df.draft()
            assert draft['priority'] in ['P1', 'P2', 'P3', 'P4']

    def test_draft_order_type_values(self, df):
        """测试工单类型值"""
        for _ in range(10):
            draft = df.draft()
            assert draft['order_type'] in ['fault', 'change', 'inspection', 'security', 'demand', 'question', 'other']

    def test_draft_list_generation(self, draft_factory):
        """测试批量草稿生成"""
        drafts = draft_factory.draft_list(count=5)

        assert len(drafts) == 5
        assert all('draft_id' in d for d in drafts)

    def test_draft_override(self, df):
        """测试数据覆盖"""
        draft = df.draft(title="自定义标题", priority="P1")

        assert draft['title'] == "自定义标题"
        assert draft['priority'] == "P1"


class TestWorkOrderDraft:
    """WorkOrderDraft 模型测试"""

    def test_draft_creation_with_minimal_data(self, df):
        """测试最小数据创建草稿"""
        draft = WorkOrderDraft(
            draft_id=df._uid(),
            user_id="user123",
            username="testuser"
        )

        assert draft.draft_id is not None
        assert draft.user_id == "user123"
        assert draft.username == "testuser"
        assert draft.priority == "P3"  # default
        assert draft.status == DraftStatus.ACTIVE

    def test_draft_to_dict(self, df):
        """测试草稿转字典"""
        draft = WorkOrderDraft(
            draft_id="test-draft-001",
            user_id="user123",
            username="testuser",
            title="测试标题",
            description="测试描述",
            priority="P2",
            order_type="fault"
        )

        d = draft.to_dict()

        assert d['draft_id'] == "test-draft-001"
        assert d['title'] == "测试标题"
        assert d['priority'] == "P2"
        assert d['order_type'] == "fault"
        assert d['status'] == 'active'

    def test_draft_status_enum(self, df):
        """测试草稿状态枚举"""
        assert DraftStatus.ACTIVE.value == "active"
        assert DraftStatus.SUBMITTED.value == "submitted"
        assert DraftStatus.EXPIRED.value == "expired"


class TestWorkOrderDraftManager:
    """WorkOrderDraftManager 测试 - TDD风格"""

    def setup_method(self):
        """每个测试前设置"""
        self.mock_redis = MagicMock()
        self.draft_manager = WorkOrderDraftManager(redis_client=self.mock_redis)

    def test_save_draft_new(self, df):
        """测试保存新草稿"""
        draft_data = df.draft()

        draft_id, saved_draft = self.draft_manager.save_draft(
            user_id=draft_data['user_id'],
            username=draft_data['username'],
            draft_data=draft_data
        )

        assert draft_id is not None
        assert saved_draft is not None
        assert saved_draft.user_id == draft_data['user_id']
        assert saved_draft.username == draft_data['username']
        assert saved_draft.title == draft_data['title']
        assert saved_draft.status == DraftStatus.ACTIVE

    def test_save_draft_with_auto_save(self, df):
        """测试自动保存草稿"""
        draft_data = df.draft()

        draft_id, saved_draft = self.draft_manager.save_draft(
            user_id=draft_data['user_id'],
            username=draft_data['username'],
            draft_data=draft_data,
            is_auto_save=True
        )

        assert saved_draft.is_auto_save is True
        assert saved_draft.last_auto_save is not None

    def test_save_draft_update_existing(self, df):
        """测试更新已存在草稿"""
        original_data = df.draft(title="原始标题")

        # 第一次保存
        draft_id, _ = self.draft_manager.save_draft(
            user_id=original_data['user_id'],
            username=original_data['username'],
            draft_data=original_data
        )

        # 更新数据
        updated_data = original_data.copy()
        updated_data['title'] = "更新后的标题"

        # 第二次保存（更新）
        _, updated_draft = self.draft_manager.save_draft(
            user_id=original_data['user_id'],
            username=original_data['username'],
            draft_id=draft_id,
            draft_data=updated_data
        )

        assert updated_draft.draft_id == draft_id
        assert updated_draft.title == "更新后的标题"

    def test_save_draft_redis_key_format(self, df):
        """测试Redis键格式"""
        draft_data = df.draft()

        draft_id, _ = self.draft_manager.save_draft(
            user_id="user123",
            username="testuser",
            draft_data=draft_data
        )

        # 验证Redis.set被调用
        self.mock_redis.set.assert_called()
        call_args = self.mock_redis.set.call_args
        key = call_args[0][0]

        assert "workorder:draft:" in key
        assert "user123" in key
        assert draft_id in key

    def test_save_draft_redis_expiration(self, df):
        """测试Redis过期时间设置"""
        draft_data = df.draft()

        self.draft_manager.save_draft(
            user_id="user123",
            username="testuser",
            draft_data=draft_data
        )

        # 验证Redis.set被调用
        self.mock_redis.set.assert_called_once()
        call_args = self.mock_redis.set.call_args

        # Redis set调用格式: set(key, value, ex=seconds)
        # 从kwargs获取ex参数
        ex_value = call_args[1].get('ex') if len(call_args) > 1 else None

        # 验证过期时间（7天 = 7 * 24 * 60 * 60 = 604800）
        assert ex_value == 60*60*24*7

    def test_get_draft(self, df):
        """测试获取草稿"""
        draft_data = df.draft()
        draft_id = "test-draft-123"

        # 设置 mock Redis 返回值
        self.mock_redis.get.return_value = json.dumps({
            'draft_id': draft_id,
            'user_id': 'user123',
            'username': 'testuser',
            'title': draft_data['title'],
            'description': draft_data['description'],
            'priority': 'P3',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        })

        draft = self.draft_manager.get_draft('user123', draft_id)

        assert draft is not None
        assert draft.draft_id == draft_id

    def test_get_draft_not_found(self):
        """测试获取不存在的草稿"""
        self.mock_redis.get.return_value = None

        draft = self.draft_manager.get_draft('user123', 'nonexistent')

        assert draft is None

    def test_list_drafts(self, df):
        """测试列出草稿"""
        self.mock_redis.keys.return_value = [
            'workorder:draft:user123:draft1',
            'workorder:draft:user123:draft2'
        ]

        self.mock_redis.get.side_effect = [
            json.dumps({
                'draft_id': 'draft1',
                'user_id': 'user123',
                'username': 'testuser',
                'title': '草稿1',
                'priority': 'P3',
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }),
            json.dumps({
                'draft_id': 'draft2',
                'user_id': 'user123',
                'username': 'testuser',
                'title': '草稿2',
                'priority': 'P2',
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            })
        ]

        drafts = self.draft_manager.list_drafts('user123')

        assert len(drafts) == 2

    def test_delete_draft(self, df):
        """测试删除草稿"""
        draft_data = df.draft()

        # 保存草稿
        draft_id, _ = self.draft_manager.save_draft(
            user_id="user123",
            username="testuser",
            draft_data=draft_data
        )

        # 删除草稿
        result = self.draft_manager.delete_draft("user123", draft_id)

        assert result is True
        self.mock_redis.delete.assert_called_once()

    def test_delete_draft_not_found(self):
        """测试删除不存在的草稿"""
        self.mock_redis.delete.return_value = 0

        result = self.draft_manager.delete_draft('user123', 'nonexistent')

        assert result is True  # Redis delete返回0但方法仍返回True

    def test_cleanup_expired_drafts(self):
        """测试清理过期草稿"""
        # Redis TTL自动处理过期，所以返回0
        result = self.draft_manager.cleanup_expired_drafts()

        assert result == 0


class TestWorkOrderDraftManagerIntegration:
    """WorkOrderDraftManager 集成测试（使用真实数据结构）"""

    def setup_method(self):
        """每个测试前设置"""
        self.mock_redis = MagicMock()
        self.draft_manager = WorkOrderDraftManager(redis_client=self.mock_redis)

    def test_full_draft_lifecycle(self, df):
        """测试完整草稿生命周期"""
        user_id = "user123"
        username = "testuser"

        # 1. 创建新草稿
        draft_data = df.draft(title="新工单草稿", priority="P2")
        draft_id, draft = self.draft_manager.save_draft(
            user_id=user_id,
            username=username,
            draft_data=draft_data
        )

        assert draft_id is not None
        assert draft.title == "新工单草稿"

        # 2. 模拟Redis存储并检索
        stored_data = draft.to_dict()
        self.mock_redis.get.return_value = json.dumps(stored_data)

        retrieved = self.draft_manager.get_draft(user_id, draft_id)
        assert retrieved is not None
        assert retrieved.title == "新工单草稿"

        # 3. 更新草稿
        updated_data = draft_data.copy()
        updated_data['title'] = "更新后的标题"
        _, updated = self.draft_manager.save_draft(
            user_id=user_id,
            username=username,
            draft_id=draft_id,
            draft_data=updated_data
        )

        assert updated.title == "更新后的标题"

        # 4. 删除草稿
        result = self.draft_manager.delete_draft(user_id, draft_id)
        assert result is True

    def test_multiple_drafts_per_user(self, df):
        """测试单个用户多个草稿"""
        user_id = "user123"
        username = "testuser"

        # 创建3个草稿
        draft_ids = []
        for i in range(3):
            draft_data = df.draft(title=f"草稿{i+1}")
            draft_id, _ = self.draft_manager.save_draft(
                user_id=user_id,
                username=username,
                draft_data=draft_data
            )
            draft_ids.append(draft_id)

        # 验证Redis存储了3个草稿
        assert self.mock_redis.set.call_count == 3

        # 列出草稿
        self.mock_redis.keys.return_value = [
            f"workorder:draft:{user_id}:{did}" for did in draft_ids
        ]

        draft_dicts = []
        for did in draft_ids:
            draft = df.draft()
            draft['draft_id'] = did
            draft_dicts.append(draft)

        self.mock_redis.get.side_effect = [json.dumps(d) for d in draft_dicts]

        drafts = self.draft_manager.list_drafts(user_id)
        assert len(drafts) == 3

    def test_draft_expiration_handling(self, df):
        """测试草稿过期处理"""
        draft_data = df.draft()

        # 保存草稿
        self.draft_manager.save_draft(
            user_id="user123",
            username="testuser",
            draft_data=draft_data
        )

        # 验证过期时间被设置
        call_args = self.mock_redis.set.call_args
        ex_value = call_args[1].get('ex') if 'ex' in call_args[1] else None

        # 7天过期
        assert ex_value == 7 * 24 * 60 * 60


# ============== API Request/Response Models Tests ==============

class TestDraftAPIIntegration:
    """工单草稿API集成测试"""

    def test_draft_save_request_model(self, df):
        """测试草稿保存请求模型序列化"""
        from api.routes.workorder import WorkOrderDraftSave

        draft_save = WorkOrderDraftSave(
            order_type="fault",
            title="测试工单",
            description="测试描述",
            priority="P2",
            device_id=123,
            device_name="test-server",
            device_ip="192.168.1.100",
            is_auto_save=False
        )

        data = draft_save.dict(exclude_none=True)

        assert data['order_type'] == "fault"
        assert data['title'] == "测试工单"
        assert data['priority'] == "P2"
        assert data['device_id'] == 123
        assert 'is_auto_save' in data

    def test_draft_response_model(self, df):
        """测试草稿响应模型"""
        from api.routes.workorder import WorkOrderDraftResponse

        now = datetime.now().isoformat()
        response = WorkOrderDraftResponse(
            draft_id="test-draft-001",
            user_id="user123",
            username="testuser",
            priority="P3",
            status="active",
            created_at=now,
            updated_at=now
        )

        data = response.dict()

        assert data['draft_id'] == "test-draft-001"
        assert data['status'] == "active"
