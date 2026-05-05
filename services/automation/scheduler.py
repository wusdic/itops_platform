# -*- coding: utf-8 -*-
"""
ITOps Platform - Task Scheduler
任务调度器
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
import croniter


@dataclass
class ScheduledTask:
    """计划任务"""
    id: str
    name: str
    func: Callable
    trigger_type: str = "interval"  # interval, cron, once
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    max_instances: int = 1
    misfire_grace_time: int = 60
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
    
    def add_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        trigger_type: str = "interval",
        trigger_config: Dict = None,
        enabled: bool = True
    ) -> bool:
        """添加任务"""
        if task_id in self._tasks:
            return False
        
        trigger_config = trigger_config or {}
        
        # 创建触发器
        if trigger_type == "interval":
            trigger = IntervalTrigger(
                seconds=trigger_config.get("seconds", 60),
                minutes=trigger_config.get("minutes"),
                hours=trigger_config.get("hours"),
                days=trigger_config.get("days"),
            )
        elif trigger_type == "cron":
            trigger = CronTrigger(
                second=trigger_config.get("second", 0),
                minute=trigger_config.get("minute", "*"),
                hour=trigger_config.get("hour", "*"),
                day_of_week=trigger_config.get("day_of_week", "*"),
                day=trigger_config.get("day", "*"),
                month=trigger_config.get("month", "*"),
            )
        elif trigger_type == "once":
            run_date = trigger_config.get("run_date")
            trigger = DateTrigger(run_date=run_date)
        else:
            return False
        
        # 添加到调度器
        self._scheduler.add_job(
            func,
            trigger,
            id=task_id,
            name=name,
            replace_existing=True,
        )
        
        # 记录任务
        self._tasks[task_id] = ScheduledTask(
            id=task_id,
            name=name,
            func=func,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            enabled=enabled,
        )
        
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id not in self._tasks:
            return False
        
        self._scheduler.remove_job(task_id)
        del self._tasks[task_id]
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id not in self._tasks:
            return False
        
        self._scheduler.pause_job(task_id)
        self._tasks[task_id].enabled = False
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        if task_id not in self._tasks:
            return False
        
        self._scheduler.resume_job(task_id)
        self._tasks[task_id].enabled = True
        return True
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def start(self):
        """启动调度器"""
        if not self._running:
            self._scheduler.start()
            self._running = True
    
    def stop(self):
        """停止调度器"""
        if self._running:
            self._scheduler.shutdown()
            self._running = False
    
    def run_now(self, task_id: str) -> bool:
        """立即执行任务"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        try:
            result = task.func()
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)
            task.run_count += 1
            return True
        except Exception as e:
            task.error_count += 1
            print(f"任务执行失败: {e}")
            return False
    
    def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """获取下次运行时间"""
        job = self._scheduler.get_job(task_id)
        if job:
            return job.next_run_time
        return None
