"""
Pytest配置和共享Fixture

遵循Google测试最佳实践 + ITTrues最佳实践:
- 80% 单元测试, 20% 集成测试
- 测试通过公共API, 不测试内部实现
- Given-When-Then结构
- DAMP (Descriptive And Meaningful Phrases) over DRY
- 测试数据必须来自工厂生成，不允许硬编码
"""

import os
import sys
import random
import string
import hashlib
import uuid
from pathlib import Path
from typing import Generator, Any, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# 测试数据工厂 (Test Data Factory)
# ============================================================================

class DataFactory:
    """
    测试数据工厂 - 生成真实感的测试数据
    
    遵循原则:
    - 不在代码中硬编码测试数据
    - 使用 faker 生成真实感数据
    - 每个工厂方法生成独立数据
    - 支持批量生成
    """

    def __init__(self, seed: int = None):
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
    
    def _uid(self) -> str:
        """生成唯一ID"""
        self._counter += 1
        return f"test_{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def ip_address(self, network: str = "192.168.1") -> str:
        """生成随机IP地址"""
        return f"{network}.{random.randint(1, 254)}"
    
    def hostname(self) -> str:
        """生成随机主机名"""
        prefixes = ["web", "app", "db", "cache", "proxy", "lb", "storage", "node"]
        return f"{random.choice(prefixes)}-{random.choice(['prod', 'dev', 'test'])}-{random.randint(1,99):02d}"
    
    def mac_address(self) -> str:
        """生成随机MAC地址"""
        return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])
    
    def port(self) -> int:
        """生成随机端口号"""
        return random.choice([22, 80, 443, 3306, 5432, 6379, 8080, 8443, 27017, 9200, 8000])

    # ----- 设备相关 -----
    def device(self, **overrides) -> dict:
        """生成设备数据"""
        device_types = ["server", "router", "switch", "firewall", "storage", "load_balancer"]
        categories = ["linux", "windows", "network", "storage"]
        protocols = ["snmp", "ssh", "ipmi", "wmi", "api"]
        locations = ["DataCenter-A", "DataCenter-B", "Edge-01", "Edge-02", "Cloud-01"]
        statuses = ["active", "inactive", "maintenance", "decommissioned"]
        
        data = {
            "name": self.hostname(),
            "ip_address": self.ip_address(),
            "device_type": random.choice(device_types),
            "protocol": random.choice(protocols),
            "community": "public",
            "category": random.choice(categories),
            "location": random.choice(locations),
            "status": random.choice(statuses),
            "tags": random.sample(["关键", "核心", "测试", "开发", "灾备"], k=random.randint(0, 3)),
            "custom_fields": {"rack": f"A-{random.randint(1,20)}", "power": f"{random.randint(1,2)}"},
        }
        data.update(overrides)
        return data

    def device_list(self, count: int = 10) -> list:
        """批量生成设备数据"""
        return [self.device() for _ in range(count)]

    # ----- 告警相关 -----
    def alert(self, device_id: str = None, **overrides) -> dict:
        """生成告警数据"""
        severities = ["critical", "high", "medium", "low", "info"]
        categories = ["cpu", "memory", "disk", "network", "process", "service", "security", "system"]
        data = {
            "name": f"{random.choice(categories).upper()}告警 - {self._uid()}",
            "severity": random.choice(severities),
            "source": device_id or f"device_{self._uid()}",
            "metric": random.choice(categories),
            "threshold": random.choice([70, 80, 85, 90, 95]),
            "current_value": random.randint(85, 99),
            "message": f"检测到{random.choice(categories)}使用率异常",
            "status": random.choice(["active", "acknowledged", "resolved"]),
            "tags": random.sample(["自动发现", "手动创建", "阈值触发", "趋势异常"], k=2),
        }
        data.update(overrides)
        return data

    def alert_list(self, count: int = 20) -> list:
        return [self.alert() for _ in range(count)]

    # ----- 工单相关 -----
    def workorder(self, **overrides) -> dict:
        """生成工单数据"""
        statuses = ["draft", "pending", "assigned", "in_progress", "resolved", "closed", "cancelled"]
        priorities = ["critical", "high", "medium", "low"]
        categories = ["hardware", "software", "network", "security", "access", "other"]
        
        data = {
            "title": f"工单-{self._uid()}",
            "description": f"详细描述 - {uuid.uuid4().hex[:8]}",
            "priority": random.choice(priorities),
            "category": random.choice(categories),
            "status": random.choice(statuses),
            "requester": f"user_{self._uid()}",
            "assignee": f"operator_{self._uid()}" if random.random() > 0.3 else None,
            "due_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
            "tags": random.sample(["紧急", "重要", "例行", "变更"], k=random.randint(0, 2)),
        }
        data.update(overrides)
        return data

    def workorder_list(self, count: int = 15) -> list:
        return [self.workorder() for _ in range(count)]

    def draft(self, **overrides) -> dict:
        """生成工单草稿数据"""
        order_types = ["fault", "change", "inspection", "security", "demand", "question", "other"]
        priorities = ["P1", "P2", "P3", "P4"]
        impacts = ["whole_company", "department", "team", "individual"]

        data = {
            "draft_id": f"draft-{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{self._uid()}",
            "username": f"user_{self._counter}",
            "order_type": random.choice(order_types),
            "title": f"草稿-{self._uid()}",
            "description": f"草稿描述 - {uuid.uuid4().hex[:8]}",
            "priority": random.choice(priorities),
            "device_id": random.randint(1, 1000) if random.random() > 0.3 else None,
            "device_name": self.hostname(),
            "device_ip": self.ip_address(),
            "assignee": f"operator_{self._uid()}" if random.random() > 0.5 else None,
            "expected_end": (datetime.now() + timedelta(days=random.randint(1, 7))).isoformat(),
            "impact": random.choice(impacts),
            "tags": random.sample(["紧急", "重要", "例行", "变更", "巡检"], k=random.randint(0, 3)),
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

    # ----- 用户/认证相关 -----
    def user(self, **overrides) -> dict:
        """生成用户数据"""
        roles = ["admin", "operator", "viewer", "manager"]
        data = {
            "username": f"user_{self._uid()}",
            "password": f"P@ssw0rd_{self._uid()}",
            "email": f"user_{self._uid()}@test.local",
            "full_name": f"测试用户 {self._counter}",
            "role": random.choice(roles),
            "department": random.choice(["IT", "运维", "开发", "安全", "网络"]),
            "phone": f"+86-{random.randint(130,189)}{random.randint(10000000, 99999999)}",
            "status": random.choice(["active", "inactive"]),
        }
        data.update(overrides)
        return data

    def api_key(self, **overrides) -> dict:
        """生成API Key数据"""
        data = {
            "name": f"apikey_{self._uid()}",
            "key_id": f"ak_{uuid.uuid4().hex[:12]}",
            "key_prefix": f"ak_{uuid.uuid4().hex[:8]}",
            "scopes": random.sample(["read", "write", "admin"], k=random.randint(1, 3)),
            "expires_at": (datetime.now() + timedelta(days=random.randint(30, 365))).isoformat(),
            "status": random.choice(["active", "inactive"]),
        }
        data.update(overrides)
        return data

    # ----- 通知相关 -----
    def notification_channel(self, **overrides) -> dict:
        """生成通知渠道数据"""
        types = ["email", "sms", "webhook", "dingtalk", "feishu", "wecom"]
        data = {
            "name": f"渠道_{self._uid()}",
            "type": random.choice(types),
            "config": {
                "webhook_url": f"https://hook.test.com/{uuid.uuid4().hex[:8]}",
                "retry_times": random.randint(1, 5),
                "timeout": random.choice([5, 10, 30]),
            },
            "status": random.choice(["active", "inactive"]),
        }
        data.update(overrides)
        return data

    def notification_target_rule(self, **overrides) -> dict:
        """生成通知目标规则数据"""
        rule_types = ["alert_level", "device", "category", "custom"]
        notify_channels = ["email", "dingtalk", "feishu", "wechat_work", "webhook", "sms", "phone"]
        data = {
            "name": f"规则_{self._uid()}",
            "description": f"通知目标规则描述 - {uuid.uuid4().hex[:8]}",
            "rule_type": random.choice(rule_types),
            "match_conditions": {
                "levels": random.sample(["critical", "high", "medium", "low", "info"], k=random.randint(1, 3))
            },
            "notify_channels": random.sample(notify_channels, k=random.randint(1, 3)),
            "notify_receivers": [f"user_{self._uid()}@test.local" for _ in range(random.randint(1, 2))],
            "notify_interval": random.choice([0, 60, 300, 600, 1800]),
            "max_notify_count": random.randint(1, 5),
            "priority": random.randint(1, 200),
            "enabled": random.choice([True, False]),
        }
        data.update(overrides)
        return data

    def notification_template(self, **overrides) -> dict:
        """生成通知模板数据"""
        data = {
            "name": f"模板_{self._uid()}",
            "channel_type": random.choice(["email", "sms", "webhook"]),
            "subject": f"告警通知 - {self._uid()}",
            "content": f"告警内容: {{alert_message}}\\n级别: {{severity}}\\n时间: {{timestamp}}",
            "vars": ["alert_message", "severity", "timestamp"],
        }
        data.update(overrides)
        return data

    # ----- 知识库相关 -----
    def document(self, **overrides) -> dict:
        """生成知识库文档数据"""
        data = {
            "title": f"文档-{self._uid()}",
            "content": f"这是文档内容 - {uuid.uuid4().hex[:8]}",
            "category": random.choice(["操作手册", "故障排查", "配置指南", "最佳实践"]),
            "tags": random.sample(["Linux", "网络", "安全", "数据库", "云原生"], k=2),
            "status": random.choice(["draft", "published", "archived"]),
            "author": f"user_{self._uid()}",
            "review_status": random.choice(["pending", "approved", "rejected"]),
        }
        data.update(overrides)
        return data

    # ----- 采集任务相关 -----
    def collection_task(self, device_id: str = None, **overrides) -> dict:
        """生成采集任务数据"""
        data = {
            "name": f"采集任务_{self._uid()}",
            "device_id": device_id or f"device_{self._uid()}",
            "metric_type": random.choice(["cpu", "memory", "disk", "network"]),
            "interval": random.choice([30, 60, 300, 600]),
            "status": random.choice(["active", "paused", "stopped"]),
            "config": {"timeout": 30, "retries": 3},
        }
        data.update(overrides)
        return data

    # ----- 自动化相关 -----
    def automation_script(self, **overrides) -> dict:
        """生成自动化脚本数据"""
        languages = ["bash", "python", "powershell"]
        data = {
            "name": f"脚本_{self._uid()}",
            "description": f"自动化脚本 - {uuid.uuid4().hex[:8]}",
            "language": random.choice(languages),
            "content": f"#!/bin/bash\necho 'Hello from test script {self._uid()}'",
            "timeout": random.choice([30, 60, 300, 600]),
            "tags": random.sample(["自动化", "批量", "巡检", "告警"], k=2),
        }
        data.update(overrides)
        return data

    def trigger_rule(self, **overrides) -> dict:
        """生成触发规则数据"""
        data = {
            "name": f"规则_{self._uid()}",
            "condition": '{"severity": "critical"}',
            "action": "execute_script",
            "target_id": f"script_{self._uid()}",
            "enabled": random.choice([True, False]),
            "cooldown": random.randint(60, 3600),
        }
        data.update(overrides)
        return data

    # ----- 备份相关 -----
    def backup_record(self, **overrides) -> dict:
        """生成备份记录数据"""
        backup_types = ["full", "incremental", "config"]
        statuses = ["success", "failed", "in_progress"]
        data = {
            "name": f"备份_{self._uid()}",
            "backup_type": random.choice(backup_types),
            "size_mb": random.randint(10, 5000),
            "status": random.choice(statuses),
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=random.randint(7, 90))).isoformat(),
        }
        data.update(overrides)
        return data


# ============================================================================
# 全局工厂实例
# ============================================================================

@pytest.fixture(scope="session")
def factory() -> DataFactory:
    """会话级工厂实例（所有测试共享相同种子，便于复现）"""
    return DataFactory(seed=42)


@pytest.fixture
def f() -> DataFactory:
    """函数级工厂实例（每个测试独立，便于生成不同数据）"""
    return DataFactory()


# ============================================================================
# 数据库Fixture（内存SQLite，隔离测试）
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """创建测试数据库引擎（function级，每个测试独立）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    # 启用外键约束
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    # 导入所有模型以确保 Base.metadata 包含所有表
    from modules.foundation.db_models.base import Base
    # 导入 foundation 层模型
    from modules.foundation.db_models.device import Device, DeviceType, DeviceStatus
    from modules.foundation.db_models.alert import Alert, AlertLevel, AlertStatus, AlertCategory, AlertRule
    from modules.foundation.db_models.monitoring import PerformanceMetric
    from modules.foundation.db_models.system import OperationLog, BackupRecord
    from modules.foundation.db_models.workorder import WorkOrder, WorkOrderType, WorkOrderStatus
    from modules.foundation.db_models.report_template import ReportTemplate, ReportTemplateType, ReportFormat, Report, ReportSchedule
    # 导入 AI 模型
    from modules.foundation.db_models.ai import AIConversation
    # 导入通知模型
    from modules.foundation.db_models.notification.notification_model import (
        NotificationChannelModel, NotificationLog, NotificationTargetRule
    )
    # 导入知识库模型
    from modules.business.knowledge_base.models import (
        SOPDocument, SOPVersion, SOPReview, FaultCase,
        Category, Tag, Document, DocumentChunk,
        SearchHistory, SearchBookmark
    )
    
    # 创建所有表
    Base.metadata.create_all(db_engine)
    
    Session = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()


# ============================================================================
# 应用级别Fixture
# ============================================================================

@pytest.fixture(scope="session")
def app():
    """创建FastAPI应用实例 (session级，所有测试共享)"""
    with patch("modules.foundation.db.client.DatabaseManager._ensure_connected"):
        with patch("modules.foundation.db.client.redis_client") as mock_redis:
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            mock_redis.exists.return_value = 0
            mock_redis.delete.return_value = 1
            mock_redis.hset.return_value = 1
            mock_redis.hgetall.return_value = {}
            mock_redis.keys.return_value = []
            mock_redis.scan_iter.return_value = iter([])
            
            from api.main import app as fastapi_app
            yield fastapi_app


@pytest.fixture(scope="function")
def client(app) -> Generator:
    """创建TestClient实例 (function级，每个测试独立)"""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


# ============================================================================
# 认证Fixture
# ============================================================================

@pytest.fixture
def admin_headers(client) -> dict:
    """获取管理员认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "***"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
    # 回退：返回模拟头
    return {"Authorization": "Bearer test_admin_token"}


@pytest.fixture
def operator_headers(client) -> dict:
    """获取运维人员认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "***"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
    return {"Authorization": "Bearer test_operator_token"}


@pytest.fixture
def viewer_headers(client) -> dict:
    """获取访客认证头"""
    return {"Authorization": "Bearer test_viewer_token"}


# ============================================================================
# Mock Fixture
# ============================================================================

@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.all.return_value = []
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    return session


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = 0
    redis_mock.hset.return_value = 1
    redis_mock.hgetall.return_value = {}
    redis_mock.keys.return_value = []
    redis_mock.scan_iter.return_value = iter([])
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    return redis_mock


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    client = MagicMock()
    client.chat.return_value = "这是一个模拟的AI响应"
    client.analyze.return_value = {"root_cause": "测试原因", "confidence": 0.95}
    return client


# ============================================================================
# 上下文管理器Fixture
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """创建临时目录"""
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    """设置测试环境变量"""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DB_ECHO", "false")
    return monkeypatch


# ============================================================================
# 响应断言辅助
# ============================================================================

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


def get_field_errors(response) -> dict:
    """从响应中提取字段级错误"""
    if response.status_code == 422:
        return {err["loc"][-1]: err["msg"] for err in response.json().get("detail", [])}
    return {}


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "unit: Unit tests (isolated, fast)")
    config.addinivalue_line("markers", "integration: Integration tests (require app context)")
    config.addinivalue_line("markers", "e2e: End-to-end business flow tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "api: API-level tests")
    config.addinivalue_line("markers", "db: Tests that need database")


def pytest_collection_modifyitems(items):
    """自动为测试添加标记"""
    for item in items:
        path = str(item.fspath)
        name = item.name
        
        # 根据路径自动添加标记
        if "unit" in path:
            item.add_marker(pytest.mark.unit)
        elif "integration" in path:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in path or "flow" in path:
            item.add_marker(pytest.mark.e2e)
        
        # 根据名称添加标记
        if "slow" in name or "stress" in name or "benchmark" in name:
            item.add_marker(pytest.mark.slow)
        if "api" in name or "_api_" in path:
            item.add_marker(pytest.mark.api)
        if "db_session" in item.fixturenames or "db_engine" in item.fixturenames:
            item.add_marker(pytest.mark.db)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """测试结束后输出摘要"""
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    skipped = len(terminalreporter.stats.get("skipped", []))
    total = passed + failed + skipped
    
    terminalreporter.write_sep("=", "ITOps Platform 测试摘要")
    terminalreporter.write_line(f"总计: {total} | 通过: {passed} | 失败: {failed} | 跳过: {skipped}")
    
    if total > 0:
        rate = passed / total * 100
        terminalreporter.write_line(f"通过率: {rate:.1f}%")
        
        if rate >= 90:
            terminalreporter.write_line("✅ 优秀 (≥90%)", green=True)
        elif rate >= 70:
            terminalreporter.write_line("⚠️ 良好 (≥70%)", yellow=True)
        else:
            terminalreporter.write_line("❌ 需改进 (<70%)", red=True)
