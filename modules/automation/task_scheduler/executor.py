"""任务执行器 - 异步执行、超时控制、重试机制"""
import asyncio
import logging
import uuid
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback

from .task import Task, TaskResult, TaskExecution, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """执行上下文"""
    execution_id: str
    task_id: str
    start_time: datetime
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 0
    user_data: Dict[str, Any] = field(default_factory=dict)
    
    def elapsed(self) -> float:
        """获取已执行时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def is_timeout(self) -> bool:
        """检查是否超时"""
        if self.timeout is None:
            return False
        return self.elapsed() > self.timeout


class TaskExecutor:
    """
    任务执行器
    支持功能:
    - 异步执行
    - 超时控制
    - 重试机制
    - 执行日志
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        default_timeout: int = 3600,
        default_retry_count: int = 3,
        default_retry_delay: int = 60,
    ):
        """
        初始化执行器
        
        Args:
            max_workers: 最大工作线程数
            default_timeout: 默认超时时间（秒）
            default_retry_count: 默认重试次数
            default_retry_delay: 默认重试延迟（秒）
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.default_retry_count = default_retry_count
        self.default_retry_delay = default_retry_delay
        
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._on_start: List[Callable] = []
        self._on_complete: List[Callable] = []
        self._on_error: List[Callable] = []
    
    def on_start(self, callback: Callable):
        """注册开始回调"""
        self._on_start.append(callback)
    
    def on_complete(self, callback: Callable):
        """注册完成回调"""
        self._on_complete.append(callback)
    
    def on_error(self, callback: Callable):
        """注册错误回调"""
        self._on_error.append(callback)
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None,
        retry_delay: Optional[int] = None,
    ) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            context: 执行上下文
            timeout: 超时时间（秒）
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            TaskResult: 任务结果
        """
        timeout = timeout or task.timeout or self.default_timeout
        retry_count = retry_count if retry_count is not None else task.retry_count
        retry_delay = retry_delay or task.retry_delay or self.default_retry_delay
        
        # 创建执行上下文
        exec_context = ExecutionContext(
            execution_id=str(uuid.uuid4()),
            task_id=task.task_id,
            start_time=datetime.now(),
            timeout=timeout,
            max_retries=retry_count,
            user_data=context or {},
        )
        
        # 创建执行记录
        execution = TaskExecution(
            execution_id=exec_context.execution_id,
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=exec_context.start_time,
        )
        self._executions[exec_context.execution_id] = execution
        
        logger.info(f"Starting task execution: {task.name} ({exec_context.execution_id})")
        
        # 触发开始回调
        for callback in self._on_start:
            try:
                await callback(task, execution)
            except Exception as e:
                logger.error(f"Error in start callback: {e}")
        
        attempt = 0
        last_error = None
        
        while attempt <= retry_count:
            try:
                execution.retry_count = attempt
                execution.add_log(f"Attempt {attempt + 1}/{retry_count + 1}")
                
                # 执行任务
                result = await self._execute_with_timeout(
                    task,
                    exec_context,
                    timeout
                )
                
                if result.success:
                    execution.mark_success(result.data, result.metadata)
                    logger.info(f"Task completed successfully: {task.name}")
                    
                    # 触发完成回调
                    for callback in self._on_complete:
                        try:
                            await callback(task, execution, result)
                        except Exception as e:
                            logger.error(f"Error in complete callback: {e}")
                    
                    return result
                else:
                    last_error = result.error
                    execution.add_log(f"Task failed: {result.error}")
                    logger.warning(f"Task attempt failed: {task.name} - {result.error}")
            
            except asyncio.TimeoutError:
                last_error = f"Task timeout after {timeout} seconds"
                execution.add_log(f"Task timeout: {timeout}s")
                logger.warning(f"Task timeout: {task.name}")
                
                # 标记超时状态
                execution.status = TaskStatus.TIMEOUT
            
            except Exception as e:
                last_error = str(e)
                execution.add_log(f"Task error: {e}\n{traceback.format_exc()}")
                logger.error(f"Task error: {task.name} - {e}")
            
            attempt += 1
            
            if attempt <= retry_count:
                execution.add_log(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        
        # 所有重试都失败
        execution.mark_failed(last_error or "Unknown error")
        logger.error(f"Task failed after {retry_count + 1} attempts: {task.name}")
        
        # 触发错误回调
        for callback in self._on_error:
            try:
                await callback(task, execution, last_error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        return TaskResult(
            success=False,
            error=last_error,
            start_time=execution.start_time,
            end_time=execution.end_time,
            duration=execution.result.duration if execution.result else None,
        )
    
    async def _execute_with_timeout(
        self,
        task: Task,
        context: ExecutionContext,
        timeout: int
    ) -> TaskResult:
        """带超时的执行"""
        try:
            result = await asyncio.wait_for(
                task.execute(context.user_data),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise
    
    async def execute_sync(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """同步执行任务（在线程池中）"""
        loop = asyncio.get_event_loop()
        
        def run_sync():
            return asyncio.run(task.execute(context or {}))
        
        future = self._executor.submit(run_sync)
        return await asyncio.wrap_future(future)
    
    async def execute_batch(
        self,
        tasks: List[Task],
        context: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5,
    ) -> List[TaskResult]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表
            context: 执行上下文
            max_concurrent: 最大并发数
            
        Returns:
            任务结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task: Task):
            async with semaphore:
                return await self.execute(task, context)
        
        # 并发执行
        coroutines = [execute_with_semaphore(task) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TaskResult(
                    success=False,
                    error=str(result),
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """获取执行记录"""
        return self._executions.get(execution_id)
    
    def get_all_executions(self) -> List[TaskExecution]:
        """获取所有执行记录"""
        return list(self._executions.values())
    
    def cancel(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self._running_tasks:
            task = self._running_tasks[execution_id]
            task.cancel()
            del self._running_tasks[execution_id]
            return True
        return False
    
    def cancel_all(self):
        """取消所有执行"""
        for task in self._running_tasks.values():
            task.cancel()
        self._running_tasks.clear()
    
    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self.cancel_all()
        self._executor.shutdown(wait=wait)


class AsyncTaskExecutor(TaskExecutor):
    """异步任务执行器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def start(self):
        """启动执行器"""
        self._running = True
        asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """停止执行器"""
        self._running = False
    
    async def _process_queue(self):
        """处理任务队列"""
        while self._running:
            try:
                task, context, result_future = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                result = await self.execute(task, context)
                result_future.set_result(result)
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing task queue: {e}")
    
    async def submit(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> asyncio.Future:
        """
        提交任务
        
        Returns:
            asyncio.Future: 结果Future
        """
        loop = asyncio.get_event_loop()
        result_future = loop.create_future()
        
        await self._task_queue.put((task, context, result_future))
        
        return result_future
    
    async def submit_and_wait(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> TaskResult:
        """提交并等待结果"""
        future = await self.submit(task, context)
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return TaskResult(
                success=False,
                error=f"Task timeout after {timeout} seconds",
            )
