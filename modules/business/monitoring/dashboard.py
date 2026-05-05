"""
仪表盘数据模块
BM-01 监控告警
提供实时数据聚合、TopN统计、可用性统计、趋势图表数据等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from .monitor import MetricPoint, DeviceStatus, AlertSeverity
from .rules import AlertEvent, AlertState

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: datetime
    value: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'count': self.count
        }


@dataclass
class AggregationResult:
    """聚合结果"""
    metric_name: str
    device_id: str
    aggregation_type: str  # 'avg', 'sum', 'min', 'max', 'count'
    
    # 时间范围
    start_time: datetime
    end_time: datetime
    
    # 统计值
    value: float
    count: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    std_dev: Optional[float] = None
    
    # 百分位数
    p50: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_name': self.metric_name,
            'device_id': self.device_id,
            'aggregation_type': self.aggregation_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'value': self.value,
            'count': self.count,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'std_dev': self.std_dev,
            'p50': self.p50,
            'p90': self.p90,
            'p95': self.p95,
            'p99': self.p99
        }


@dataclass
class TopNItem:
    """TopN统计项"""
    rank: int
    device_id: str
    metric_name: str
    value: float
    unit: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rank': self.rank,
            'device_id': self.device_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'unit': self.unit
        }


@dataclass
class AvailabilityReport:
    """可用性报告"""
    device_id: str
    start_time: datetime
    end_time: datetime
    
    # 可用性指标
    uptime_seconds: int
    downtime_seconds: int
    availability_percent: float
    
    # 告警统计
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    
    # MTBF/MTTR
    mtbf_hours: Optional[float] = None  # 平均故障间隔时间
    mttr_minutes: Optional[float] = None  # 平均恢复时间
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'downtime_seconds': self.downtime_seconds,
            'availability_percent': self.availability_percent,
            'total_alerts': self.total_alerts,
            'critical_alerts': self.critical_alerts,
            'warning_alerts': self.warning_alerts,
            'mtbf_hours': self.mtbf_hours,
            'mttr_minutes': self.mttr_minutes
        }


@dataclass
class DashboardSummary:
    """仪表盘摘要"""
    total_devices: int
    online_devices: int
    offline_devices: int
    
    total_alerts: int
    active_alerts: int
    critical_alerts: int
    resolved_alerts: int
    
    alerts_trend: List[int]  # 过去N小时的告警数量
    
    top_severity_distribution: Dict[str, int]
    top_rule_alerts: List[Dict[str, Any]]
    top_device_alerts: List[Dict[str, Any]]
    
    availability_summary: Dict[str, float]  # 整体可用性统计
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_devices': self.total_devices,
            'online_devices': self.online_devices,
            'offline_devices': self.offline_devices,
            'total_alerts': self.total_alerts,
            'active_alerts': self.active_alerts,
            'critical_alerts': self.critical_alerts,
            'resolved_alerts': self.resolved_alerts,
            'alerts_trend': self.alerts_trend,
            'top_severity_distribution': self.top_severity_distribution,
            'top_rule_alerts': self.top_rule_alerts,
            'top_device_alerts': self.top_device_alerts,
            'availability_summary': self.availability_summary
        }


class DashboardData:
    """
    仪表盘数据服务
    负责实时数据聚合、TopN统计、可用性统计、趋势图表数据
    """
    
    def __init__(
        self,
        monitor_core=None,
        alert_engine=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化仪表盘数据服务
        
        Args:
            monitor_core: 监控核心实例
            alert_engine: 告警引擎实例
            config: 配置字典
        """
        self.config = config or {}
        self._monitor_core = monitor_core
        self._alert_engine = alert_engine
        
        # 告警历史（用于统计）
        self._alert_history: List[AlertEvent] = []
        self._max_history_size = self.config.get('max_history_size', 10000)
        
        logger.info('DashboardData initialized')
    
    def set_monitor_core(self, monitor_core) -> None:
        """设置监控核心"""
        self._monitor_core = monitor_core
    
    def set_alert_engine(self, alert_engine) -> None:
        """设置告警引擎"""
        self._alert_engine = alert_engine
    
    def add_alert_history(self, alert: AlertEvent) -> None:
        """添加告警历史"""
        self._alert_history.append(alert)
        
        # 限制历史大小
        if len(self._alert_history) > self._max_history_size:
            self._alert_history = self._alert_history[-self._max_history_size:]
    
    def get_realtime_metrics(
        self,
        device_id: Optional[str] = None,
        metric_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, List[TimeSeriesPoint]]:
        """
        获取实时指标数据
        
        Args:
            device_id: 设备ID（None表示所有设备）
            metric_names: 指标名称列表（None表示所有指标）
            limit: 返回条数限制
            
        Returns:
            指标名称 -> 时间序列数据
        """
        result = {}
        
        if not self._monitor_core:
            return result
        
        # 获取设备状态
        device_status = self._monitor_core.get_all_device_status()
        devices = [device_id] if device_id else device_status.keys()
        
        for dev in devices:
            if metric_names:
                metrics = metric_names
            else:
                # 获取该设备的所有指标
                metrics = set()
                buffer = self._monitor_core._metric_buffer
                for key in buffer:
                    if key.startswith(f"{dev}:"):
                        metric_name = key.split(':', 1)[1]
                        metrics.add(metric_name)
            
            for metric_name in metrics:
                points = self._monitor_core.get_metrics(dev, metric_name)
                if points:
                    points = points[-limit:]
                    result[f"{dev}:{metric_name}"] = [
                        TimeSeriesPoint(
                            timestamp=p.timestamp,
                            value=p.value
                        )
                        for p in points
                    ]
        
        return result
    
    def aggregate_metrics(
        self,
        device_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        interval_seconds: int = 60
    ) -> List[TimeSeriesPoint]:
        """
        聚合指标数据（按时间间隔）
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            start_time: 开始时间
            end_time: 结束时间
            interval_seconds: 间隔秒数
            
        Returns:
            聚合后的时间序列数据
        """
        if not self._monitor_core:
            return []
        
        # 获取原始数据
        raw_points = self._monitor_core.get_metrics(
            device_id, metric_name, start_time, end_time
        )
        
        if not raw_points:
            return []
        
        # 按时间间隔分组
        interval = timedelta(seconds=interval_seconds)
        buckets: Dict[datetime, List[float]] = defaultdict(list)
        
        for point in raw_points:
            # 计算桶的时间（对齐到interval）
            bucket_time = datetime(
                point.timestamp.year,
                point.timestamp.month,
                point.timestamp.day,
                point.timestamp.hour,
                point.timestamp.minute // (interval_seconds // 60) * (interval_seconds // 60)
            )
            buckets[bucket_time].append(point.value)
        
        # 计算每个桶的聚合值
        result = []
        for bucket_time in sorted(buckets.keys()):
            values = buckets[bucket_time]
            result.append(TimeSeriesPoint(
                timestamp=bucket_time,
                value=statistics.mean(values),
                min_value=min(values),
                max_value=max(values),
                count=len(values)
            ))
        
        return result
    
    def get_statistics(
        self,
        device_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[AggregationResult]:
        """
        获取指标统计信息
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            聚合结果
        """
        if not self._monitor_core:
            return None
        
        raw_points = self._monitor_core.get_metrics(
            device_id, metric_name, start_time, end_time
        )
        
        if not raw_points:
            return None
        
        values = [p.value for p in raw_points]
        
        result = AggregationResult(
            metric_name=metric_name,
            device_id=device_id,
            aggregation_type='statistics',
            start_time=start_time,
            end_time=end_time,
            value=statistics.mean(values),
            count=len(values),
            min_value=min(values),
            max_value=max(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else None
        )
        
        # 计算百分位数
        if len(values) > 1:
            sorted_values = sorted(values)
            n = len(sorted_values)
            result.p50 = sorted_values[int(n * 0.5)]
            result.p90 = sorted_values[int(n * 0.9)]
            result.p95 = sorted_values[int(n * 0.95)]
            result.p99 = sorted_values[int(n * 0.99)]
        
        return result
    
    def get_topn_metrics(
        self,
        metric_name: str,
        n: int = 10,
        order: str = 'desc',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TopNItem]:
        """
        获取TopN指标
        
        Args:
            metric_name: 指标名称
            n: 前N个
            order: 排序方式 'desc' 或 'asc'
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            TopN列表
        """
        if not self._monitor_core:
            return []
        
        # 收集所有设备的最新值
        device_values: Dict[str, float] = {}
        buffer = self._monitor_core._metric_buffer
        
        for key, points in buffer.items():
            if key.endswith(f":{metric_name}"):
                if points:
                    device_id = key.split(':')[0]
                    # 使用最新值
                    device_values[device_id] = points[-1].value
        
        if not device_values:
            return []
        
        # 排序
        sorted_items = sorted(
            device_values.items(),
            key=lambda x: x[1],
            reverse=(order == 'desc')
        )
        
        # 取前N个
        result = []
        unit = ''
        
        for i, (device_id, value) in enumerate(sorted_items[:n]):
            # 获取单位
            points = self._monitor_core._metric_buffer.get(f"{device_id}:{metric_name}", [])
            if points:
                unit = points[0].unit
            
            result.append(TopNItem(
                rank=i + 1,
                device_id=device_id,
                metric_name=metric_name,
                value=value,
                unit=unit
            ))
        
        return result
    
    def get_topn_alerts(
        self,
        n: int = 10,
        group_by: str = 'rule'
    ) -> List[Dict[str, Any]]:
        """
        获取TopN告警统计
        
        Args:
            n: 前N个
            group_by: 分组方式 'rule', 'device', 'severity'
            
        Returns:
            TopN告警列表
        """
        # 使用告警历史
        history = self._alert_history
        
        if group_by == 'rule':
            # 按规则分组
            rule_counts: Dict[str, int] = defaultdict(int)
            for alert in history:
                rule_counts[alert.rule_id] += 1
            
            sorted_rules = sorted(
                rule_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            result = []
            for i, (rule_id, count) in enumerate(sorted_rules[:n]):
                result.append({
                    'rank': i + 1,
                    'rule_id': rule_id,
                    'count': count
                })
            return result
        
        elif group_by == 'device':
            # 按设备分组
            device_counts: Dict[str, int] = defaultdict(int)
            for alert in history:
                device_counts[alert.device_id] += 1
            
            sorted_devices = sorted(
                device_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            result = []
            for i, (device_id, count) in enumerate(sorted_devices[:n]):
                result.append({
                    'rank': i + 1,
                    'device_id': device_id,
                    'count': count
                })
            return result
        
        return []
    
    def get_availability(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> AvailabilityReport:
        """
        计算设备可用性
        
        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            可用性报告
        """
        total_seconds = int((end_time - start_time).total_seconds())
        
        # 获取该设备相关的告警
        device_alerts = [
            a for a in self._alert_history
            if a.device_id == device_id and a.fired_at <= end_time
        ]
        
        # 计算告警统计
        critical_alerts = [a for a in device_alerts if a.severity == AlertSeverity.CRITICAL]
        warning_alerts = [a for a in device_alerts if a.severity == AlertSeverity.WARNING]
        
        # 计算停机时间（简化计算：假设每个critical告警影响5分钟）
        downtime_seconds = len(critical_alerts) * 300  # 5分钟
        uptime_seconds = max(0, total_seconds - downtime_seconds)
        
        availability_percent = (uptime_seconds / total_seconds * 100) if total_seconds > 0 else 100
        
        # 计算MTTR（简化：平均恢复时间）
        mttr_minutes = None
        if critical_alerts:
            total_recovery_time = sum(
                (a.resolved_at - a.fired_at).total_seconds()
                for a in critical_alerts
                if a.resolved_at
            )
            mttr_minutes = total_recovery_time / len(critical_alerts) / 60 if critical_alerts else None
        
        # 计算MTBF
        mtbf_hours = None
        if len(critical_alerts) > 1:
            total_uptime = uptime_seconds
            mtbf_hours = total_uptime / (len(critical_alerts) - 1) / 3600
        
        return AvailabilityReport(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            uptime_seconds=uptime_seconds,
            downtime_seconds=downtime_seconds,
            availability_percent=round(availability_percent, 2),
            total_alerts=len(device_alerts),
            critical_alerts=len(critical_alerts),
            warning_alerts=len(warning_alerts),
            mtbf_hours=round(mtbf_hours, 2) if mtbf_hours else None,
            mttr_minutes=round(mttr_minutes, 2) if mttr_minutes else None
        )
    
    def get_alerts_trend(
        self,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        获取告警趋势
        
        Args:
            hours: 过去多少小时
            interval_minutes: 间隔分钟数
            
        Returns:
            趋势数据列表
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 按时间间隔分组
        interval = timedelta(minutes=interval_minutes)
        buckets: Dict[datetime, Dict[str, int]] = defaultdict(
            lambda: {'total': 0, 'critical': 0, 'warning': 0, 'info': 0}
        )
        
        for alert in self._alert_history:
            if alert.fired_at < start_time or alert.fired_at > end_time:
                continue
            
            bucket_time = datetime(
                alert.fired_at.year,
                alert.fired_at.month,
                alert.fired_at.day,
                alert.fired_at.hour,
                (alert.fired_at.minute // interval_minutes) * interval_minutes
            )
            
            buckets[bucket_time]['total'] += 1
            
            if alert.severity == AlertSeverity.CRITICAL:
                buckets[bucket_time]['critical'] += 1
            elif alert.severity == AlertSeverity.WARNING:
                buckets[bucket_time]['warning'] += 1
            elif alert.severity == AlertSeverity.INFO:
                buckets[bucket_time]['info'] += 1
        
        result = []
        for bucket_time in sorted(buckets.keys()):
            data = buckets[bucket_time]
            result.append({
                'timestamp': bucket_time.isoformat(),
                'total': data['total'],
                'critical': data['critical'],
                'warning': data['warning'],
                'info': data['info']
            })
        
        return result
    
    def get_severity_distribution(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        获取告警严重级别分布
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            严重级别 -> 数量
        """
        distribution: Dict[str, int] = {
            'critical': 0,
            'error': 0,
            'warning': 0,
            'info': 0
        }
        
        for alert in self._alert_history:
            if start_time and alert.fired_at < start_time:
                continue
            if end_time and alert.fired_at > end_time:
                continue
            
            severity = alert.severity.value
            if severity in distribution:
                distribution[severity] += 1
        
        return distribution
    
    def get_dashboard_summary(self) -> DashboardSummary:
        """
        获取仪表盘摘要
        
        Returns:
            仪表盘摘要
        """
        # 设备统计
        total_devices = 0
        online_devices = 0
        offline_devices = 0
        
        if self._monitor_core:
            device_status = self._monitor_core.get_all_device_status()
            total_devices = len(device_status)
            online_devices = sum(
                1 for s in device_status.values()
                if s != DeviceStatus.OFFLINE
            )
            offline_devices = sum(
                1 for s in device_status.values()
                if s == DeviceStatus.OFFLINE
            )
        
        # 告警统计
        history = self._alert_history
        active_alerts = [a for a in history if a.state == AlertState.FIRING]
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        resolved_alerts = [a for a in history if a.state == AlertState.RESOLVED]
        
        # 告警趋势（过去24小时，每小时）
        alerts_trend = [0] * 24
        now = datetime.now()
        for i in range(24):
            hour_start = now - timedelta(hours=24-i)
            hour_end = hour_start + timedelta(hours=1)
            count = sum(
                1 for a in history
                if hour_start <= a.fired_at < hour_end
            )
            alerts_trend[i] = count
        
        # 严重级别分布
        severity_dist = self.get_severity_distribution()
        
        # Top规则告警
        top_rule_alerts = self.get_topn_alerts(n=5, group_by='rule')
        
        # Top设备告警
        top_device_alerts = self.get_topn_alerts(n=5, group_by='device')
        
        # 可用性摘要
        availability_summary: Dict[str, float] = {}
        if self._monitor_core:
            for device_id in list(self._monitor_core.get_all_device_status().keys())[:10]:
                report = self.get_availability(
                    device_id,
                    datetime.now() - timedelta(days=1),
                    datetime.now()
                )
                availability_summary[device_id] = report.availability_percent
        
        return DashboardSummary(
            total_devices=total_devices,
            online_devices=online_devices,
            offline_devices=offline_devices,
            total_alerts=len(history),
            active_alerts=len(active_alerts),
            critical_alerts=len(critical_alerts),
            resolved_alerts=len(resolved_alerts),
            alerts_trend=alerts_trend,
            top_severity_distribution=severity_dist,
            top_rule_alerts=top_rule_alerts,
            top_device_alerts=top_device_alerts,
            availability_summary=availability_summary
        )
    
    def get_chart_data(
        self,
        device_id: str,
        metric_name: str,
        chart_type: str = 'line',
        hours: int = 24,
        interval_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取图表数据
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            chart_type: 图表类型 'line', 'area', 'bar'
            hours: 过去多少小时
            interval_minutes: 间隔分钟数
            
        Returns:
            图表数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 获取聚合数据
        points = self.aggregate_metrics(
            device_id, metric_name, start_time, end_time, interval_minutes * 60
        )
        
        # 获取统计信息
        stats = self.get_statistics(device_id, metric_name, start_time, end_time)
        
        return {
            'chart_type': chart_type,
            'metric_name': metric_name,
            'device_id': device_id,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'data_points': [p.to_dict() for p in points],
            'statistics': stats.to_dict() if stats else None,
            'labels': {
                'x': '时间',
                'y': metric_name
            }
        }
    
    def get_multi_series_chart(
        self,
        devices: List[str],
        metric_name: str,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取多系列图表数据
        
        Args:
            devices: 设备ID列表
            metric_name: 指标名称
            hours: 过去多少小时
            interval_minutes: 间隔分钟数
            
        Returns:
            多系列图表数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        series = []
        for device_id in devices:
            points = self.aggregate_metrics(
                device_id, metric_name, start_time, end_time, interval_minutes * 60
            )
            series.append({
                'device_id': device_id,
                'data_points': [p.to_dict() for p in points]
            })
        
        return {
            'metric_name': metric_name,
            'series': series,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'labels': {
                'x': '时间',
                'y': metric_name
            }
        }