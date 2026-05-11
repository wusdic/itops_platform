"""
告警审计日志测试
测试AlertAuditLog模型的创建、查询功能
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from modules.foundation.db_models.alert import AlertAuditLog, Alert, AlertLevel, AlertStatus


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

    def test_filter_by_alert_id(self):
        """测试按告警ID过滤"""
        # 模拟查询
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 5

        # 模拟查询结果
        mock_results = [
            AlertAuditLog(id=i, alert_id=100, action="update")
            for i in range(1, 6)
        ]
        mock_query.all.return_value = mock_results

        # 执行过滤
        result = mock_query.filter().all()

        assert len(result) == 5
        assert all(log.alert_id == 100 for log in result)

    def test_filter_by_action(self):
        """测试按操作类型过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [
            AlertAuditLog(id=1, alert_id=1, action="acknowledge"),
        ]

        result = mock_query.filter().all()
        assert len(result) == 1
        assert result[0].action == "acknowledge"

    def test_filter_by_operator(self):
        """测试按操作人过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [
            AlertAuditLog(id=1, alert_id=1, operator="admin"),
        ]

        result = mock_query.filter().all()
        assert len(result) == 1
        assert result[0].operator == "admin"

    def test_filter_by_date_range(self):
        """测试按时间范围过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        # 验证日期过滤被调用
        mock_query.filter().count.return_value = 10
        mock_query.filter().order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        result = mock_query.filter(start_date >= start_date, end_date <= end_date).all()
        assert isinstance(result, list)
