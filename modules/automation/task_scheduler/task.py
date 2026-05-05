"""任务定义 - 任务基类及各类任务实现"""
import logging
import json
import asyncio
from typing import Optional, Callable, Dict, Any, List, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRY = "retry"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return self.success
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'metadata': self.metadata,
        }


@dataclass
class TaskExecution:
    """任务执行记录"""
    execution_id: str
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[TaskResult] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def add_log(self, message: str):
        """添加日志"""
        self.logs.append(f"[{datetime.now().isoformat()}] {message}")
    
    def mark_success(self, result: Any = None, metadata: Optional[Dict] = None):
        """标记成功"""
        self.status = TaskStatus.SUCCESS
        self.end_time = datetime.now()
        self.result = TaskResult(
            success=True,
            data=result,
            start_time=self.start_time,
            end_time=self.end_time,
            duration=(self.end_time - self.start_time).total_seconds(),
            metadata=metadata or {},
        )
    
    def mark_failed(self, error: str, metadata: Optional[Dict] = None):
        """标记失败"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.now()
        self.result = TaskResult(
            success=False,
            error=error,
            start_time=self.start_time,
            end_time=self.end_time,
            duration=(self.end_time - self.start_time).total_seconds(),
            metadata=metadata or {},
        )


@dataclass
class Task:
    """任务基类"""
    task_id: str
    name: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[int] = None  # 秒
    retry_count: int = 0
    retry_delay: int = 60  # 秒
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """执行任务"""
        pass
    
    def validate(self) -> bool:
        """验证任务配置"""
        return bool(self.name and self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority.value,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'enabled': self.enabled,
            'tags': self.tags,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class CollectionTask(Task):
    """数据采集任务"""
    
    def __init__(
        self,
        task_id: str = "",
        name: str = "",
        description: str = "",
        collector_type: str = "snmp",
        target: str = "",
        interval: int = 300,
        **kwargs
    ):
        super().__init__(task_id, name, description, **kwargs)
        self.collector_type = collector_type
        self.target = target
        self.interval = interval
    
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """执行采集任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing collection task: {self.name}")
            
            # 根据采集类型执行
            if self.collector_type == "snmp":
                result = await self._execute_snmp(context)
            elif self.collector_type == "log":
                result = await self._execute_log(context)
            elif self.collector_type == "script":
                result = await self._execute_script(context)
            else:
                result = await self._execute_generic(context)
            
            end_time = datetime.now()
            
            return TaskResult(
                success=True,
                data=result,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
            )
        except Exception as e:
            logger.error(f"Collection task failed: {e}")
            return TaskResult(
                success=False,
                error=str(e),
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    async def _execute_snmp(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行SNMP采集"""
        # 这里实现SNMP采集逻辑
        return {
            'collector_type': 'snmp',
            'target': self.target,
            'metrics': [],
        }
    
    async def _execute_log(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行日志采集"""
        return {
            'collector_type': 'log',
            'target': self.target,
            'logs_collected': 0,
        }
    
    async def _execute_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行脚本采集"""
        return {
            'collector_type': 'script',
            'target': self.target,
            'output': '',
        }
    
    async def _execute_generic(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行通用采集"""
        return {'status': 'completed'}


class ReportTask(Task):
    """报告生成任务"""
    
    def __init__(
        self,
        task_id: str = "",
        name: str = "",
        description: str = "",
        report_type: str = "daily",
        template: str = "",
        recipients: List[str] = field(default_factory=list),
        output_format: str = "pdf",
        **kwargs
    ):
        super().__init__(task_id, name, description, **kwargs)
        self.report_type = report_type
        self.template = template
        self.recipients = recipients
        self.output_format = output_format
    
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """执行报告任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing report task: {self.name}")
            
            # 生成报告
            report_data = await self._generate_report(context)
            
            # 发送报告（如果有收件人）
            if self.recipients:
                await self._send_report(report_data)
            
            end_time = datetime.now()
            
            return TaskResult(
                success=True,
                data={
                    'report_type': self.report_type,
                    'format': self.output_format,
                    'recipients': self.recipients,
                },
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
            )
        except Exception as e:
            logger.error(f"Report task failed: {e}")
            return TaskResult(
                success=False,
                error=str(e),
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    async def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        return {
            'title': self.name,
            'type': self.report_type,
            'generated_at': datetime.now().isoformat(),
            'data': {},
        }
    
    async def _send_report(self, report_data: Dict[str, Any]):
        """发送报告"""
        pass


class ScriptTask(Task):
    """脚本执行任务"""
    
    def __init__(
        self,
        task_id: str = "",
        name: str = "",
        description: str = "",
        script_type: str = "shell",
        script_content: str = "",
        script_path: str = "",
        working_dir: str = "",
        env_vars: Dict[str, str] = field(default_factory=dict),
        **kwargs
    ):
        super().__init__(task_id, name, description, **kwargs)
        self.script_type = script_type
        self.script_content = script_content
        self.script_path = script_path
        self.working_dir = working_dir
        self.env_vars = env_vars
    
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """执行脚本任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing script task: {self.name}")
            
            result = await self._run_script(context)
            
            end_time = datetime.now()
            
            return TaskResult(
                success=result['returncode'] == 0,
                data=result,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                metadata={'script_type': self.script_type},
            )
        except Exception as e:
            logger.error(f"Script task failed: {e}")
            return TaskResult(
                success=False,
                error=str(e),
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    async def _run_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行脚本"""
        import subprocess
        import os
        
        # 准备环境
        env = os.environ.copy()
        env.update(self.env_vars)
        
        # 确定脚本内容
        if self.script_path:
            cmd = [self.script_path]
        else:
            if self.script_type == 'shell':
                cmd = ['/bin/bash', '-c', self.script_content]
            elif self.script_type == 'python':
                cmd = ['python3', '-c', self.script_content]
            else:
                cmd = self.script_content.split()
        
        # 执行
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout
            )
            
            return {
                'returncode': proc.returncode,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
            }
        except asyncio.TimeoutError:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Timeout after {self.timeout} seconds',
            }


class WorkflowTask(Task):
    """任务链（工作流）"""
    
    def __init__(
        self,
        task_id: str = "",
        name: str = "",
        description: str = "",
        steps: List[Dict[str, Any]] = field(default_factory=list),
        continue_on_error: bool = True,
        **kwargs
    ):
        super().__init__(task_id, name, description, **kwargs)
        self.steps = steps
        self.continue_on_error = continue_on_error
    
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """执行工作流"""
        start_time = datetime.now()
        results = []
        all_success = True
        
        try:
            logger.info(f"Executing workflow: {self.name}")
            
            step_context = context.copy()
            
            for i, step in enumerate(self.steps):
                step_name = step.get('name', f'Step {i+1}')
                step_task_id = step.get('task_id')
                step_type = step.get('type', 'task')
                step_config = step.get('config', {})
                
                logger.info(f"Executing workflow step: {step_name}")
                
                try:
                    step_result = await self._execute_step(
                        step_type,
                        step_task_id,
                        step_config,
                        step_context
                    )
                    
                    results.append({
                        'step': i + 1,
                        'name': step_name,
                        'success': step_result.success,
                        'data': step_result.data,
                    })
                    
                    # 更新上下文
                    if step_result.data:
                        step_context[f'step_{i}_result'] = step_result.data
                    
                    if not step_result.success:
                        all_success = False
                        if not self.continue_on_error:
                            break
                
                except Exception as e:
                    logger.error(f"Workflow step failed: {e}")
                    results.append({
                        'step': i + 1,
                        'name': step_name,
                        'success': False,
                        'error': str(e),
                    })
                    all_success = False
                    if not self.continue_on_error:
                        break
            
            end_time = datetime.now()
            
            return TaskResult(
                success=all_success,
                data={
                    'workflow': self.name,
                    'steps': results,
                    'total_steps': len(self.steps),
                    'completed_steps': len(results),
                },
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
            )
        
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return TaskResult(
                success=False,
                error=str(e),
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    async def _execute_step(
        self,
        step_type: str,
        task_id: str,
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskResult:
        """执行工作流步骤"""
        if step_type == 'task':
            # 执行子任务
            # 这里应该从任务注册表获取任务
            pass
        elif step_type == 'delay':
            # 延迟
            delay_seconds = config.get('seconds', 0)
            await asyncio.sleep(delay_seconds)
            return TaskResult(success=True, data={'delayed': delay_seconds})
        elif step_type == 'condition':
            # 条件判断
            condition = config.get('condition', '')
            # 简单评估
            result = eval(condition, {}, context) if condition else True
            return TaskResult(success=True, data={'condition_result': result})
        elif step_type == 'script':
            # 脚本执行
            script_task = ScriptTask(
                name=config.get('name', 'Inline Script'),
                script_type=config.get('script_type', 'shell'),
                script_content=config.get('content', ''),
            )
            return await script_task.execute(context)
        
        return TaskResult(success=False, error=f"Unknown step type: {step_type}")


class TaskRegistry:
    """任务注册表"""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._factories: Dict[str, Callable] = {}
    
    def register(self, task: Task):
        """注册任务"""
        self._tasks[task.task_id] = task
        logger.info(f"Registered task: {task.task_id} - {task.name}")
    
    def unregister(self, task_id: str):
        """取消注册"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Unregistered task: {task_id}")
    
    def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def list_all(self) -> List[Task]:
        """列出所有任务"""
        return list(self._tasks.values())
    
    def register_factory(self, task_type: str, factory: Callable):
        """注册任务工厂"""
        self._factories[task_type] = factory
    
    def create_task(self, task_type: str, **kwargs) -> Task:
        """创建任务"""
        if task_type in self._factories:
            return self._factories[task_type](**kwargs)
        
        # 默认工厂
        if task_type == 'collection':
            return CollectionTask(**kwargs)
        elif task_type == 'report':
            return ReportTask(**kwargs)
        elif task_type == 'script':
            return ScriptTask(**kwargs)
        elif task_type == 'workflow':
            return WorkflowTask(**kwargs)
        else:
            return Task(**kwargs)
