"""任务调度器核心 - APScheduler封装"""
import logging
import uuid
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
)
import pytz

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """触发器类型"""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"
    ONCE = "once"


@dataclass
class JobInfo:
    """任务作业信息"""
    job_id: str
    name: str
    trigger_type: TriggerType
    trigger_args: Dict[str, Any]
    func_ref: str
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: Optional[int] = None
    next_run_time: Optional[datetime] = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)


class TaskScheduler:
    """
    任务调度器
    基于APScheduler的任务调度系统
    
    支持功能:
    - Cron表达式解析
    - 任务注册与管理
    - 任务状态跟踪
    - 并发控制
    """
    
    def __init__(
        self,
        timezone: str = "Asia/Shanghai",
        job_defaults: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化任务调度器
        
        Args:
            timezone: 时区
            job_defaults: 作业默认配置
            executor_config: 执行器配置
        """
        self.timezone = timezone
        self._scheduler = BackgroundScheduler(
            timezone=timezone,
            job_defaults=job_defaults or {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60,
            },
            executors=executor_config or {
                'default': {
                    'type': 'threadpool',
                    'max_workers': 10,
                },
                'processpool': {
                    'type': 'processpool',
                    'max_workers': 4,
                },
            }
        )
        
        self._jobs: Dict[str, JobInfo] = {}
        self._listeners: Dict[str, List[Callable]] = {
            'executed': [],
            'error': [],
            'missed': [],
            'submitted': [],
        }
        self._running = False
    
    def start(self):
        """启动调度器"""
        if self._running:
            return
        
        # 注册事件监听
        self._scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        self._scheduler.add_listener(
            self._on_job_missed,
            EVENT_JOB_MISSED
        )
        self._scheduler.add_listener(
            self._on_job_submitted,
            EVENT_JOB_SUBMITTED
        )
        
        self._scheduler.start()
        self._running = True
        logger.info("Task scheduler started")
    
    def stop(self, wait: bool = True):
        """停止调度器"""
        if not self._running:
            return
        
        self._scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("Task scheduler stopped")
    
    def _on_job_executed(self, event):
        """作业执行完成回调"""
        job_id = event.job_id
        
        # 更新作业状态
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "completed"
            job.next_run_time = event.scheduled_run_time
        
        # 触发监听器
        for listener in self._listeners['executed']:
            try:
                listener(event, None)
            except Exception as e:
                logger.error(f"Error in executed listener: {e}")
    
    def _on_job_error(self, event):
        """作业执行错误回调"""
        job_id = event.job_id
        
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "error"
        
        for listener in self._listeners['error']:
            try:
                listener(event, event.exception)
            except Exception as e:
                logger.error(f"Error in error listener: {e}")
    
    def _on_job_missed(self, event):
        """作业错过的回调"""
        job_id = event.job_id
        
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "missed"
        
        for listener in self._listeners['missed']:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in missed listener: {e}")
    
    def _on_job_submitted(self, event):
        """作业提交回调"""
        job_id = event.job_id
        
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "running"
        
        for listener in self._listeners['submitted']:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in submitted listener: {e}")
    
    def add_listener(self, event: str, callback: Callable):
        """添加事件监听器"""
        if event in self._listeners:
            self._listeners[event].append(callback)
    
    def remove_listener(self, event: str, callback: Callable):
        """移除事件监听器"""
        if event in self._listeners:
            self._listeners[event].remove(callback)
    
    def _parse_cron(self, cron_expr: str) -> Dict[str, Any]:
        """解析Cron表达式"""
        parts = cron_expr.strip().split()
        
        if len(parts) < 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        result = {}
        
        # 秒 分 时 日 月 周
        if len(parts) >= 6:
            result['second'] = parts[0]
            result['minute'] = parts[1]
            result['hour'] = parts[2]
            result['day'] = parts[3]
            result['month'] = parts[4]
            result['day_of_week'] = parts[5]
        else:
            result['minute'] = parts[0]
            result['hour'] = parts[1]
            result['day'] = parts[2]
            result['month'] = parts[3]
            result['day_of_week'] = parts[4]
        
        return result
    
    def _create_trigger(self, trigger_type: TriggerType, trigger_args: Dict[str, Any]):
        """创建触发器"""
        if trigger_type == TriggerType.CRON:
            return CronTrigger(
                timezone=self.timezone,
                **trigger_args
            )
        elif trigger_type == TriggerType.INTERVAL:
            return IntervalTrigger(
                timezone=self.timezone,
                **trigger_args
            )
        elif trigger_type == TriggerType.DATE:
            return DateTrigger(
                run_date=trigger_args.get('run_date'),
                timezone=self.timezone,
            )
        elif trigger_type == TriggerType.ONCE:
            return DateTrigger(
                run_date=trigger_args.get('run_date', datetime.now()),
                timezone=self.timezone,
            )
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")
    
    def add_job(
        self,
        func: Callable,
        trigger_type: TriggerType,
        name: str,
        job_id: Optional[str] = None,
        trigger_args: Optional[Dict[str, Any]] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        max_instances: int = 1,
        coalesce: bool = True,
        misfire_grace_time: Optional[int] = 60,
        **extra_config
    ) -> str:
        """
        添加任务
        
        Args:
            func: 任务函数
            trigger_type: 触发器类型
            name: 任务名称
            job_id: 任务ID
            trigger_args: 触发器参数
            args: 位置参数
            kwargs: 关键字参数
            max_instances: 最大实例数
            coalesce: 合并错过的执行
            misfire_grace_time: 错过执行的宽限时间（秒）
            
        Returns:
            job_id: 任务ID
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        if job_id in self._jobs:
            raise ValueError(f"Job ID already exists: {job_id}")
        
        trigger_args = trigger_args or {}
        args = args or ()
        kwargs = kwargs or {}
        
        # 解析Cron表达式
        if trigger_type == TriggerType.CRON and isinstance(trigger_args.get('cron'), str):
            cron_expr = trigger_args.pop('cron')
            trigger_args.update(self._parse_cron(cron_expr))
        
        # 创建触发器
        trigger = self._create_trigger(trigger_type, trigger_args)
        
        # 添加作业
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            args=args,
            kwargs=kwargs,
            max_instances=max_instances,
            coalesce=coalesce,
            misfire_grace_time=misfire_grace_time,
            **extra_config
        )
        
        # 保存作业信息
        job_info = JobInfo(
            job_id=job_id,
            name=name,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            func_ref=f"{func.__module__}.{func.__name__}",
            args=args,
            kwargs=kwargs,
            max_instances=max_instances,
            coalesce=coalesce,
            misfire_grace_time=misfire_grace_time,
        )
        self._jobs[job_id] = job_info
        
        logger.info(f"Added job: {name} ({job_id})")
        return job_id
    
    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id not in self._jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        self._scheduler.remove_job(job_id)
        del self._jobs[job_id]
        logger.info(f"Removed job: {job_id}")
    
    def pause_job(self, job_id: str):
        """暂停任务"""
        if job_id not in self._jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        self._scheduler.pause_job(job_id)
        self._jobs[job_id].status = "paused"
        logger.info(f"Paused job: {job_id}")
    
    def resume_job(self, job_id: str):
        """恢复任务"""
        if job_id not in self._jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        self._scheduler.resume_job(job_id)
        self._jobs[job_id].status = "pending"
        logger.info(f"Resumed job: {job_id}")
    
    def run_job(self, job_id: str, wait: bool = True) -> Any:
        """立即运行任务"""
        if job_id not in self._jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        job = self._scheduler.get_job(job_id)
        if job:
            return self._scheduler.run_job(job, wait=wait)
        return None
    
    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """获取任务信息"""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[JobInfo]:
        """获取所有任务"""
        return list(self._jobs.values())
    
    def get_next_run_time(self, job_id: str) -> Optional[datetime]:
        """获取任务下次运行时间"""
        job = self._scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        result = []
        
        for job_id, job_info in self._jobs.items():
            aps_job = self._scheduler.get_job(job_id)
            
            result.append({
                'job_id': job_id,
                'name': job_info.name,
                'trigger_type': job_info.trigger_type.value,
                'trigger_args': job_info.trigger_args,
                'func_ref': job_info.func_ref,
                'status': job_info.status,
                'next_run_time': job_info.next_run_time.isoformat() if job_info.next_run_time else None,
                'max_instances': job_info.max_instances,
                'created_at': job_info.created_at.isoformat(),
            })
        
        return result
    
    # 便捷方法
    
    def add_cron_job(
        self,
        func: Callable,
        cron: str,
        name: str,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """添加Cron任务"""
        return self.add_job(
            func=func,
            trigger_type=TriggerType.CRON,
            name=name,
            job_id=job_id,
            trigger_args={'cron': cron},
            **kwargs
        )
    
    def add_interval_job(
        self,
        func: Callable,
        interval: int,
        name: str,
        unit: str = "seconds",
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """添加间隔任务"""
        return self.add_job(
            func=func,
            trigger_type=TriggerType.INTERVAL,
            name=name,
            job_id=job_id,
            trigger_args={unit: interval},
            **kwargs
        )
    
    def add_once_job(
        self,
        func: Callable,
        run_date: datetime,
        name: str,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """添加一次性任务"""
        return self.add_job(
            func=func,
            trigger_type=TriggerType.ONCE,
            name=name,
            job_id=job_id,
            trigger_args={'run_date': run_date},
            **kwargs
        )
    
    def is_running(self) -> bool:
        """检查调度器是否运行"""
        return self._running
    
    @property
    def scheduler(self) -> BackgroundScheduler:
        """获取底层调度器"""
        return self._scheduler
