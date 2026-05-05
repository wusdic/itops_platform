"""
定时报告调度服务
基于APScheduler实现定时任务
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ReportScheduler:
    """报告调度器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.scheduler = BackgroundScheduler(
            jobstores={'default': MemoryJobStore()},
            executors={'default': ThreadPoolExecutor(max_workers=4)},
            job_defaults={
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 60 * 5  # 5分钟
            },
            timezone='Asia/Shanghai'
        )
        
        self._report_callbacks: List[Callable] = []
        self._running = False
    
    def start(self):
        """启动调度器"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Report scheduler started")
    
    def shutdown(self):
        """关闭调度器"""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Report scheduler stopped")
    
    def register_report_callback(self, callback: Callable):
        """注册报告生成回调函数"""
        self._report_callbacks.append(callback)
    
    def calculate_next_run(self, cron_expression: str) -> Optional[datetime]:
        """计算下次执行时间"""
        # 简单的cron解析，用于计算下次执行时间
        # 格式: 分 时 日 月 周
        try:
            parts = cron_expression.split()
            if len(parts) >= 5:
                now = datetime.now()
                # 简化实现，实际应该使用croniter库
                return now + timedelta(days=1)
        except Exception as e:
            logger.error(f"Failed to parse cron expression: {e}")
        return None
    
    def add_schedule(self, schedule_id: str, cron_expression: str,
                     func: Callable, args: tuple = (), kwargs: dict = None) -> bool:
        """
        添加定时任务
        
        Args:
            schedule_id: 任务ID
            cron_expression: Cron表达式 (分 时 日 月 周)
            func: 执行函数
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            是否添加成功
        """
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                logger.error(f"Invalid cron expression: {cron_expression}")
                return False
            
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone='Asia/Shanghai'
            )
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=schedule_id,
                args=args,
                kwargs=kwargs or {},
                replace_existing=True
            )
            
            logger.info(f"Added scheduled task: {schedule_id}, cron: {cron_expression}")
            return True
        except Exception as e:
            logger.error(f"Failed to add scheduled task: {e}")
            return False
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """移除定时任务"""
        try:
            self.scheduler.remove_job(schedule_id)
            logger.info(f"Removed scheduled task: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove scheduled task: {e}")
            return False
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """暂停定时任务"""
        try:
            self.scheduler.pause_job(schedule_id)
            logger.info(f"Paused scheduled task: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause scheduled task: {e}")
            return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """恢复定时任务"""
        try:
            self.scheduler.resume_job(schedule_id)
            logger.info(f"Resumed scheduled task: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume scheduled task: {e}")
            return False
    
    def get_schedule_info(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        try:
            job = self.scheduler.get_job(schedule_id)
            if job:
                return {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "pending": job.pending
                }
        except Exception as e:
            logger.error(f"Failed to get schedule info: {e}")
        return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """获取所有定时任务"""
        schedules = []
        for job in self.scheduler.get_jobs():
            schedules.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "pending": job.pending
            })
        return schedules
    
    def execute_now(self, schedule_id: str) -> bool:
        """立即执行任务"""
        try:
            job = self.scheduler.get_job(schedule_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"Triggered immediate execution: {schedule_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to execute schedule: {e}")
        return False


# 全局调度器实例
_scheduler = ReportScheduler()


def get_scheduler() -> ReportScheduler:
    """获取调度器实例"""
    return _scheduler


def start_scheduler():
    """启动全局调度器"""
    _scheduler.start()


def stop_scheduler():
    """停止全局调度器"""
    _scheduler.shutdown()