"""
浏览器任务执行器
定时任务执行和队列管理
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    start_time: float
    end_time: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    log_path: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """执行时长"""
        end = self.end_time or asyncio.get_event_loop().time()
        return end - self.start_time
    
    @property
    def success(self) -> bool:
        """是否成功"""
        return self.status == TaskStatus.COMPLETED


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    script_path: str
    schedule: Optional[str] = None  # cron格式
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300  # 秒
    retry_count: int = 3
    retry_interval: int = 60  # 秒
    device_id: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    config: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=datetime.now().timestamp)
    updated_at: float = field(default_factory=datetime.now().timestamp)
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    run_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'script_path': self.script_path,
            'schedule': self.schedule,
            'priority': self.priority.value,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_interval': self.retry_interval,
            'device_id': self.device_id,
            'credentials': self.credentials,
            'config': self.config,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_run_at': self.last_run_at,
            'next_run_at': self.next_run_at,
            'run_count': self.run_count,
            'success_count': self.success_count,
            'fail_count': self.fail_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        return cls(
            id=data['id'],
            name=data['name'],
            script_path=data['script_path'],
            schedule=data.get('schedule'),
            priority=TaskPriority(data.get('priority', 5)),
            timeout=data.get('timeout', 300),
            retry_count=data.get('retry_count', 3),
            retry_interval=data.get('retry_interval', 60),
            device_id=data.get('device_id'),
            credentials=data.get('credentials'),
            config=data.get('config', {}),
            status=TaskStatus(data.get('status', 'pending')),
            created_at=data.get('created_at', datetime.now().timestamp()),
            updated_at=data.get('updated_at', datetime.now().timestamp()),
            last_run_at=data.get('last_run_at'),
            next_run_at=data.get('next_run_at'),
            run_count=data.get('run_count', 0),
            success_count=data.get('success_count', 0),
            fail_count=data.get('fail_count', 0)
        )


class TaskQueue:
    """
    任务队列
    
    基于优先级的任务队列管理
    """
    
    def __init__(self):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
    
    async def add_task(self, task: Task):
        """
        添加任务
        
        Args:
            task: 任务对象
        """
        async with self._lock:
            self._tasks[task.id] = task
            # 优先级: (priority, timestamp)
            priority = (256 - task.priority.value, task.created_at)
            await self._queue.put((priority, task.id))
        
        logger.info(f"任务已添加: {task.name} (优先级: {task.priority.name})")
    
    async def get_task(self, timeout: float = None) -> Optional[Task]:
        """
        获取任务
        
        Args:
            timeout: 超时时间
        
        Returns:
            任务对象
        """
        try:
            _, task_id = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            async with self._lock:
                return self._tasks.get(task_id)
        except asyncio.TimeoutError:
            return None
    
    async def remove_task(self, task_id: str):
        """
        移除任务
        
        Args:
            task_id: 任务ID
        """
        async with self._lock:
            self._tasks.pop(task_id, None)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None
    
    async def update_task_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = status
                self._tasks[task_id].updated_at = datetime.now().timestamp()
    
    async def get_pending_tasks(self) -> List[Task]:
        """获取待执行任务"""
        async with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
    
    async def get_running_tasks(self) -> List[Task]:
        """获取运行中任务"""
        async with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
    
    @property
    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()


class TaskExecutor:
    """
    任务执行器
    
    功能特性：
    1. 定时任务执行
    2. 任务队列管理
    3. 执行日志记录
    """
    
    def __init__(self, db_path: str = None, log_dir: str = "/tmp/browser_tasks"):
        """
        初始化执行器
        
        Args:
            db_path: SQLite数据库路径
            log_dir: 日志目录
        """
        self._db_path = db_path or "/tmp/browser_tasks.db"
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        self._queue = TaskQueue()
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._scheduler: Optional[asyncio.Task] = None
        self._results: Dict[str, TaskResult] = {}
        self._lock = asyncio.Lock()
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                duration REAL,
                output TEXT,
                error TEXT,
                created_at REAL DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        conn.commit()
        conn.close()
    
    async def start(self, workers: int = 3):
        """
        启动执行器
        
        Args:
            workers: 工作线程数
        """
        if self._running:
            return
        
        self._running = True
        
        # 启动工作线程
        for i in range(workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        # 启动调度器
        self._scheduler = asyncio.create_task(self._scheduler_loop())
        
        logger.info(f"任务执行器已启动 ({workers} workers)")
    
    async def stop(self):
        """停止执行器"""
        self._running = False
        
        # 取消工作线程
        for worker in self._workers:
            worker.cancel()
        
        # 取消调度器
        if self._scheduler:
            self._scheduler.cancel()
        
        # 等待所有任务完成
        await asyncio.gather(*self._workers, self._scheduler, return_exceptions=True)
        
        self._workers.clear()
        logger.info("任务执行器已停止")
    
    async def submit_task(self, task: Task):
        """
        提交任务
        
        Args:
            task: 任务对象
        """
        await self._queue.add_task(task)
    
    async def submit_tasks(self, tasks: List[Task]):
        """
        批量提交任务
        
        Args:
            tasks: 任务列表
        """
        for task in tasks:
            await self.submit_task(task)
    
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        async with self._lock:
            return self._results.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        status = await self._queue.get_task_status(task_id)
        if status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            await self._queue.update_task_status(task_id, TaskStatus.CANCELLED)
            return True
        return False
    
    async def _worker(self, worker_id: int):
        """
        工作线程
        
        Args:
            worker_id: 工作线程ID
        """
        logger.info(f"Worker {worker_id} 已启动")
        
        while self._running:
            task = await self._queue.get_task(timeout=1.0)
            if not task:
                continue
            
            if task.status == TaskStatus.CANCELLED:
                continue
            
            # 更新状态
            await self._queue.update_task_status(task.id, TaskStatus.RUNNING)
            task.status = TaskStatus.RUNNING
            task.last_run_at = datetime.now().timestamp()
            task.run_count += 1
            
            # 执行任务
            result = await self._execute_task(task)
            
            # 记录结果
            async with self._lock:
                self._results[task.id] = result
            
            # 更新任务统计
            if result.success:
                task.success_count += 1
                task.status = TaskStatus.COMPLETED
            else:
                task.fail_count += 1
                task.status = TaskStatus.FAILED
            
            task.updated_at = datetime.now().timestamp()
            
            # 保存历史
            self._save_history(task, result)
        
        logger.info(f"Worker {worker_id} 已停止")
    
    async def _execute_task(self, task: Task) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 任务对象
        
        Returns:
            任务结果
        """
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now().timestamp()
        )
        
        # 创建日志文件
        log_path = self._log_dir / f"{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        result.log_path = str(log_path)
        
        # 设置日志处理器
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        task_logger = logging.getLogger(f'task_{task.id}')
        task_logger.addHandler(file_handler)
        task_logger.setLevel(logging.DEBUG)
        
        try:
            task_logger.info(f"开始执行任务: {task.name}")
            
            # 导入脚本
            import importlib.util
            spec = importlib.util.spec_from_file_location("task_script", task.script_path)
            if not spec or not spec.loader:
                raise Exception(f"无法加载脚本: {task.script_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # 创建浏览器配置
            from .browser_driver import BrowserConfig, BrowserDriver
            
            config_data = task.config.get('browser', {})
            config = BrowserConfig(
                headless=config_data.get('headless', True),
                timeout=config_data.get('timeout', 30000),
                viewport_width=config_data.get('viewport_width', 1920),
                viewport_height=config_data.get('viewport_height', 1080)
            )
            
            async with BrowserDriver(config) as driver:
                await driver.start()
                
                # 如果有登录凭证，先登录
                if task.credentials:
                    await self._perform_login(driver, task.credentials, task_logger)
                
                # 执行脚本
                try:
                    spec.loader.exec_module(module)
                    if hasattr(module, 'run_script'):
                        output = await module.run_script(driver)
                        result.output = output or {'status': 'completed'}
                    elif hasattr(module, 'main'):
                        await module.main()
                except Exception as e:
                    task_logger.error(f"脚本执行失败: {e}")
                    raise
            
            result.status = TaskStatus.COMPLETED
            task_logger.info("任务执行成功")
            
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            task_logger.error(f"任务执行失败: {e}")
        
        finally:
            result.end_time = datetime.now().timestamp()
            task_logger.removeHandler(file_handler)
            file_handler.close()
        
        return result
    
    async def _perform_login(self, driver, credentials: Dict[str, Any], logger):
        """
        执行登录
        
        Args:
            driver: 浏览器驱动
            credentials: 登录凭证
            logger: 日志记录器
        """
        login_url = credentials.get('login_url')
        username = credentials.get('username')
        password = credentials.get('password')
        username_selector = credentials.get('username_selector')
        password_selector = credentials.get('password_selector')
        submit_selector = credentials.get('submit_selector')
        
        if not all([login_url, username, password, username_selector, password_selector, submit_selector]):
            logger.warning("登录凭证不完整，跳过登录")
            return
        
        from .browser_driver import ElementSelector
        
        logger.info(f"正在登录: {login_url}")
        
        await driver.navigate(login_url)
        await asyncio.sleep(1)  # 等待页面加载
        
        # 输入用户名
        await driver.fill(
            ElementSelector(username_selector, 'css'),
            username
        )
        
        # 输入密码
        await driver.fill(
            ElementSelector(password_selector, 'css'),
            password
        )
        
        # 点击登录
        await driver.click(
            ElementSelector(submit_selector, 'css')
        )
        
        await asyncio.sleep(2)  # 等待登录完成
        logger.info("登录完成")
    
    async def _scheduler_loop(self):
        """调度循环"""
        from croniter import croniter
        
        logger.info("调度器已启动")
        
        while self._running:
            try:
                # 检查定时任务
                pending = await self._queue.get_pending_tasks()
                now = datetime.now().timestamp()
                
                for task in pending:
                    if task.schedule:
                        try:
                            cron = croniter(task.schedule, datetime.now())
                            next_run = cron.get_next()
                            
                            if task.next_run_at is None or task.next_run_at <= now:
                                task.next_run_at = next_run.timestamp()
                                await self._queue.add_task(task)
                        except Exception as e:
                            logger.error(f"解析调度规则失败: {task.schedule} - {e}")
                
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
            
            await asyncio.sleep(60)  # 每分钟检查一次
        
        logger.info("调度器已停止")
    
    def _save_history(self, task: Task, result: TaskResult):
        """
        保存执行历史
        
        Args:
            task: 任务对象
            result: 执行结果
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO task_history 
            (id, task_id, task_name, status, start_time, end_time, duration, output, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            result.task_id,
            task.name,
            result.status.value,
            result.start_time,
            result.end_time,
            result.duration,
            json.dumps(result.output) if result.output else None,
            result.error
        ))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        Args:
            limit: 返回数量
        
        Returns:
            历史记录列表
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM task_history 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_task_logs(self, task_id: str) -> List[str]:
        """
        获取任务日志
        
        Args:
            task_id: 任务ID
        
        Returns:
            日志内容
        """
        result = asyncio.get_event_loop().run_until_complete(
            self.get_result(task_id)
        )
        
        if not result or not result.log_path:
            return []
        
        log_path = Path(result.log_path)
        if log_path.exists():
            return log_path.read_text().splitlines()
        
        return []
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
