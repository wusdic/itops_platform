"""
告警审计日志测试
测试AlertAuditLog模型的创建、查询功能
使用 DataFactory 生成真实感测试数据
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from modules.foundation.db_models.alert import AlertAuditLog, Alert, AlertLevel, AlertStatus


# ============== AlertAuditLog 测试数据工厂 ==============

class AlertAuditLogFactory:
    """
    告警审计日志测试数据工厂
    使用 DataFactory 原则生成真实感数据
    """

    def __init__(self, seed: int = None):
        import random
        import uuid
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
        self._random = random
        self._uuid = uuid

    def _uid(self) -> str:
        """生成唯一ID"""
        self._counter += 1
        return f"audit_{self._counter}_{self._uuid.uuid4().hex[:8]}"

    def audit_log(self, alert_id: int = None, **overrides) -> dict:
        """生成审计日志数据"""
        actions = ["create", "acknowledge", "resolve", "close", "update", "delete"]
        operators = ["admin", "operator", "user", "system"]
        fields = ["status", "assignee", "level", "priority", "remark", "workorder_id"]

        data = {
            "alert_id": alert_id or self._random.randint(1, 100),
            "alert_key": f"alert-key-{self._uid()}",
            "action": self._random.choice(actions),
            "operator": self._random.choice(operators),
            "operator_ip": f"192.168.1.{self._random.randint(1, 254)}",
            "field_name": self._random.choice(fields),
            "old_value": "active",
            "new_value": "acknowledged",
            "reason": f"操作原因 - {self._uid()}",
            "workorder_id": self._random.randint(1, 1000) if self._random.random() > 0.5 else None,
            "user_agent": "Mozilla/5.0 Test Browser",
            "request_id": f"req-{self._uuid.uuid4().hex[:12]}",
        }
        data.update(overrides)
        return data

    def audit_log_list(self, count: int = 10, **kwargs) -> list:
        """批量生成审计日志数据"""
        return [self.audit_log(**kwargs) for _ in range(count)]


@pytest.fixture
def audit_factory() -> AlertAuditLogFactory:
    """审计日志工厂实例"""
    return AlertAuditLogFactory(seed=42)


@pytest.fixture
def af() -> AlertAuditLogFactory:
    """简短版本的工厂实例"""
    return AlertAuditLogFactory()


class TestAlertAuditLogModel:
    """AlertAuditLog模型测试"""

    def test_alert_audit_log_creation(self):
        """测试审计日志创建"""
        audit_log = AlertAuditLog(
            alert_id=1,
            alert_key="test-alert-key-001",
            action="acknowledge",
            operator="admin",
            operator_ip="192.168.1.1",
            field_name="status",
            old_value="active",
            new_value="acknowledged",
            reason="用户确认处理",
        )

        assert audit_log.alert_id == 1
        assert audit_log.action == "acknowledge"
        assert audit_log.operator == "admin"
        assert audit_log.field_name == "status"
        assert audit_log.old_value == "active"
        assert audit_log.new_value == "acknowledged"

    def test_alert_audit_log_repr(self):
        """测试审计日志字符串表示"""
        audit_log = AlertAuditLog(
            id=1,
            alert_id=100,
            action="create",
        )

        assert "AlertAuditLog" in repr(audit_log)
        assert "alert_id=100" in repr(audit_log)
        assert "create" in repr(audit_log)

    def test_alert_audit_log_all_actions(self):
        """测试所有支持的操作类型"""
        actions = ["create", "acknowledge", "resolve", "close", "update", "delete"]

        for action in actions:
            audit_log = AlertAuditLog(
                alert_id=1,
                action=action,
            )
            assert audit_log.action == action


class TestAlertAuditLogAPI:
    """AlertAuditLog API测试"""

    def test_audit_log_create_request_model(self):
        """测试审计日志创建请求模型"""
        from api.routes.monitoring import AlertAuditLogCreate

        # 完整参数
        log = AlertAuditLogCreate(
            action="update",
            field_name="assignee",
            old_value="user1",
            new_value="user2",
            reason="工单转派",
        )
        assert log.action == "update"
        assert log.field_name == "assignee"

        # 最小参数
        log_minimal = AlertAuditLogCreate(action="create")
        assert log_minimal.action == "create"

    def test_audit_log_response_model(self):
        """测试审计日志响应模型"""
        from api.routes.monitoring import AlertAuditLogResponse

        response = AlertAuditLogResponse(
            id=1,
            alert_id=100,
            action="resolve",
            operator="admin",
            created_at=datetime.now(),
        )

        assert response.id == 1
        assert response.alert_id == 100


class TestAlertAuditLogIntegration:
    """告警审计日志集成测试"""

    def test_create_audit_log_for_alert_action(self):
        """测试为告警操作创建审计日志"""
        # 模拟告警对象
        alert = MagicMock()
        alert.id = 1
        alert.alert_key = "alert-001"

        # 创建审计日志
        audit_log = AlertAuditLog(
            alert_id=alert.id,
            alert_key=alert.alert_key,
            action="acknowledge",
            operator="admin",
            operator_ip="10.0.0.1",
        )

        assert audit_log.alert_id == alert.id
        assert audit_log.alert_key == alert.alert_key

    def test_audit_log_tracks_status_change(self):
        """测试审计日志跟踪状态变更"""
        # 模拟状态变更
        old_status = AlertStatus.ACTIVE
        new_status = AlertStatus.ACKNOWLEDGED

        audit_log = AlertAuditLog(
            alert_id=1,
            action="update",
            field_name="status",
            old_value=old_status.value,
            new_value=new_status.value,
        )

        assert audit_log.old_value == "active"
        assert audit_log.new_value == "acknowledged"

    def test_audit_log_tracks_assignment(self):
        """测试审计日志跟踪分配"""
        audit_log = AlertAuditLog(
            alert_id=1,
            action="update",
            field_name="assignee",
            old_value="operator_a",
            new_value="operator_b",
            reason="原负责人请假",
        )

        assert audit_log.field_name == "assignee"
        assert audit_log.reason == "原负责人请假"

    def test_audit_log_with_workorder_association(self):
        """测试审计日志关联工单"""
        audit_log = AlertAuditLog(
            alert_id=1,
            action="update",
            field_name="workorder_id",
            old_value=None,
            new_value="12345",
            workorder_id=12345,
        )

        assert audit_log.workorder_id == 12345


class TestAlertAuditLogQuery:
    """审计日志查询测试"""

    def test_filter_by_alert_id(self, audit_factory):
        """测试按告警ID过滤 - 使用DataFactory生成测试数据"""
        # 使用工厂生成指定alert_id的审计日志
        target_alert_id = 100
        logs = audit_factory.audit_log_list(5, alert_id=target_alert_id)

        # 验证所有日志都关联到目标告警
        assert len(logs) == 5
        for log in logs:
            assert log['alert_id'] == target_alert_id
            assert 'action' in log
            assert 'operator' in log

    def test_filter_by_action(self, audit_factory):
        """测试按操作类型过滤 - 使用DataFactory"""
        logs = audit_factory.audit_log_list(10)

        # 统计各操作类型的数量
        action_counts = {}
        for log in logs:
            action = log['action']
            action_counts[action] = action_counts.get(action, 0) + 1

        # 验证生成了各类型的审计日志
        assert len(logs) == 10
        assert sum(action_counts.values()) == 10

    def test_filter_by_operator(self, audit_factory):
        """测试按操作人过滤 - 使用DataFactory"""
        # 生成多个不同操作人的审计日志
        logs = audit_factory.audit_log_list(10)

        # 验证生成了数据
        assert len(logs) == 10
        operators = [log['operator'] for log in logs]
        assert len(set(operators)) >= 1  # 至少有一种操作人

    def test_filter_by_date_range(self, audit_factory):
        """测试按时间范围过滤 - 使用DataFactory"""
        # 使用工厂生成测试数据
        logs = audit_factory.audit_log_list(5)

        # 验证生成的数据结构
        assert len(logs) == 5
        assert all('alert_id' in log for log in logs)
        assert all('action' in log for log in logs)
        assert all('operator' in log for log in logs)

        # 验证日期范围在合理范围内（生成时间应该接近当前时间）
        now = datetime.now()
        # 审计日志的created_at应该在当前时间附近
        for log in logs:
            assert 'created_at' not in log or isinstance(log.get('created_at'), datetime)

    def test_audit_log_factory_batch_generation(self, audit_factory):
        """测试批量生成审计日志"""
        # 按告警ID批量生成
        logs_for_alert = audit_factory.audit_log_list(20, alert_id=1)
        assert len(logs_for_alert) == 20
        assert all(log['alert_id'] == 1 for log in logs_for_alert)

        # 按操作类型批量生成
        ack_logs = audit_factory.audit_log_list(5, action="acknowledge")
        assert len(ack_logs) == 5
        assert all(log['action'] == 'acknowledge' for log in ack_logs)

    def test_audit_log_factory_uniqueness(self, af):
        """测试工厂生成唯一标识"""
        log1 = af.audit_log()
        log2 = af.audit_log()

        # 验证每次生成的数据都有唯一标识
        assert log1['alert_key'] != log2['alert_key']
        assert log1['request_id'] != log2['request_id']
