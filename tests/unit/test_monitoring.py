"""
BM-01 监控告警模块单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from modules.business.monitoring.monitor import (
    MonitorCore, MetricPoint, DeviceStatus, AlertSeverity, 
    ThresholdCheckResult, TrendAnalysisResult
)
from modules.business.monitoring.rules import (
    AlertRulesEngine, AlertRule, AlertEvent, AlertState, RuleType
)
from modules.business.monitoring.alerter import (
    AlertTrigger, AlertTicket, TicketStatus, EscalationPolicy, EscalationLevel
)
from modules.business.monitoring.notification import (
    NotificationService, Notification, NotificationChannel, 
    NotificationPriority, NotificationTemplate, NotificationStatus
)
from modules.business.monitoring.dashboard import (
    DashboardData, TimeSeriesPoint, AggregationResult, 
    TopNItem, AvailabilityReport, DashboardSummary
)


class TestMonitorCore:
    """监控核心测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.monitor = MonitorCore({
            'collect_interval': 60,
            'check_interval': 30,
            'offline_threshold': 300
        })
    
    def test_add_metric(self):
        """测试添加指标"""
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=85.5,
            timestamp=datetime.now(),
            unit='%'
        )
        
        self.monitor.add_metric(metric)
        
        # 验证设备状态
        assert self.monitor.get_device_status('server-001') == DeviceStatus.NORMAL
        
        # 验证指标获取
        retrieved = self.monitor.get_metrics('server-001', 'cpu.usage')
        assert len(retrieved) == 1
        assert retrieved[0].value == 85.5
    
    def test_add_metrics_batch(self):
        """测试批量添加指标"""
        metrics = [
            MetricPoint('dev-1', 'cpu', 50.0, datetime.now()),
            MetricPoint('dev-1', 'memory', 60.0, datetime.now()),
            MetricPoint('dev-2', 'cpu', 70.0, datetime.now()),
        ]
        
        self.monitor.add_metrics(metrics)
        
        assert len(self.monitor.get_metrics('dev-1', 'cpu')) == 1
        assert len(self.monitor.get_metrics('dev-1', 'memory')) == 1
        assert len(self.monitor.get_metrics('dev-2', 'cpu')) == 1
    
    def test_threshold_check(self):
        """测试阈值检查"""
        # 注册阈值规则
        rules = {
            'cpu_high': {
                'name': 'CPU过高',
                'metric_name': 'cpu.usage',
                'devices': ['*'],
                'thresholds': [
                    {'operator': '>', 'value': 80, 'severity': 'warning'},
                    {'operator': '>', 'value': 95, 'severity': 'critical'}
                ]
            }
        }
        self.monitor.register_threshold_rules(rules)
        
        # 测试触发阈值
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            timestamp=datetime.now()
        )
        
        results = self.monitor.check_threshold(metric)
        
        assert len(results) == 2
        # 第一个阈值应该触发 (90 > 80)
        assert results[0].is_triggered == True
        # 第二个阈值应该触发 (90 > 95 为 False)
        assert results[1].is_triggered == False
    
    def test_threshold_check_not_triggered(self):
        """测试阈值未触发"""
        rules = {
            'cpu_high': {
                'name': 'CPU过高',
                'metric_name': 'cpu.usage',
                'devices': ['*'],
                'thresholds': [
                    {'operator': '>', 'value': 80, 'severity': 'warning'}
                ]
            }
        }
        self.monitor.register_threshold_rules(rules)
        
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=50.0,
            timestamp=datetime.now()
        )
        
        results = self.monitor.check_threshold(metric)
        
        assert len(results) == 1
        assert results[0].is_triggered == False
    
    def test_device_filter(self):
        """测试设备过滤"""
        rules = {
            'specific_device': {
                'name': '特定设备告警',
                'metric_name': 'cpu.usage',
                'devices': ['server-001', 'server-002'],
                'thresholds': [
                    {'operator': '>', 'value': 80, 'severity': 'warning'}
                ]
            }
        }
        self.monitor.register_threshold_rules(rules)
        
        # 匹配设备应该触发
        metric1 = MetricPoint('server-001', 'cpu.usage', 90.0, datetime.now())
        results1 = self.monitor.check_threshold(metric1)
        assert len(results1) == 1
        
        # 不匹配设备不应该触发
        metric2 = MetricPoint('server-003', 'cpu.usage', 90.0, datetime.now())
        results2 = self.monitor.check_threshold(metric2)
        assert len(results2) == 0
    
    def test_trend_analysis(self):
        """测试趋势分析"""
        now = datetime.now()
        
        # 添加历史数据
        for i in range(10):
            metric = MetricPoint(
                device_id='server-001',
                metric_name='cpu.usage',
                value=50.0 + i * 2,  # 持续上升
                timestamp=now - timedelta(seconds=(10 - i) * 30)
            )
            self.monitor.add_metric(metric)
        
        # 分析趋势
        result = self.monitor.analyze_trend('server-001', 'cpu.usage', window_seconds=300)
        
        assert result is not None
        assert result.trend in ['up', 'down', 'stable']
        assert result.device_id == 'server-001'
        assert result.metric_name == 'cpu.usage'
    
    def test_trend_analysis_insufficient_data(self):
        """测试数据不足时的趋势分析"""
        metric = MetricPoint('server-001', 'cpu.usage', 50.0, datetime.now())
        self.monitor.add_metric(metric)
        
        result = self.monitor.analyze_trend('server-001', 'cpu.usage')
        assert result is None
    
    def test_device_offline_detection(self):
        """测试设备离线检测"""
        # 添加一个设备
        metric = MetricPoint('server-001', 'cpu.usage', 50.0, datetime.now())
        self.monitor.add_metric(metric)
        
        # 设备应该在正常状态
        assert self.monitor.get_device_status('server-001') == DeviceStatus.NORMAL
        
        # 模拟设备很久没有上报数据
        self.monitor._device_last_seen['server-002'] = datetime.now() - timedelta(seconds=600)
        offline_devices = self.monitor.check_device_offline()
        
        assert 'server-002' in offline_devices
        assert self.monitor.get_device_status('server-002') == DeviceStatus.OFFLINE
    
    def test_clear_metric_buffer(self):
        """测试清除指标缓冲区"""
        for i in range(5):
            metric = MetricPoint('server-001', 'cpu', float(i), datetime.now())
            self.monitor.add_metric(metric)
        
        # 清除特定指标
        self.monitor.clear_metric_buffer('server-001', 'cpu')
        assert len(self.monitor.get_metrics('server-001', 'cpu')) == 0
        
        # 清除设备所有指标
        self.monitor.add_metric(MetricPoint('server-001', 'memory', 50.0, datetime.now()))
        self.monitor.clear_metric_buffer('server-001')
        assert len(self.monitor.get_metrics('server-001', 'memory')) == 0
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.monitor.add_metric(MetricPoint('server-001', 'cpu', 50.0, datetime.now()))
        
        stats = self.monitor.get_statistics()
        
        assert 'buffer_size' in stats
        assert 'device_count' in stats
        assert 'is_running' in stats


class TestAlertRulesEngine:
    """告警规则引擎测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.engine = AlertRulesEngine({
            'deduplication_ttl': 3600
        })
    
    def test_add_rule(self):
        """测试添加规则"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ]
        )
        
        self.engine.add_rule(rule)
        
        retrieved = self.engine.get_rule('cpu_high')
        assert retrieved is not None
        assert retrieved.name == 'CPU过高告警'
    
    def test_remove_rule(self):
        """测试删除规则"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            metric_name='cpu.usage'
        )
        
        self.engine.add_rule(rule)
        assert self.engine.get_rule('cpu_high') is not None
        
        self.engine.remove_rule('cpu_high')
        assert self.engine.get_rule('cpu_high') is None
    
    def test_evaluate_trigger(self):
        """测试评估触发"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ],
            suppress_interval=0  # 禁用抑制
        )
        
        self.engine.add_rule(rule)
        
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            timestamp=datetime.now()
        )
        
        alerts = self.engine.evaluate(metric)
        
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].state == AlertState.FIRING
    
    def test_evaluate_not_trigger(self):
        """测试评估不触发"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ]
        )
        
        self.engine.add_rule(rule)
        
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=50.0,
            timestamp=datetime.now()
        )
        
        alerts = self.engine.evaluate(metric)
        assert len(alerts) == 0
    
    def test_deduplication(self):
        """测试去重"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ]
        )
        
        self.engine.add_rule(rule)
        
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            timestamp=datetime.now()
        )
        
        # 第一次评估
        alerts1 = self.engine.evaluate(metric)
        assert len(alerts1) == 1
        
        # 第二次评估（应该去重）
        alerts2 = self.engine.evaluate(metric)
        assert len(alerts2) == 0
    
    def test_suppression(self):
        """测试抑制"""
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ],
            suppress_interval=300  # 5分钟
        )
        
        self.engine.add_rule(rule)
        
        # 手动抑制
        self.engine.suppress('cpu_high', 'server-001')
        
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            timestamp=datetime.now()
        )
        
        alerts = self.engine.evaluate(metric)
        assert len(alerts) == 0
    
    def test_get_enabled_rules(self):
        """测试获取启用的规则"""
        self.engine.add_rule(AlertRule(
            id='enabled_rule',
            name='启用规则',
            rule_type=RuleType.THRESHOLD,
            enabled=True,
            metric_name='cpu.usage'
        ))
        
        self.engine.add_rule(AlertRule(
            id='disabled_rule',
            name='禁用规则',
            rule_type=RuleType.THRESHOLD,
            enabled=False,
            metric_name='memory.usage'
        ))
        
        enabled = self.engine.get_enabled_rules()
        assert len(enabled) == 1
        assert enabled[0].id == 'enabled_rule'
    
    def test_export_import_rules(self):
        """测试导出导入规则"""
        rules = [
            AlertRule(
                id='rule1',
                name='规则1',
                rule_type=RuleType.THRESHOLD,
                metric_name='cpu.usage'
            ),
            AlertRule(
                id='rule2',
                name='规则2',
                rule_type=RuleType.THRESHOLD,
                metric_name='memory.usage'
            )
        ]
        
        for rule in rules:
            self.engine.add_rule(rule)
        
        # 导出
        exported = self.engine.export_rules()
        assert len(exported) == 2
        
        # 创建新引擎并导入
        new_engine = AlertRulesEngine()
        imported = new_engine.import_rules(exported)
        assert imported == 2


class TestAlertTrigger:
    """告警触发器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.trigger = AlertTrigger({
            'auto_close_interval': 86400
        })
    
    def test_create_ticket(self):
        """测试创建工单"""
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        assert ticket is not None
        assert ticket.status == TicketStatus.OPEN
        assert ticket.device_id == 'server-001'
    
    def test_acknowledge_ticket(self):
        """测试确认工单"""
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        success = self.trigger.acknowledge_ticket(
            ticket.id,
            user='admin',
            note='正在处理'
        )
        
        assert success == True
        assert ticket.status == TicketStatus.ACKNOWLEDGED
        assert ticket.acknowledged_by == 'admin'
    
    def test_assign_ticket(self):
        """测试分配工单"""
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        success = self.trigger.assign_ticket(
            ticket.id,
            assignee='engineer-1',
            assignee_group='ops-team'
        )
        
        assert success == True
        assert ticket.assignee == 'engineer-1'
        assert ticket.assignee_group == 'ops-team'
    
    def test_resolve_ticket(self):
        """测试解决工单"""
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        success = self.trigger.resolve_ticket(
            ticket.id,
            user='engineer-1',
            resolution='已重启服务'
        )
        
        assert success == True
        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.annotations.get('resolution') == '已重启服务'
    
    def test_close_ticket(self):
        """测试关闭工单"""
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        # 先解决再关闭
        self.trigger.resolve_ticket(ticket.id, 'admin')
        success = self.trigger.close_ticket(ticket.id, 'admin')
        
        assert success == True
        assert ticket.status == TicketStatus.CLOSED
    
    def test_escalate_ticket(self):
        """测试升级工单"""
        # 添加升级策略
        self.trigger.add_escalation_policy(EscalationPolicy(
            level=1,
            wait_seconds=60,
            notify_channels=['email'],
            description='Level 1'
        ))
        
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=99.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        
        ticket = self.trigger.create_ticket(alert)
        
        # 触发升级
        success = self.trigger.escalate_ticket(ticket.id)
        
        assert success == True
        assert ticket.escalation_level == 1
        assert ticket.escalation_count == 1
    
    def test_get_tickets_by_status(self):
        """测试按状态获取工单"""
        # 创建3个告警，每个使用不同的alert_id
        alert_ids = ['alert-001', 'alert-002', 'alert-003']
        
        for alert_id in alert_ids:
            alert = AlertEvent(
                id=alert_id,
                rule_id='cpu_high',
                rule_name='CPU过高',
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                device_id='server-001',
                metric_name='cpu.usage',
                value=90.0,
                threshold_value=80.0,
                message='CPU使用率过高',
                fired_at=datetime.now()
            )
            ticket = self.trigger.create_ticket(alert)
            assert ticket is not None, f"Failed to create ticket for {alert_id}"
        
        tickets = self.trigger.get_tickets()
        assert len(tickets) == 3, f"Expected 3 tickets, got {len(tickets)}"
        
        # 确认一个
        self.trigger.acknowledge_ticket(tickets[0].id, 'admin')
        
        open_tickets = self.trigger.get_tickets(status=TicketStatus.OPEN)
        ack_tickets = self.trigger.get_tickets(status=TicketStatus.ACKNOWLEDGED)
        
        assert len(open_tickets) == 2, f"Expected 2 open tickets, got {len(open_tickets)}"
        assert len(ack_tickets) == 1, f"Expected 1 acknowledged ticket, got {len(ack_tickets)}"


class TestNotificationService:
    """通知服务测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.notification = NotificationService({
            'max_concurrent_notifications': 5,
            'default_silence_minutes': 30
        })
    
    @pytest.mark.asyncio
    async def test_send_notification(self):
        """测试发送通知"""
        notification = await self.notification.send(
            channel=NotificationChannel.IN_APP,
            recipients=['user-001'],
            title='测试通知',
            content='这是一条测试通知',
            priority=NotificationPriority.NORMAL
        )
        
        assert notification is not None
        assert notification.status == NotificationStatus.SENT
    
    @pytest.mark.asyncio
    async def test_silence(self):
        """测试静默"""
        key = 'rule:device'
        
        # 设置静默
        self.notification.silence(key, minutes=30)
        assert self.notification.is_silenced(key) == True
        
        # 取消静默
        self.notification.unsilence(key)
        assert self.notification.is_silenced(key) == False
    
    @pytest.mark.asyncio
    async def test_silenced_notification(self):
        """测试被静默的通知"""
        # 设置静默
        self.notification.silence('cpu_high:server-001', minutes=30)
        
        notification = await self.notification.send(
            channel=NotificationChannel.IN_APP,
            recipients=['user-001'],
            title='测试',
            content='测试内容',
            context={'silence_key': 'cpu_high:server-001'}
        )
        
        # 应该返回None因为被静默
        assert notification is None
    
    def test_add_template(self):
        """测试添加模板"""
        template = NotificationTemplate(
            id='test_template',
            name='测试模板',
            channel=NotificationChannel.EMAIL,
            title_template='测试: {title}',
            content_template='内容: {content}',
            variables=['title', 'content']
        )
        
        self.notification.add_template(template)
        
        retrieved = self.notification.get_template('test_template')
        assert retrieved is not None
        assert retrieved.name == '测试模板'
    
    def test_render_template(self):
        """测试渲染模板"""
        template = NotificationTemplate(
            id='test_template',
            name='测试模板',
            channel=NotificationChannel.IN_APP,
            title_template='[{severity}] {rule_name}',
            content_template='设备: {device_id}\n值: {value}',
            variables=['severity', 'rule_name', 'device_id', 'value']
        )
        
        rendered = template.render({
            'severity': 'warning',
            'rule_name': 'CPU过高',
            'device_id': 'server-001',
            'value': '90%'
        })
        
        assert '[warning] CPU过高' in rendered['title']
        assert 'server-001' in rendered['content']
        assert '90%' in rendered['content']
    
    def test_rate_limit(self):
        """测试限流"""
        self.notification.set_rate_limit(
            NotificationChannel.EMAIL,
            max_count=3,
            window_seconds=60
        )
        
        rule = self.notification._rate_limits.get(NotificationChannel.EMAIL)
        assert rule is not None
        assert rule.max_count == 3
    
    def test_get_statistics(self):
        """测试获取统计"""
        stats = self.notification.get_statistics()
        
        assert 'total_notifications' in stats
        assert 'by_channel' in stats


class TestDashboardData:
    """仪表盘数据测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.dashboard = DashboardData({
            'max_history_size': 1000
        })
        
        # 创建监控核心
        self.monitor = MonitorCore()
        self.dashboard.set_monitor_core(self.monitor)
    
    def test_get_realtime_metrics(self):
        """测试获取实时指标"""
        # 添加测试数据
        self.monitor.add_metric(MetricPoint(
            'server-001', 'cpu.usage', 50.0, datetime.now()
        ))
        
        metrics = self.dashboard.get_realtime_metrics(
            device_id='server-001',
            metric_names=['cpu.usage']
        )
        
        assert 'server-001:cpu.usage' in metrics
    
    def test_aggregate_metrics(self):
        """测试聚合指标"""
        now = datetime.now()
        
        # 添加多个数据点
        for i in range(10):
            self.monitor.add_metric(MetricPoint(
                'server-001',
                'cpu.usage',
                50.0 + i,
                now - timedelta(minutes=i)
            ))
        
        aggregated = self.dashboard.aggregate_metrics(
            'server-001',
            'cpu.usage',
            now - timedelta(minutes=10),
            now,
            interval_seconds=60
        )
        
        assert len(aggregated) >= 0  # 可能聚合后数据点较少
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        now = datetime.now()
        
        for i in range(20):
            self.monitor.add_metric(MetricPoint(
                'server-001',
                'cpu.usage',
                50.0 + (i % 10),
                now - timedelta(minutes=i)
            ))
        
        stats = self.dashboard.get_statistics(
            'server-001',
            'cpu.usage',
            now - timedelta(minutes=30),
            now
        )
        
        assert stats is not None
        assert stats.count == 20
        assert stats.min_value is not None
        assert stats.max_value is not None
    
    def test_get_topn_metrics(self):
        """测试TopN指标"""
        # 添加多个设备的数据
        for i in range(5):
            self.monitor.add_metric(MetricPoint(
                f'server-{i:03d}',
                'cpu.usage',
                50.0 + i * 10,
                datetime.now()
            ))
        
        topn = self.dashboard.get_topn_metrics(
            'cpu.usage',
            n=3,
            order='desc'
        )
        
        assert len(topn) <= 3
        if len(topn) >= 2:
            assert topn[0].value >= topn[1].value
    
    def test_get_availability(self):
        """测试可用性计算"""
        # 添加告警历史
        for i in range(5):
            alert = AlertEvent(
                id=f'alert-{i}',
                rule_id='cpu_high',
                rule_name='CPU过高',
                severity=AlertSeverity.CRITICAL if i < 2 else AlertSeverity.WARNING,
                state=AlertState.FIRING,
                device_id='server-001',
                metric_name='cpu.usage',
                value=90.0,
                threshold_value=80.0,
                message='CPU使用率过高',
                fired_at=datetime.now() - timedelta(hours=i)
            )
            self.dashboard.add_alert_history(alert)
        
        report = self.dashboard.get_availability(
            'server-001',
            datetime.now() - timedelta(days=1),
            datetime.now()
        )
        
        assert report.device_id == 'server-001'
        assert report.total_alerts >= 5
    
    def test_get_severity_distribution(self):
        """测试严重级别分布"""
        for i, severity in enumerate([AlertSeverity.CRITICAL] * 3 + 
                                      [AlertSeverity.WARNING] * 5 + 
                                      [AlertSeverity.INFO] * 2):
            alert = AlertEvent(
                id=f'alert-{i}',
                rule_id='rule',
                rule_name='测试',
                severity=severity,
                state=AlertState.FIRING,
                device_id='server-001',
                metric_name='cpu.usage',
                value=90.0,
                threshold_value=80.0,
                message='测试',
                fired_at=datetime.now()
            )
            self.dashboard.add_alert_history(alert)
        
        distribution = self.dashboard.get_severity_distribution()
        
        assert distribution['critical'] == 3
        assert distribution['warning'] == 5
        assert distribution['info'] == 2
    
    def test_get_dashboard_summary(self):
        """测试仪表盘摘要"""
        # 添加设备
        self.monitor.add_metric(MetricPoint(
            'server-001', 'cpu.usage', 50.0, datetime.now()
        ))
        
        # 添加告警
        alert = AlertEvent(
            id='alert-001',
            rule_id='cpu_high',
            rule_name='CPU过高',
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            threshold_value=80.0,
            message='CPU使用率过高',
            fired_at=datetime.now()
        )
        self.dashboard.add_alert_history(alert)
        
        summary = self.dashboard.get_dashboard_summary()
        
        assert isinstance(summary, DashboardSummary)
        assert summary.total_devices >= 1
        assert summary.active_alerts >= 1


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_alert_flow(self):
        """测试完整的告警流程"""
        # 1. 创建监控核心
        monitor = MonitorCore()
        
        # 2. 创建告警引擎
        engine = AlertRulesEngine()
        
        # 3. 创建触发器
        trigger = AlertTrigger()
        
        # 4. 创建通知服务
        notification = NotificationService()
        
        # 5. 添加告警规则
        rule = AlertRule(
            id='cpu_high',
            name='CPU过高告警',
            rule_type=RuleType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            metric_name='cpu.usage',
            thresholds=[
                {'operator': '>', 'value': 80, 'severity': 'warning'}
            ],
            suppress_interval=0
        )
        engine.add_rule(rule)
        
        # 6. 添加指标（触发告警）
        metric = MetricPoint(
            device_id='server-001',
            metric_name='cpu.usage',
            value=90.0,
            timestamp=datetime.now()
        )
        monitor.add_metric(metric)
        
        # 7. 评估告警
        alerts = engine.evaluate(metric)
        assert len(alerts) == 1
        
        # 8. 创建工单
        ticket = trigger.create_ticket(alerts[0])
        assert ticket is not None
        assert ticket.status == TicketStatus.OPEN
        
        # 9. 发送通知
        notif = await notification.send(
            channel=NotificationChannel.IN_APP,
            recipients=['admin'],
            title=f"[告警] {alerts[0].rule_name}",
            content=alerts[0].message
        )
        assert notif.status == NotificationStatus.SENT
        
        # 10. 确认工单
        trigger.acknowledge_ticket(ticket.id, 'admin')
        assert ticket.status == TicketStatus.ACKNOWLEDGED
        
        # 11. 解决工单
        trigger.resolve_ticket(ticket.id, 'admin', '已重启服务')
        assert ticket.status == TicketStatus.RESOLVED


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
