"""
监控核心模块
BM-01 监控告警
提供指标采集调度、阈值检查、趋势分析、设备状态管理、告警触发等功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """设备状态枚举"""
    NORMAL = 'normal'
    WARNING = 'warning'
    CRITICAL = 'critical'
    OFFLINE = 'offline'
    MAINTENANCE = 'maintenance'
    UNKNOWN = 'unknown'


class AlertSeverity(Enum):
    """告警级别枚举"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@dataclass
class MetricPoint:
    """指标数据点"""
    device_id: str
    metric_name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'unit': self.unit
        }


@dataclass
class ThresholdCheckResult:
    """阈值检查结果"""
    metric_point: MetricPoint
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    is_triggered: bool
    threshold_value: float
    operator: str
    message: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_point': self.metric_point.to_dict(),
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'is_triggered': self.is_triggered,
            'threshold_value': self.threshold_value,
            'operator': self.operator,
            'message': self.message
        }


@dataclass
class TrendAnalysisResult:
    """趋势分析结果"""
    metric_name: str
    device_id: str
    trend: str  # 'up', 'down', 'stable'
    change_rate: float  # 变化率百分比
    avg_value: float
    current_value: float
    prediction: Optional[float] = None  # 预测值
    confidence: float = 0.0  # 置信度
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_name': self.metric_name,
            'device_id': self.device_id,
            'trend': self.trend,
            'change_rate': self.change_rate,
            'avg_value': self.avg_value,
            'current_value': self.current_value,
            'prediction': self.prediction,
            'confidence': self.confidence
        }


class MonitorCore:
    """
    监控核心类
    负责指标采集调度、阈值检查、趋势分析、设备状态管理、告警触发
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化监控核心
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 指标数据缓存
        self._metric_buffer: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._metric_buffer_size = self.config.get('metric_buffer_size', 1000)
        
        # 设备状态管理
        self._device_status: Dict[str, DeviceStatus] = {}
        self._device_last_seen: Dict[str, datetime] = {}
        
        # 阈值规则（由AlertRulesEngine提供）
        self._threshold_rules: Dict[str, Dict[str, Any]] = {}
        
        # 告警回调
        self._alert_callbacks: List[Callable] = []
        
        # 调度间隔配置
        self._collect_interval = self.config.get('collect_interval', 60)  # 秒
        self._check_interval = self.config.get('check_interval', 30)  # 秒
        self._trend_window = self.config.get('trend_window', 300)  # 趋势分析时间窗口（秒）
        
        # 设备离线判定时间（秒）
        self._offline_threshold = self.config.get('offline_threshold', 300)
        
        logger.info('MonitorCore initialized')
    
    def register_threshold_rules(self, rules: Dict[str, Dict[str, Any]]) -> None:
        """注册阈值规则"""
        self._threshold_rules = rules
        logger.info(f'Registered {len(rules)} threshold rules')
    
    def register_alert_callback(self, callback: Callable) -> None:
        """注册告警回调函数"""
        self._alert_callbacks.append(callback)
    
    def add_metric(self, metric: MetricPoint) -> None:
        """
        添加指标数据
        
        Args:
            metric: 指标数据点
        """
        key = f"{metric.device_id}:{metric.metric_name}"
        self._metric_buffer[key].append(metric)
        
        # 限制缓冲区大小
        if len(self._metric_buffer[key]) > self._metric_buffer_size:
            self._metric_buffer[key] = self._metric_buffer[key][-self._metric_buffer_size:]
        
        # 更新设备最后活跃时间
        self._device_last_seen[metric.device_id] = datetime.now()
        
        # 更新设备状态
        self._update_device_status(metric.device_id, DeviceStatus.NORMAL)
    
    def add_metrics(self, metrics: List[MetricPoint]) -> None:
        """批量添加指标数据"""
        for metric in metrics:
            self.add_metric(metric)
    
    def get_metrics(
        self,
        device_id: str,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricPoint]:
        """
        获取指标数据
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指标数据列表
        """
        key = f"{device_id}:{metric_name}"
        metrics = self._metric_buffer.get(key, [])
        
        if start_time or end_time:
            filtered = []
            for m in metrics:
                if start_time and m.timestamp < start_time:
                    continue
                if end_time and m.timestamp > end_time:
                    continue
                filtered.append(m)
            return filtered
        return metrics
    
    def check_threshold(
        self,
        metric: MetricPoint,
        rules: Optional[Dict[str, Any]] = None
    ) -> List[ThresholdCheckResult]:
        """
        检查指标是否触发阈值
        
        Args:
            metric: 指标数据点
            rules: 使用的规则（如果为None则使用注册的规则）
            
        Returns:
            阈值检查结果列表
        """
        results = []
        rules_to_check = rules or self._threshold_rules
        
        # 根据指标名称查找匹配的规则
        matching_rules = {
            rule_id: rule for rule_id, rule in rules_to_check.items()
            if rule.get('metric_name') == metric.metric_name
        }
        
        for rule_id, rule in matching_rules.items():
            # 检查设备ID是否匹配
            target_devices = rule.get('devices', ['*'])
            if '*' not in target_devices and metric.device_id not in target_devices:
                continue
            
            # 获取阈值配置
            thresholds = rule.get('thresholds', [])
            for threshold in thresholds:
                severity = AlertSeverity(threshold.get('severity', 'warning'))
                operator = threshold.get('operator', '>')
                threshold_value = threshold.get('value', 0)
                
                is_triggered = self._evaluate_threshold(
                    metric.value, operator, threshold_value
                )
                
                result = ThresholdCheckResult(
                    metric_point=metric,
                    rule_id=rule_id,
                    rule_name=rule.get('name', rule_id),
                    severity=severity,
                    is_triggered=is_triggered,
                    threshold_value=threshold_value,
                    operator=operator,
                    message=self._generate_threshold_message(
                        metric, rule, threshold, is_triggered
                    )
                )
                results.append(result)
        
        return results
    
    def _evaluate_threshold(
        self,
        value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """
        评估阈值条件
        
        Args:
            value: 当前值
            operator: 操作符
            threshold: 阈值
            
        Returns:
            是否触发阈值
        """
        operators = {
            '>': lambda v, t: v > t,
            '>=': lambda v, t: v >= t,
            '<': lambda v, t: v < t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: v == t,
            '!=': lambda v, t: v != t,
            'range': lambda v, t: t[0] <= v <= t[1],
        }
        
        op_func = operators.get(operator)
        if not op_func:
            logger.warning(f'Unknown operator: {operator}')
            return False
        
        try:
            return op_func(value, threshold)
        except Exception as e:
            logger.error(f'Error evaluating threshold: {e}')
            return False
    
    def _generate_threshold_message(
        self,
        metric: MetricPoint,
        rule: Dict[str, Any],
        threshold: Dict[str, Any],
        is_triggered: bool
    ) -> str:
        """生成阈值告警消息"""
        severity = threshold.get('severity', 'warning')
        operator = threshold.get('operator', '>')
        threshold_value = threshold.get('value', 0)
        
        if is_triggered:
            return (
                f"[{severity.upper()}] {rule.get('name', 'Unknown Rule')} - "
                f"设备 {metric.device_id} 的指标 {metric.metric_name} "
                f"当前值 {metric.value}{metric.unit} "
                f"触发了阈值条件 {operator} {threshold_value}{metric.unit}"
            )
        return ''
    
    def analyze_trend(
        self,
        device_id: str,
        metric_name: str,
        window_seconds: Optional[int] = None
    ) -> Optional[TrendAnalysisResult]:
        """
        分析指标趋势
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            window_seconds: 分析时间窗口（秒）
            
        Returns:
            趋势分析结果
        """
        window = window_seconds or self._trend_window
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=window)
        
        metrics = self.get_metrics(device_id, metric_name, start_time, end_time)
        
        if len(metrics) < 2:
            return None
        
        values = [m.value for m in metrics]
        current_value = values[-1]
        avg_value = sum(values) / len(values)
        
        # 计算变化率
        first_value = values[0]
        if first_value != 0:
            change_rate = ((current_value - first_value) / first_value) * 100
        else:
            change_rate = 0.0
        
        # 判断趋势
        if abs(change_rate) < 5:  # 5%以内视为稳定
            trend = 'stable'
        elif change_rate > 0:
            trend = 'up'
        else:
            trend = 'down'
        
        # 简单线性预测
        if len(values) >= 3:
            # 使用简单线性回归
            n = len(values)
            x = list(range(n))
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
            intercept = (sum_y - slope * sum_x) / n
            
            # 预测下一个值
            prediction = slope * n + intercept
            
            # 计算置信度（基于拟合度）
            y_mean = sum_y / n
            ss_tot = sum((yi - y_mean) ** 2 for yi in values)
            ss_res = sum((values[i] - (slope * i + intercept)) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            confidence = max(0, min(1, r_squared))
        else:
            prediction = None
            confidence = 0.0
        
        return TrendAnalysisResult(
            metric_name=metric_name,
            device_id=device_id,
            trend=trend,
            change_rate=change_rate,
            avg_value=avg_value,
            current_value=current_value,
            prediction=prediction,
            confidence=confidence
        )
    
    def _update_device_status(self, device_id: str, status: DeviceStatus) -> None:
        """更新设备状态"""
        current_status = self._device_status.get(device_id)
        
        # 状态升级规则: normal -> warning -> critical
        if current_status == DeviceStatus.CRITICAL:
            # critical状态只能降级到warning或normal
            if status == DeviceStatus.NORMAL:
                self._device_status[device_id] = status
        elif current_status == DeviceStatus.WARNING:
            # warning可以升级到critical，可以降级到normal
            if status == DeviceStatus.CRITICAL:
                self._device_status[device_id] = status
            elif status == DeviceStatus.NORMAL:
                self._device_status[device_id] = status
        else:
            self._device_status[device_id] = status
        
        logger.debug(f'Device {device_id} status updated to {status.value}')
    
    def check_device_offline(self) -> List[str]:
        """
        检查离线设备
        
        Returns:
            离线设备ID列表
        """
        now = datetime.now()
        offline_devices = []
        
        for device_id, last_seen in self._device_last_seen.items():
            if (now - last_seen).total_seconds() > self._offline_threshold:
                if self._device_status.get(device_id) != DeviceStatus.OFFLINE:
                    self._device_status[device_id] = DeviceStatus.OFFLINE
                    offline_devices.append(device_id)
                    logger.warning(f'Device {device_id} is offline')
        
        return offline_devices
    
    def get_device_status(self, device_id: str) -> DeviceStatus:
        """获取设备状态"""
        return self._device_status.get(device_id, DeviceStatus.UNKNOWN)
    
    def get_all_device_status(self) -> Dict[str, DeviceStatus]:
        """获取所有设备状态"""
        return dict(self._device_status)
    
    async def start(self) -> None:
        """启动监控核心"""
        if self._running:
            logger.warning('MonitorCore is already running')
            return
        
        self._running = True
        logger.info('MonitorCore started')
        
        # 启动定时任务
        self._tasks.append(asyncio.create_task(self._offline_check_task()))
    
    async def stop(self) -> None:
        """停止监控核心"""
        self._running = False
        
        # 取消所有任务
        for task in self._tasks:
            task.cancel()
        
        self._tasks.clear()
        logger.info('MonitorCore stopped')
    
    async def _offline_check_task(self) -> None:
        """离线检查定时任务"""
        while self._running:
            try:
                self.check_device_offline()
            except Exception as e:
                logger.error(f'Error in offline check task: {e}')
            
            await asyncio.sleep(self._check_interval)
    
    def clear_metric_buffer(self, device_id: Optional[str] = None, 
                           metric_name: Optional[str] = None) -> None:
        """
        清除指标缓冲区
        
        Args:
            device_id: 设备ID（None表示所有设备）
            metric_name: 指标名称（None表示所有指标）
        """
        if device_id and metric_name:
            key = f"{device_id}:{metric_name}"
            self._metric_buffer.pop(key, None)
        elif device_id:
            keys_to_remove = [k for k in self._metric_buffer if k.startswith(f"{device_id}:")]
            for key in keys_to_remove:
                del self._metric_buffer[key]
        else:
            self._metric_buffer.clear()
        
        logger.debug(f'Cleared metric buffer: device={device_id}, metric={metric_name}')
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        return {
            'buffer_size': sum(len(v) for v in self._metric_buffer.values()),
            'device_count': len(self._device_status),
            'device_status': {k: v.value for k, v in self._device_status.items()},
            'registered_rules': len(self._threshold_rules),
            'is_running': self._running
        }
