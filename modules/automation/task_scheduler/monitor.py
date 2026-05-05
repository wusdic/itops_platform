"""任务监控 - 执行状态监控、性能指标、失败告警"""
import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

from .task import Task, TaskStatus, TaskExecution

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """监控指标"""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    
    success_rate: float = 0.0
    failure_rate: float = 0.0
    
    total_execution_time: float = 0.0
    
    tasks_by_priority: Dict[str, int] = field(default_factory=dict)
    tasks_by_type: Dict[str, int] = field(default_factory=dict)
    
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'running_tasks': self.running_tasks,
            'pending_tasks': self.pending_tasks,
            'avg_duration': self.avg_duration,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'success_rate': self.success_rate,
            'failure_rate': self.failure_rate,
            'total_execution_time': self.total_execution_time,
            'tasks_by_priority': self.tasks_by_priority,
            'tasks_by_type': self.tasks_by_type,
            'recent_failures': list(self.recent_failures),
        }


@dataclass
class Alert:
    """告警"""
    alert_id: str
    level: str  # critical, warning, info
    title: str
    message: str
    task_id: Optional[str] = None
    execution_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class TaskMonitor:
    """
    任务监控器
    支持功能:
    - 执行状态监控
    - 性能指标
    - 失败告警
    """
    
    def __init__(
        self,
        alert_threshold: Optional[Dict[str, Any]] = None,
        metrics_retention: int = 3600,
    ):
        """
        初始化监控器
        
        Args:
            alert_threshold: 告警阈值配置
            metrics_retention: 指标保留时间（秒）
        """
        self.alert_threshold = alert_threshold or {
            'failure_rate': 0.1,      # 失败率超过10%
            'consecutive_failures': 3, # 连续失败3次
            'task_timeout': 300,      # 任务超时5分钟
            'queue_size': 1000,       # 队列大小
        }
        self.metrics_retention = metrics_retention
        
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._performance = PerformanceMetrics()
        self._alerts: Dict[str, Alert] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 回调
        self._on_alert: List[Callable] = []
        self._on_metrics_update: List[Callable] = []
        
        # 历史数据
        self._execution_history: deque = deque(maxlen=10000)
        self._duration_history: deque = deque(maxlen=1000)
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self._on_alert.append(callback)
    
    def on_metrics_update(self, callback: Callable):
        """注册指标更新回调"""
        self._on_metrics_update.append(callback)
    
    async def start(self):
        """启动监控"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Task monitor started")
    
    async def stop(self):
        """停止监控"""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task monitor stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检查告警条件
                await self._check_alerts()
                
                # 清理过期指标
                self._cleanup_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            await asyncio.sleep(10)  # 每10秒检查一次
    
    def record_task_start(self, task: Task, execution: TaskExecution):
        """记录任务开始"""
        self._performance.total_tasks += 1
        self._performance.running_tasks += 1
        self._performance.pending_tasks -= 1
        
        # 按类型统计
        task_type = task.__class__.__name__
        self._performance.tasks_by_type[task_type] = \
            self._performance.tasks_by_type.get(task_type, 0) + 1
        
        # 按优先级统计
        priority = task.priority.name
        self._performance.tasks_by_priority[priority] = \
            self._performance.tasks_by_priority.get(priority, 0) + 1
        
        self._record_metric('task_started_total', MetricType.COUNTER, 1, {
            'task_type': task_type,
            'priority': priority,
        })
    
    def record_task_complete(self, task: Task, execution: TaskExecution):
        """记录任务完成"""
        self._performance.running_tasks -= 1
        self._execution_history.append(execution)
        
        if execution.result:
            duration = execution.result.duration or 0
            self._duration_history.append(duration)
            
            # 更新性能指标
            self._update_performance_metrics(duration)
            
            if execution.result.success:
                self._performance.completed_tasks += 1
                self._record_metric('task_completed_total', MetricType.COUNTER, 1, {
                    'task_type': task.__class__.__name__,
                    'status': 'success',
                })
            else:
                self._performance.failed_tasks += 1
                self._performance.recent_failures.append({
                    'task_id': task.task_id,
                    'task_name': task.name,
                    'error': execution.result.error,
                    'timestamp': datetime.now().isoformat(),
                })
                self._record_metric('task_failed_total', MetricType.COUNTER, 1, {
                    'task_type': task.__class__.__name__,
                    'error_type': str(type(execution.result.error)),
                })
                
                # 检查是否需要告警
                self._check_failure_alert(task, execution)
    
    def record_task_timeout(self, task: Task, execution: TaskExecution):
        """记录任务超时"""
        self._performance.running_tasks -= 1
        self._performance.failed_tasks += 1
        
        self._performance.recent_failures.append({
            'task_id': task.task_id,
            'task_name': task.name,
            'error': 'Task timeout',
            'timestamp': datetime.now().isoformat(),
        })
        
        self._record_metric('task_timeout_total', MetricType.COUNTER, 1, {
            'task_type': task.__class__.__name__,
        })
        
        # 触发超时告警
        self._trigger_alert(
            level='warning',
            title=f"Task timeout: {task.name}",
            message=f"Task {task.name} (ID: {task.task_id}) timed out after {task.timeout} seconds",
            task_id=task.task_id,
            execution_id=execution.execution_id,
        )
    
    def _update_performance_metrics(self, duration: float):
        """更新性能指标"""
        durations = list(self._duration_history)
        
        if durations:
            self._performance.avg_duration = sum(durations) / len(durations)
            self._performance.min_duration = min(durations)
            self._performance.max_duration = max(durations)
        
        # 计算成功率
        total = self._performance.completed_tasks + self._performance.failed_tasks
        if total > 0:
            self._performance.success_rate = self._performance.completed_tasks / total
            self._performance.failure_rate = self._performance.failed_tasks / total
        
        self._performance.total_execution_time = sum(durations)
    
    def _record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """记录指标"""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
        )
        
        self._metrics[name].append(metric)
        
        # 触发回调
        for callback in self._on_metrics_update:
            try:
                callback(name, metric)
            except Exception as e:
                logger.error(f"Error in metrics update callback: {e}")
    
    def _check_alerts(self):
        """检查告警条件"""
        # 检查失败率
        failure_rate = self._performance.failure_rate
        threshold = self.alert_threshold.get('failure_rate', 0.1)
        
        if failure_rate > threshold and self._performance.total_tasks > 10:
            self._trigger_alert(
                level='warning',
                title='High failure rate',
                message=f"Failure rate is {failure_rate:.2%}, threshold is {threshold:.2%}",
            )
        
        # 检查连续失败
        recent_failures = list(self._performance.recent_failures)
        consecutive = 0
        last_task = None
        
        for failure in reversed(recent_failures):
            if last_task and failure['task_id'] == last_task:
                consecutive += 1
            else:
                if consecutive >= self.alert_threshold.get('consecutive_failures', 3):
                    self._trigger_alert(
                        level='critical',
                        title=f'Consecutive task failures: {last_task}',
                        message=f'Task {last_task} has failed {consecutive} consecutive times',
                        task_id=last_task,
                    )
                consecutive = 1
                last_task = failure['task_id']
    
    def _check_failure_alert(self, task: Task, execution: TaskExecution):
        """检查失败告警"""
        # 检查是否超过重试次数
        if execution.retry_count >= task.retry_count:
            self._trigger_alert(
                level='warning',
                title=f'Task failed after retries: {task.name}',
                message=f"Task {task.name} failed after {execution.retry_count} retries. Last error: {execution.result.error}",
                task_id=task.task_id,
                execution_id=execution.execution_id,
            )
    
    def _trigger_alert(
        self,
        level: str,
        title: str,
        message: str,
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ):
        """触发告警"""
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            task_id=task_id,
            execution_id=execution_id,
        )
        
        self._alerts[alert_id] = alert
        logger.warning(f"Alert triggered: {title} - {message}")
        
        # 触发回调
        for callback in self._on_alert:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            logger.info(f"Alert resolved: {alert.title}")
    
    def _cleanup_metrics(self):
        """清理过期指标"""
        cutoff = datetime.now() - timedelta(seconds=self.metrics_retention)
        
        for name in list(self._metrics.keys()):
            self._metrics[name] = [
                m for m in self._metrics[name]
                if m.timestamp > cutoff
            ]
            
            if not self._metrics[name]:
                del self._metrics[name]
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取指标"""
        if name:
            return {
                'name': name,
                'data': [
                    {
                        'value': m.value,
                        'labels': m.labels,
                        'timestamp': m.timestamp.isoformat(),
                    }
                    for m in self._metrics.get(name, [])
                ]
            }
        
        return {
            'performance': self._performance.to_dict(),
            'metrics': {
                name: len(data)
                for name, data in self._metrics.items()
            },
        }
    
    def get_alerts(self, resolved: Optional[bool] = None) -> List[Alert]:
        """获取告警列表"""
        if resolved is None:
            return list(self._alerts.values())
        
        return [a for a in self._alerts.values() if a.resolved == resolved]
    
    def get_performance(self) -> PerformanceMetrics:
        """获取性能指标"""
        return self._performance
    
    def get_task_stats(self, task_id: str) -> Dict[str, Any]:
        """获取任务统计"""
        executions = [e for e in self._execution_history if e.task_id == task_id]
        
        if not executions:
            return {}
        
        completed = sum(1 for e in executions if e.status == TaskStatus.SUCCESS)
        failed = sum(1 for e in executions if e.status == TaskStatus.FAILED)
        
        durations = [
            e.result.duration
            for e in executions
            if e.result and e.result.duration
        ]
        
        return {
            'task_id': task_id,
            'total_executions': len(executions),
            'successful': completed,
            'failed': failed,
            'success_rate': completed / len(executions) if executions else 0,
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'last_execution': executions[-1].start_time.isoformat() if executions else None,
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """导出指标"""
        import json
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'performance': self._performance.to_dict(),
            'alerts': [
                {
                    'alert_id': a.alert_id,
                    'level': a.level,
                    'title': a.title,
                    'message': a.message,
                    'task_id': a.task_id,
                    'timestamp': a.timestamp.isoformat(),
                    'resolved': a.resolved,
                }
                for a in self._alerts.values()
            ],
        }
        
        if format == 'json':
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return str(data)
