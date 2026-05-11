# -*- coding: utf-8 -*-
"""
告警管理API集成测试

遵循Google测试最佳实践:
- Given-When-Then结构
- 测试通过公共API
- 测试业务工作流，不测试内部实现
- 使用 f 工厂fixture生成所有测试数据

注意: 告警接口位于 /api/v1/monitoring/alerts
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAlertAPI:
    """告警管理API测试类"""

    @pytest.fixture
    def mock_alert_query(self, db_session):
        """模拟告警查询"""
        with patch.object(db_session, 'query') as mock_query:
            yield mock_query

    # ============== 告警列表接口 ==============

    def test_get_alerts_empty(self, client, admin_headers, mock_alert_query):
        """Given: 系统中无告警
           When: 获取告警列表
           Then: 返回空列表"""
        mock_alert_query.return_value.filter.return_value.count.return_value = 0
        mock_alert_query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_alerts_with_data(self, client, admin_headers, f, mock_alert_query):
        """Given: 系统中有告警
           When: 获取告警列表
           Then: 返回告警列表"""
        alerts = [
            MagicMock(
                id=1,
                alert_key="cpu-alert-001",
                device_id=1,
                device_name="web-server-01",
                device_ip="192.168.1.10",
                level=MagicMock(value="critical"),
                category=MagicMock(value="cpu"),
                title="CPU使用率过高",
                message="CPU使用率超过90%",
                metric_name="cpu_usage",
                metric_value="95.5",
                threshold="90",
                unit="%",
                status=MagicMock(value="active"),
                first_occurred_at=datetime.now() - timedelta(hours=1),
                occurred_at=datetime.now() - timedelta(hours=1),
                created_at=datetime.now() - timedelta(hours=1),
                updated_at=datetime.now(),
            ),
            MagicMock(
                id=2,
                alert_key="memory-alert-001",
                device_id=2,
                device_name="db-server-01",
                device_ip="192.168.1.20",
                level=MagicMock(value="high"),
                category=MagicMock(value="memory"),
                title="内存使用率过高",
                message="内存使用率超过85%",
                metric_name="memory_usage",
                metric_value="87.3",
                threshold="85",
                unit="%",
                status=MagicMock(value="acknowledged"),
                first_occurred_at=datetime.now() - timedelta(hours=2),
                occurred_at=datetime.now() - timedelta(hours=2),
                acknowledged_at=datetime.now() - timedelta(hours=1),
                created_at=datetime.now() - timedelta(hours=2),
                updated_at=datetime.now() - timedelta(hours=1),
            ),
        ]
        
        mock_alert_query.return_value.count.return_value = 2
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = alerts
        
        response = client.get(
            "/api/v1/monitoring/alerts",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_get_alerts_with_status_filter(self, client, admin_headers, f, mock_alert_query):
        """Given: 系统中有多种状态告警
           When: 按状态过滤
           Then: 返回指定状态告警"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?status=active",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alerts_with_severity_filter(self, client, admin_headers, f, mock_alert_query):
        """Given: 系统中有多种严重程度告警
           When: 按严重程度过滤
           Then: 返回指定严重程度告警"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?severity=critical",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alerts_with_host_filter(self, client, admin_headers, f, mock_alert_query):
        """Given: 系统中有多个主机告警
           When: 按主机过滤
           Then: 返回指定主机的告警"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?host=web-server",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alerts_with_pagination(self, client, admin_headers, f, mock_alert_query):
        """Given: 系统中有多个告警
           When: 请求分页
           Then: 返回指定页的数据"""
        mock_alert_query.return_value.count.return_value = 100
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?page=2&page_size=20",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100

    def test_get_alerts_unauthorized(self, client):
        """Given: 未认证用户
           When: 获取告警列表
           Then: 返回401"""
        response = client.get("/api/v1/monitoring/alerts")
        assert response.status_code == 401

    # ============== 创建告警接口 ==============

    def test_create_alert_success(self, client, admin_headers, f, db_session):
        """Given: 有效的告警数据
           When: 创建告警
           Then: 返回创建的告警"""
        with patch.object(db_session, 'add'), \
             patch.object(db_session, 'commit'), \
             patch.object(db_session, 'refresh') as mock_refresh:
            
            mock_refresh.side_effect = lambda x: setattr(x, 'id', 1) or setattr(x, 'created_at', datetime.now())
            
            response = client.post(
                "/api/v1/monitoring/alerts",
                json={
                    "title": "CPU告警",
                    "severity": "critical",
                    "description": "CPU使用率超过95%",
                    "host": "web-server-01",
                    "metric_name": "cpu_usage",
                    "threshold": 90.0,
                    "current_value": 95.5,
                },
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["title"] == "CPU告警"

    def test_create_alert_minimal(self, client, admin_headers, f, db_session):
        """Given: 最少告警数据
           When: 创建告警
           Then: 返回创建的告警"""
        with patch.object(db_session, 'add'), \
             patch.object(db_session, 'commit'), \
             patch.object(db_session, 'refresh') as mock_refresh:
            
            mock_refresh.side_effect = lambda x: setattr(x, 'id', 2) or setattr(x, 'created_at', datetime.now())
            
            response = client.post(
                "/api/v1/monitoring/alerts",
                json={
                    "title": "简单告警",
                    "severity": "info",
                },
                headers=admin_headers
            )
            
            assert response.status_code == 200

    def test_create_alert_with_device_info(self, client, admin_headers, f, db_session):
        """Given: 告警关联设备信息
           When: 创建告警
           Then: 返回创建的告警"""
        with patch.object(db_session, 'add'), \
             patch.object(db_session, 'commit'), \
             patch.object(db_session, 'refresh') as mock_refresh:
            
            mock_refresh.side_effect = lambda x: setattr(x, 'id', 3) or setattr(x, 'created_at', datetime.now())
            
            response = client.post(
                "/api/v1/monitoring/alerts",
                json={
                    "title": "内存告警",
                    "severity": "high",
                    "description": "内存使用率过高",
                    "host": "db-server-01",
                    "metric_name": "memory_usage",
                    "threshold": 85.0,
                    "current_value": 88.5,
                },
                headers=admin_headers
            )
            
            assert response.status_code == 200

    # ============== 告警详情接口 ==============

    def test_get_alert_not_found(self, client, admin_headers, mock_alert_query):
        """Given: 告警不存在
           When: 获取告警详情
           Then: 返回404"""
        mock_alert_query.return_value.filter.return_value.first.return_value = None
        
        response = client.get(
            "/api/v1/monitoring/alerts/9999",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_get_alert_found(self, client, admin_headers, mock_alert_query):
        """Given: 告警存在
           When: 获取告警详情
           Then: 返回告警详情"""
        mock_alert_query.return_value.filter.return_value.first.return_value = MagicMock(
            id=1,
            alert_key="cpu-alert-001",
            device_id=1,
            device_name="web-server-01",
            device_ip="192.168.1.10",
            level=MagicMock(value="critical"),
            category=MagicMock(value="cpu"),
            title="CPU使用率过高",
            message="CPU使用率超过90%",
            metric_name="cpu_usage",
            metric_value="95.5",
            threshold="90",
            unit="%",
            status=MagicMock(value="active"),
            first_occurred_at=datetime.now() - timedelta(hours=1),
            occurred_at=datetime.now() - timedelta(hours=1),
            acknowledged_at=None,
            resolved_at=None,
            acknowledged_by=None,
            resolved_by=None,
            resolution_note=None,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now(),
        )
        
        response = client.get(
            "/api/v1/monitoring/alerts/1",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    # ============== 确认告警接口 ==============

    def test_acknowledge_alert_success(self, client, admin_headers, mock_alert_query):
        """Given: 告警存在且未确认
           When: 确认告警
           Then: 返回成功"""
        alert = MagicMock(
            id=1,
            status=MagicMock(value="active"),
        )
        mock_alert_query.return_value.filter.return_value.first.return_value = alert
        
        response = client.put(
            "/api/v1/monitoring/alerts/1/acknowledge",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_acknowledge_alert_not_found(self, client, admin_headers, mock_alert_query):
        """Given: 告警不存在
           When: 确认告警
           Then: 返回404"""
        mock_alert_query.return_value.filter.return_value.first.return_value = None
        
        response = client.put(
            "/api/v1/monitoring/alerts/9999/acknowledge",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    # ============== 解决告警接口 ==============

    def test_resolve_alert_success(self, client, admin_headers, mock_alert_query):
        """Given: 告警存在且已确认
           When: 解决告警
           Then: 返回成功"""
        alert = MagicMock(
            id=1,
            status=MagicMock(value="acknowledged"),
        )
        mock_alert_query.return_value.filter.return_value.first.return_value = alert
        
        response = client.put(
            "/api/v1/monitoring/alerts/1/resolve",
            json={"resolution_note": "已重启服务"},
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_resolve_alert_not_found(self, client, admin_headers, mock_alert_query):
        """Given: 告警不存在
           When: 解决告警
           Then: 返回404"""
        mock_alert_query.return_value.filter.return_value.first.return_value = None
        
        response = client.put(
            "/api/v1/monitoring/alerts/9999/resolve",
            json={"resolution_note": "已处理"},
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_resolve_alert_with_note(self, client, admin_headers, mock_alert_query):
        """Given: 告警存在
           When: 解决告警并添加备注
           Then: 返回成功"""
        alert = MagicMock(id=1, status=MagicMock(value="acknowledged"))
        mock_alert_query.return_value.filter.return_value.first.return_value = alert
        
        response = client.put(
            "/api/v1/monitoring/alerts/1/resolve",
            json={"resolution_note": "CPU使用率已恢复正常"},
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 删除告警接口 ==============

    def test_delete_alert_success(self, client, admin_headers, mock_alert_query):
        """Given: 告警存在
           When: 删除告警
           Then: 返回成功"""
        alert = MagicMock(id=1)
        mock_alert_query.return_value.filter.return_value.first.return_value = alert
        
        with patch.object(db_session, 'delete'), \
             patch.object(db_session, 'commit'):
            
            response = client.delete(
                "/api/v1/monitoring/alerts/1",
                headers=admin_headers
            )
            
            assert response.status_code == 200

    def test_delete_alert_not_found(self, client, admin_headers, mock_alert_query):
        """Given: 告警不存在
           When: 删除告警
           Then: 返回404"""
        mock_alert_query.return_value.filter.return_value.first.return_value = None
        
        response = client.delete(
            "/api/v1/monitoring/alerts/9999",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    # ============== 告警统计接口 ==============

    def test_get_alert_stats(self, client, admin_headers, mock_alert_query):
        """Given: 系统有告警
           When: 获取告警统计
           Then: 返回统计信息"""
        response = client.get(
            "/api/v1/monitoring/alerts/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alert_stats_by_level(self, client, admin_headers, mock_alert_query):
        """Given: 系统有告警
           When: 按级别获取告警统计
           Then: 返回统计信息"""
        response = client.get(
            "/api/v1/monitoring/alerts/stats/by-level",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alert_stats_by_status(self, client, admin_headers, mock_alert_query):
        """Given: 系统有告警
           When: 按状态获取告警统计
           Then: 返回统计信息"""
        response = client.get(
            "/api/v1/monitoring/alerts/stats/by-status",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 告警规则接口 ==============

    def test_get_alert_rules(self, client, admin_headers, mock_alert_query):
        """Given: 系统有告警规则
           When: 获取告警规则列表
           Then: 返回规则列表"""
        response = client.get(
            "/api/v1/monitoring/alerts/rules",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_create_alert_rule(self, client, admin_headers, f, mock_alert_query):
        """Given: 有效的告警规则数据
           When: 创建告警规则
           Then: 返回创建的规则"""
        response = client.post(
            "/api/v1/monitoring/alerts/rules",
            json={
                "name": "CPU高使用率告警",
                "condition": "cpu_usage > 90",
                "severity": "high",
                "enabled": True,
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_update_alert_rule(self, client, admin_headers, mock_alert_query):
        """Given: 告警规则存在
           When: 更新告警规则
           Then: 返回成功"""
        response = client.put(
            "/api/v1/monitoring/alerts/rules/1",
            json={
                "condition": "cpu_usage > 95",
                "severity": "critical",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_delete_alert_rule(self, client, admin_headers, mock_alert_query):
        """Given: 告警规则存在
           When: 删除告警规则
           Then: 返回成功"""
        response = client.delete(
            "/api/v1/monitoring/alerts/rules/1",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 告警历史接口 ==============

    def test_get_alert_history(self, client, admin_headers, mock_alert_query):
        """Given: 系统有告警历史
           When: 获取告警历史
           Then: 返回历史记录"""
        response = client.get(
            "/api/v1/monitoring/alerts/history?days=7",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_alert_history_by_host(self, client, admin_headers, mock_alert_query):
        """Given: 系统有指定主机告警历史
           When: 获取主机告警历史
           Then: 返回历史记录"""
        response = client.get(
            "/api/v1/monitoring/alerts/history?host=web-server-01&days=30",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 权限测试 ==============

    def test_operator_can_view_alerts(self, client, operator_headers, mock_alert_query):
        """Given: 操作员已认证
           When: 获取告警列表
           Then: 返回告警列表"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts",
            headers=operator_headers
        )
        
        assert response.status_code == 200

    def test_viewer_can_view_alerts(self, client, viewer_headers, mock_alert_query):
        """Given: 访客已认证
           When: 获取告警列表
           Then: 返回告警列表"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts",
            headers=viewer_headers
        )
        
        assert response.status_code == 200

    def test_viewer_cannot_create_alert(self, client, viewer_headers, f, db_session):
        """Given: 访客已认证
           When: 创建告警
           Then: 返回403"""
        response = client.post(
            "/api/v1/monitoring/alerts",
            json={
                "title": "访客告警",
                "severity": "info",
            },
            headers=viewer_headers
        )
        
        assert response.status_code == 403

    # ============== 验证测试 ==============

    def test_create_alert_invalid_severity(self, client, admin_headers, f, db_session):
        """Given: 无效的严重程度
           When: 创建告警
           Then: 返回422验证错误"""
        response = client.post(
            "/api/v1/monitoring/alerts",
            json={
                "title": "测试告警",
                "severity": "invalid_severity",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 422

    def test_create_alert_missing_title(self, client, admin_headers, f, db_session):
        """Given: 缺少必需字段标题
           When: 创建告警
           Then: 返回422验证错误"""
        response = client.post(
            "/api/v1/monitoring/alerts",
            json={
                "severity": "critical",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 422

    # ============== 过滤组合测试 ==============

    def test_filter_by_status_and_severity(self, client, admin_headers, mock_alert_query):
        """Given: 系统有多种状态和级别的告警
           When: 按状态和严重程度组合过滤
           Then: 返回匹配的告警"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?status=active&severity=critical",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_multiple_criteria(self, client, admin_headers, mock_alert_query):
        """Given: 系统有多种条件的告警
           When: 按多个条件过滤
           Then: 返回匹配的告警"""
        mock_alert_query.return_value.count.return_value = 0
        mock_alert_query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        response = client.get(
            "/api/v1/monitoring/alerts?status=active&severity=high&host=web-server",
            headers=admin_headers
        )
        
        assert response.status_code == 200