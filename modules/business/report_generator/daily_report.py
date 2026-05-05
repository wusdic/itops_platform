"""
日巡检报告生成器
生成每日运维巡检报告，包括监控数据汇总、告警统计、值班情况等
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .reporter import ReportGenerator, ReportType, Report, ReportStatus

logger = logging.getLogger(__name__)


@dataclass
class MonitoringSummary:
    """监控数据汇总"""
    total_hosts: int = 0
    online_hosts: int = 0
    offline_hosts: int = 0
    total_metrics: int = 0
    abnormal_metrics: int = 0
    cpu_avg_usage: float = 0.0
    memory_avg_usage: float = 0.0
    disk_avg_usage: float = 0.0
    network_in_avg: float = 0.0
    network_out_avg: float = 0.0


@dataclass
class AlertStatistics:
    """告警统计"""
    total_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    acknowledged_count: int = 0
    resolved_count: int = 0
    top_alerts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DutyInfo:
    """值班信息"""
    duty_person: str = ""
    shift_type: str = ""  # day/night
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    incidents_handled: int = 0
    handover_notes: str = ""


@dataclass
class DeviceStatus:
    """设备状态"""
    device_name: str = ""
    device_type: str = ""
    status: str = ""  # online/offline/maintenance
    last_check: Optional[datetime] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class AnomalyRecord:
    """异常记录"""
    anomaly_id: str = ""
    timestamp: Optional[datetime] = None
    source: str = ""
    severity: str = ""  # critical/warning/info
    description: str = ""
    handled: bool = False
    handler: str = ""
    resolution: str = ""


class DailyReportGenerator:
    """
    日巡检报告生成器
    
    生成内容包括：
    - 当日监控数据汇总
    - 告警统计
    - 值班情况
    - 设备状态
    - 异常记录
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        data_sources: Optional[Dict[str, Any]] = None
    ):
        """
        初始化日巡检报告生成器
        
        Args:
            report_generator: 报告生成器实例
            data_sources: 数据源配置
        """
        self._report_generator = report_generator
        self._data_sources = data_sources or {}
    
    def generate(
        self,
        report_date: Optional[datetime] = None,
        duty_person: str = "",
        duty_shift: str = "day",
        monitoring_data: Optional[Dict[str, Any]] = None,
        alert_data: Optional[Dict[str, Any]] = None,
        device_data: Optional[Dict[str, Any]] = None,
        anomaly_records: Optional[List[Dict[str, Any]]] = None,
        custom_content: Optional[Dict[str, Any]] = None,
    ) -> Report:
        """
        生成日巡检报告
        
        Args:
            report_date: 报告日期
            duty_person: 值班人
            duty_shift: 班次 (day/night)
            monitoring_data: 监控数据
            alert_data: 告警数据
            device_data: 设备数据
            anomaly_records: 异常记录
            custom_content: 自定义内容
            
        Returns:
            生成的报告对象
        """
        report_date = report_date or datetime.now()
        period_start = report_date.replace(hour=0, minute=0, second=0)
        period_end = report_date.replace(hour=23, minute=59, second=59)
        
        # 创建报告
        report = self._report_generator.create_report(
            report_type=ReportType.DAILY,
            title=f"日巡检报告 - {report_date.strftime('%Y-%m-%d')}",
            description=f"日常运维巡检报告，值班人：{duty_person}",
            author=duty_person,
            period_start=period_start,
            period_end=period_end,
            tags=['daily', 'inspection', duty_shift],
        )
        
        # 收集数据
        monitoring_summary = self._collect_monitoring_data(monitoring_data)
        alert_stats = self._collect_alert_data(alert_data)
        device_status = self._collect_device_data(device_data)
        anomalies = self._collect_anomaly_records(anomaly_records)
        
        # 构建上下文
        context = {
            'report_date': report_date,
            'duty_person': duty_person,
            'duty_shift': duty_shift,
            'monitoring': monitoring_summary,
            'alerts': alert_stats,
            'devices': device_status,
            'anomalies': anomalies,
            'custom': custom_content or {},
        }
        
        # 生成报告
        return self._report_generator.generate(report, context=context)
    
    def _collect_monitoring_data(
        self,
        data: Optional[Dict[str, Any]]
    ) -> MonitoringSummary:
        """收集监控数据"""
        if not data:
            return MonitoringSummary()
        
        summary = MonitoringSummary()
        
        # 从数据中提取监控指标
        summary.total_hosts = data.get('total_hosts', 0)
        summary.online_hosts = data.get('online_hosts', 0)
        summary.offline_hosts = data.get('offline_hosts', 0)
        summary.total_metrics = data.get('total_metrics', 0)
        summary.abnormal_metrics = data.get('abnormal_metrics', 0)
        summary.cpu_avg_usage = data.get('cpu_avg_usage', 0.0)
        summary.memory_avg_usage = data.get('memory_avg_usage', 0.0)
        summary.disk_avg_usage = data.get('disk_avg_usage', 0.0)
        summary.network_in_avg = data.get('network_in_avg', 0.0)
        summary.network_out_avg = data.get('network_out_avg', 0.0)
        
        return summary
    
    def _collect_alert_data(
        self,
        data: Optional[Dict[str, Any]]
    ) -> AlertStatistics:
        """收集告警数据"""
        if not data:
            return AlertStatistics()
        
        stats = AlertStatistics()
        
        stats.total_count = data.get('total_count', 0)
        stats.critical_count = data.get('critical_count', 0)
        stats.warning_count = data.get('warning_count', 0)
        stats.info_count = data.get('info_count', 0)
        stats.acknowledged_count = data.get('acknowledged_count', 0)
        stats.resolved_count = data.get('resolved_count', 0)
        stats.top_alerts = data.get('top_alerts', [])
        
        return stats
    
    def _collect_device_data(
        self,
        data: Optional[Dict[str, Any]]
    ) -> List[DeviceStatus]:
        """收集设备数据"""
        if not data:
            return []
        
        devices = []
        device_list = data.get('devices', [])
        
        for dev in device_list:
            device = DeviceStatus(
                device_name=dev.get('name', ''),
                device_type=dev.get('type', ''),
                status=dev.get('status', 'unknown'),
                last_check=dev.get('last_check'),
                issues=dev.get('issues', []),
            )
            devices.append(device)
        
        return devices
    
    def _collect_anomaly_records(
        self,
        records: Optional[List[Dict[str, Any]]]
    ) -> List[AnomalyRecord]:
        """收集异常记录"""
        if not records:
            return []
        
        anomalies = []
        
        for rec in records:
            anomaly = AnomalyRecord(
                anomaly_id=rec.get('id', ''),
                timestamp=rec.get('timestamp'),
                source=rec.get('source', ''),
                severity=rec.get('severity', 'info'),
                description=rec.get('description', ''),
                handled=rec.get('handled', False),
                handler=rec.get('handler', ''),
                resolution=rec.get('resolution', ''),
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def generate_html_content(
        self,
        report_date: datetime,
        duty_person: str,
        duty_shift: str,
        monitoring: MonitoringSummary,
        alerts: AlertStatistics,
        devices: List[DeviceStatus],
        anomalies: List[AnomalyRecord],
    ) -> str:
        """生成HTML格式报告内容"""
        html = f"""
<h1>日巡检报告</h1>
<p><strong>日期:</strong> {report_date.strftime('%Y-%m-%d')}</p>
<p><strong>值班人:</strong> {duty_person}</p>
<p><strong>班次:</strong> {'白班' if duty_shift == 'day' else '夜班'}</p>

<h2>一、监控数据汇总</h2>
<table>
    <tr><th>指标</th><th>数值</th></tr>
    <tr><td>主机总数</td><td>{monitoring.total_hosts}</td></tr>
    <tr><td>在线主机</td><td>{monitoring.online_hosts}</td></tr>
    <tr><td>离线主机</td><td>{monitoring.offline_hosts}</td></tr>
    <tr><td>总指标数</td><td>{monitoring.total_metrics}</td></tr>
    <tr><td>异常指标</td><td>{monitoring.abnormal_metrics}</td></tr>
    <tr><td>平均CPU使用率</td><td>{monitoring.cpu_avg_usage:.1f}%</td></tr>
    <tr><td>平均内存使用率</td><td>{monitoring.memory_avg_usage:.1f}%</td></tr>
    <tr><td>平均磁盘使用率</td><td>{monitoring.disk_avg_usage:.1f}%</td></tr>
</table>

<h2>二、告警统计</h2>
<table>
    <tr><th>告警级别</th><th>数量</th></tr>
    <tr><td>总计</td><td>{alerts.total_count}</td></tr>
    <tr><td>严重</td><td>{alerts.critical_count}</td></tr>
    <tr><td>警告</td><td>{alerts.warning_count}</td></tr>
    <tr><td>信息</td><td>{alerts.info_count}</td></tr>
    <tr><td>已确认</td><td>{alerts.acknowledged_count}</td></tr>
    <tr><td>已解决</td><td>{alerts.resolved_count}</td></tr>
</table>
"""
        
        # 添加Top告警
        if alerts.top_alerts:
            html += "<h3>Top 5 告警</h3><table><tr><th>告警名称</th><th>级别</th><th>持续时间</th></tr>"
            for alert in alerts.top_alerts[:5]:
                html += f"<tr><td>{alert.get('name', '')}</td><td>{alert.get('severity', '')}</td><td>{alert.get('duration', '')}</td></tr>"
            html += "</table>"
        
        # 添加设备状态
        html += "<h2>三、设备状态</h2>"
        if devices:
            html += "<table><tr><th>设备名称</th><th>类型</th><th>状态</th><th>问题</th></tr>"
            for dev in devices:
                issues = ', '.join(dev.issues) if dev.issues else '无'
                status_icon = '✓' if dev.status == 'online' else '✗'
                html += f"<tr><td>{dev.device_name}</td><td>{dev.device_type}</td><td>{status_icon} {dev.status}</td><td>{issues}</td></tr>"
            html += "</table>"
        else:
            html += "<p>暂无设备异常</p>"
        
        # 添加异常记录
        html += "<h2>四、异常记录</h2>"
        if anomalies:
            html += "<table><tr><th>时间</th><th>来源</th><th>级别</th><th>描述</th><th>处理状态</th></tr>"
            for anomaly in anomalies:
                handled = '已处理' if anomaly.handled else '未处理'
                html += f"<tr><td>{anomaly.timestamp.strftime('%H:%M') if anomaly.timestamp else ''}</td>"
                html += f"<td>{anomaly.source}</td><td>{anomaly.severity}</td>"
                html += f"<td>{anomaly.description}</td><td>{handled}</td></tr>"
            html += "</table>"
        else:
            html += "<p>当日无异常记录</p>"
        
        # 巡检结论
        html += """
<h2>五、巡检结论</h2>
<div class="summary">
"""
        
        if monitoring.offline_hosts > 0:
            html += f'<div class="alert warning">注意：{monitoring.offline_hosts}台主机离线</div>'
        
        if alerts.critical_count > 0:
            html += f'<div class="alert alert">警告：存在{alerts.critical_count}条严重告警</div>'
        
        if monitoring.cpu_avg_usage > 80:
            html += f'<div class="alert warning">注意：CPU平均使用率过高 ({monitoring.cpu_avg_usage:.1f}%)</div>'
        
        if len(anomalies) > 0:
            unhandled = sum(1 for a in anomalies if not a.handled)
            if unhandled > 0:
                html += f'<div class="alert">有{unhandled}条异常待处理</div>'
        
        html += "<p>整体运行状况：正常</p>"
        html += "</div>"
        
        return html
    
    def get_template_variables(self) -> Dict[str, str]:
        """获取模板变量说明"""
        return {
            'report_date': '报告日期',
            'duty_person': '值班人员',
            'duty_shift': '值班班次 (day/night)',
            'monitoring.total_hosts': '主机总数',
            'monitoring.online_hosts': '在线主机数',
            'monitoring.offline_hosts': '离线主机数',
            'monitoring.cpu_avg_usage': '平均CPU使用率(%)',
            'monitoring.memory_avg_usage': '平均内存使用率(%)',
            'monitoring.disk_avg_usage': '平均磁盘使用率(%)',
            'alerts.total_count': '告警总数',
            'alerts.critical_count': '严重告警数',
            'alerts.warning_count': '警告告警数',
            'alerts.resolved_count': '已解决告警数',
            'devices': '设备列表',
            'anomalies': '异常记录列表',
        }
