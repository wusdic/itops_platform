"""
脚本执行器 (executor.py)

提供本地/远程脚本执行、多脚本批量执行、脚本参数化、超时控制、输出捕获等功能
"""

import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml


class ExecutionStatus(Enum):
    """脚本执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ScriptType(Enum):
    """支持的脚本类型"""
    SHELL = "shell"
    POWERSHELL = "powershell"
    PYTHON = "python"
    ANSIBLE = "ansible"


@dataclass
class ExecutionResult:
    """脚本执行结果"""
    task_id: str
    script_name: str
    script_type: ScriptType
    status: ExecutionStatus
    return_code: int
    stdout: str
    stderr: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    host: str = "localhost"
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'script_name': self.script_name,
            'script_type': self.script_type.value,
            'status': self.status.value,
            'return_code': self.return_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'host': self.host,
            'parameters': self.parameters,
            'error_message': self.error_message,
        }


@dataclass
class Script:
    """脚本定义"""
    name: str
    script_type: ScriptType
    content: str
    description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = 300
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    interpreter_path: Optional[str] = None
    rollback_script: Optional[str] = None  # 回滚脚本内容
    enable_auto_rollback: bool = False  # 是否在执行失败时自动回滚
    
    def get_interpreter(self) -> str:
        """获取脚本解释器路径"""
        if self.interpreter_path:
            return self.interpreter_path
        
        type_to_interpreter = {
            ScriptType.SHELL: "/bin/bash",
            ScriptType.POWERSHELL: "pwsh",
            ScriptType.PYTHON: "python3",
            ScriptType.ANSIBLE: "ansible-playbook",
        }
        return type_to_interpreter.get(self.script_type, "/bin/bash")
    
    def get_extension(self) -> str:
        """获取脚本文件扩展名"""
        extensions = {
            ScriptType.SHELL: ".sh",
            ScriptType.POWERSHELL: ".ps1",
            ScriptType.PYTHON: ".py",
            ScriptType.ANSIBLE: ".yml",
        }
        return extensions.get(self.script_type, ".sh")
    
    def render_content(self, params: Dict[str, Any]) -> str:
        """渲染脚本内容，支持参数替换"""
        content = self.content
        for key, value in params.items():
            # 支持 ${key} 和 {{key}} 两种格式
            content = content.replace(f"${{{key}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content


class ScriptExecutor:
    """
    脚本执行器
    
    提供本地脚本执行、多脚本批量执行、超时控制、输出捕获等功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化脚本执行器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._execution_history: List[ExecutionResult] = []
        self._max_history = self.config.get('max_history', 1000)
        self._active_tasks: Dict[str, threading.Thread] = {}
        self._cancellation_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        
        # 默认配置
        self._default_timeout = self.config.get('default_timeout', 300)
        self._output_buffer_size = self.config.get('output_buffer_size', 8192)
        
        # 回滚管理器
        from .rollback import RollbackManager, SnapshotType, get_rollback_manager
        self._rollback_manager = get_rollback_manager()
        
        # 注册默认的快照创建器（设备配置快照）
        # 使用lambda延迟引用，因为方法定义在类中靠后的位置
        self._rollback_manager.register_snapshot_creator(
            SnapshotType.DEVICE_CONFIG,
            lambda exec_id: self._create_device_config_snapshot(exec_id)
        )
    
    def execute(
        self,
        script: Union[str, Script],
        script_type: Optional[ScriptType] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        host: str = "localhost",
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ExecutionResult:
        """
        执行单个脚本
        
        Args:
            script: 脚本内容或Script对象
            script_type: 脚本类型（当script为字符串时必需）
            parameters: 脚本参数
            timeout: 超时时间（秒）
            working_dir: 工作目录
            env_vars: 环境变量
            capture_output: 是否捕获输出
            host: 目标主机
            on_output: 输出回调函数
            
        Returns:
            ExecutionResult: 执行结果
        """
        # 构建Script对象
        if isinstance(script, str):
            if script_type is None:
                script_type = self._detect_script_type(script)
            script_obj = Script(
                name=f"script_{uuid.uuid4().hex[:8]}",
                script_type=script_type,
                content=script,
            )
        else:
            script_obj = script
        
        # 合并参数
        parameters = parameters or {}
        timeout = timeout or script_obj.timeout or self._default_timeout
        working_dir = working_dir or script_obj.working_dir
        env_vars = {**script_obj.env_vars, **(env_vars or {})}
        
        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        # 创建取消标志
        cancel_event = threading.Event()
        with self._lock:
            self._cancellation_flags[task_id] = cancel_event
        
        # 准备执行结果
        result = ExecutionResult(
            task_id=task_id,
            script_name=script_obj.name,
            script_type=script_obj.script_type,
            status=ExecutionStatus.RUNNING,
            return_code=-1,
            stdout="",
            stderr="",
            start_time=datetime.now(),
            host=host,
            parameters=parameters,
        )
        
        # 渲染脚本内容
        rendered_content = script_obj.render_content(parameters)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=script_obj.get_extension(),
            delete=False,
        ) as f:
            f.write(rendered_content)
            script_path = f.name
        
        try:
            # 构建命令
            cmd = self._build_command(script_obj, script_path)
            
            # 准备环境变量
            full_env = os.environ.copy()
            full_env.update(env_vars)
            
            # 设置工作目录
            cwd = working_dir or os.getcwd()
            
            # 执行脚本
            result = self._run_process(
                task_id=task_id,
                cmd=cmd,
                env=full_env,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                cancel_event=cancel_event,
                on_output=on_output,
                result=result,
            )
            
        except subprocess.TimeoutExpired:
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = f"Script execution timed out after {timeout} seconds"
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
        finally:
            # 总是保存快照（在失败/超时时）
            # 这允许后续手动回滚
            rollback_triggered = False
            if result.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT):
                rollback_triggered = self._trigger_auto_rollback(
                    task_id, script_obj, result
                )
            
            # 如果触发了回滚，在error_message中标记
            if rollback_triggered:
                result.error_message = f"{result.error_message} [Auto-rollback triggered]"
            
            # 清理临时文件
            try:
                os.unlink(script_path)
            except:
                pass
            
            # 更新结果
            result.end_time = datetime.now()
            if result.duration == 0:
                result.duration = (result.end_time - result.start_time).total_seconds()
            
            # 添加到历史记录
            with self._lock:
                self._execution_history.append(result)
                if len(self._execution_history) > self._max_history:
                    self._execution_history = self._execution_history[-self._max_history:]
                
                # 清理取消标志
                self._cancellation_flags.pop(task_id, None)
        
        return result
    
    def execute_batch(
        self,
        scripts: List[Union[str, Script]],
        script_types: Optional[List[ScriptType]] = None,
        parameters_list: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[int] = None,
        parallel: bool = False,
        max_workers: int = 4,
    ) -> List[ExecutionResult]:
        """
        批量执行脚本
        
        Args:
            scripts: 脚本列表
            script_types: 脚本类型列表
            parameters_list: 参数列表
            timeout: 超时时间
            parallel: 是否并行执行
            max_workers: 最大并行数
            
        Returns:
            List[ExecutionResult]: 执行结果列表
        """
        results = []
        
        # 规范化参数
        if script_types is None:
            script_types = [None] * len(scripts)
        if parameters_list is None:
            parameters_list = [{}] * len(scripts)
        
        if parallel:
            # 并行执行
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i, (script, script_type, params) in enumerate(zip(
                    scripts, script_types, parameters_list
                )):
                    future = executor.submit(
                        self.execute,
                        script=script,
                        script_type=script_type,
                        parameters=params,
                        timeout=timeout,
                    )
                    futures[future] = i
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # 处理异常情况
                        idx = futures[future]
                        results.append(ExecutionResult(
                            task_id=f"batch_error_{idx}",
                            script_name=f"script_{idx}",
                            script_type=ScriptType.SHELL,
                            status=ExecutionStatus.FAILED,
                            return_code=-1,
                            stdout="",
                            stderr="",
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            duration=0,
                            error_message=str(e),
                        ))
        else:
            # 串行执行
            for i, (script, script_type, params) in enumerate(zip(
                scripts, script_types, parameters_list
            )):
                result = self.execute(
                    script=script,
                    script_type=script_type,
                    parameters=params,
                    timeout=timeout,
                )
                results.append(result)
        
        return results
    
    def cancel(self, task_id: str) -> bool:
        """
        取消执行中的任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        with self._lock:
            cancel_event = self._cancellation_flags.get(task_id)
            if cancel_event:
                cancel_event.set()
                return True
        return False
    
    def get_history(
        self,
        limit: int = 100,
        status: Optional[ExecutionStatus] = None,
        host: Optional[str] = None,
    ) -> List[ExecutionResult]:
        """
        获取执行历史
        
        Args:
            limit: 返回数量限制
            status: 按状态过滤
            host: 按主机过滤
            
        Returns:
            List[ExecutionResult]: 执行结果列表
        """
        with self._lock:
            history = self._execution_history.copy()
        
        # 过滤
        if status:
            history = [r for r in history if r.status == status]
        if host:
            history = [r for r in history if r.host == host]
        
        # 返回最近的结果
        return history[-limit:]
    
    def clear_history(self):
        """清空执行历史"""
        with self._lock:
            self._execution_history.clear()
    
    def _detect_script_type(self, content: str) -> ScriptType:
        """检测脚本类型"""
        # 检查shebang
        shebang_match = re.match(r'#!\S+', content)
        if shebang_match:
            shebang = shebang_match.group(0)
            if 'python' in shebang.lower():
                return ScriptType.PYTHON
            elif 'bash' in shebang.lower():
                return ScriptType.SHELL
            elif 'powershell' in shebang.lower():
                return ScriptType.POWERSHELL
        
        # 检查内容特征
        if re.search(r'---\s*\n', content) and re.search(r'^\s*-\s+\w+:', content, re.MULTILINE):
            return ScriptType.ANSIBLE
        if re.search(r'\$PSVersionTable', content, re.IGNORECASE):
            return ScriptType.POWERSHELL
        if re.search(r'^\s*(if|for|while|function|echo)\s', content, re.MULTILINE):
            return ScriptType.SHELL
        
        return ScriptType.SHELL
    
    def _build_command(self, script: Script, script_path: str) -> List[str]:
        """构建执行命令"""
        interpreter = script.get_interpreter()
        
        if script.script_type == ScriptType.ANSIBLE:
            return [interpreter, script_path]
        elif script.script_type == ScriptType.POWERSHELL:
            return [interpreter, "-NoProfile", "-NonInteractive", "-File", script_path]
        else:
            return [interpreter, script_path]
    
    def _run_process(
        self,
        task_id: str,
        cmd: List[str],
        env: Dict[str, str],
        cwd: str,
        timeout: int,
        capture_output: bool,
        cancel_event: threading.Event,
        on_output: Optional[Callable[[str], None]],
        result: ExecutionResult,
    ) -> ExecutionResult:
        """运行进程并捕获输出"""
        stdout_buffer = []
        stderr_buffer = []
        
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = f"Failed to start process: {str(e)}"
            return result
        
        # 读取输出线程
        def read_output(pipe, buffer, is_stderr=False):
            try:
                for line in iter(pipe.readline, ''):
                    if not line:
                        break
                    buffer.append(line)
                    if on_output:
                        prefix = "[STDERR] " if is_stderr else ""
                        on_output(prefix + line)
            except:
                pass
        
        stdout_thread = None
        stderr_thread = None
        
        if capture_output:
            stdout_thread = threading.Thread(
                target=read_output,
                args=(process.stdout, stdout_buffer, False),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=read_output,
                args=(process.stderr, stderr_buffer, True),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
        
        # 等待进程完成或超时
        start_time = time.time()
        
        while True:
            # 检查是否取消
            if cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result.status = ExecutionStatus.CANCELLED
                result.error_message = "Task was cancelled by user"
                break
            
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result.status = ExecutionStatus.TIMEOUT
                result.error_message = f"Script execution timed out after {timeout} seconds"
                break
            
            # 检查进程状态
            return_code = process.poll()
            if return_code is not None:
                # 进程已结束
                if stdout_thread:
                    stdout_thread.join(timeout=2)
                if stderr_thread:
                    stderr_thread.join(timeout=2)
                
                result.return_code = return_code
                result.stdout = ''.join(stdout_buffer)
                result.stderr = ''.join(stderr_buffer)
                result.duration = time.time() - start_time
                
                if return_code == 0:
                    result.status = ExecutionStatus.SUCCESS
                else:
                    result.status = ExecutionStatus.FAILED
                    if not result.error_message:
                        result.error_message = f"Script exited with code {return_code}"
                
                break
            
            # 短暂休眠，避免CPU占用过高
            time.sleep(0.1)
        
        return result
    
    def _trigger_auto_rollback(
        self,
        task_id: str,
        script: Script,
        result: ExecutionResult,
    ) -> bool:
        """
        触发自动回滚
        
        Args:
            task_id: 任务ID
            script: 脚本对象
            result: 执行结果
            
        Returns:
            bool: 是否成功触发回滚
        """
        try:
            # 总是保存快照（无论是否启用自动回滚）
            # 这允许后续手动回滚
            snapshot = self._rollback_manager.save_checkpoint(
                execution_id=task_id,
                metadata={
                    'script_name': script.name,
                    'status': result.status.value,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.return_code,
                }
            )
            
            # 只有启用自动回滚时才执行回滚脚本
            if script.enable_auto_rollback and script.rollback_script:
                rollback_result = self._rollback_manager.execute_rollback(
                    execution_id=task_id,
                    rollback_script=script.rollback_script,
                    rollback_params={
                        'task_id': task_id,
                        'script_name': script.name,
                        'error': result.error_message,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                    }
                )
                return rollback_result.status.value == "success"
            
            return True
            
        except Exception as e:
            # 回滚失败不影响主流程
            import logging
            logging.getLogger(__name__).warning(f"Auto-rollback failed: {e}")
            return False
    
    def _create_device_config_snapshot(self, execution_id: str) -> Dict[str, Any]:
        """
        创建设备配置快照（示例实现）
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 快照数据
        """
        # 这里可以接入真实的设备配置获取逻辑
        # 目前返回示例数据
        return {
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat(),
            'device_configs': [],
            'note': 'Device config snapshot placeholder - implement with actual device config retrieval',
        }
    
    def save_checkpoint(
        self,
        execution_id: str,
        snapshot_type: str = "device_config",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        保存检查点快照
        
        Args:
            execution_id: 执行ID
            snapshot_type: 快照类型
            data: 快照数据
            metadata: 快照元数据
        """
        from .rollback import SnapshotType
        type_map = {
            'device_config': SnapshotType.DEVICE_CONFIG,
            'database_state': SnapshotType.DATABASE_STATE,
            'script_output': SnapshotType.SCRIPT_OUTPUT,
            'full_system': SnapshotType.FULL_SYSTEM,
        }
        snap_type = type_map.get(snapshot_type, SnapshotType.SCRIPT_OUTPUT)
        
        return self._rollback_manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=snap_type,
            data=data,
            metadata=metadata,
        )
    
    def get_snapshot(self, execution_id: str):
        """
        获取执行快照
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Snapshot或None
        """
        return self._rollback_manager.get_snapshot(execution_id)


class ExecutionProgress:
    """执行进度跟踪"""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.running = 0
        self.pending = 0
        self.results: List[ExecutionResult] = []
        self._lock = threading.Lock()
    
    def update(self, result: ExecutionResult):
        """更新执行结果"""
        with self._lock:
            self.results.append(result)
            self.completed += 1
            if result.status == ExecutionStatus.FAILED:
                self.failed += 1
            elif result.status == ExecutionStatus.RUNNING:
                self.running += 1
            else:
                self.pending += 1
    
    def get_progress(self) -> float:
        """获取执行进度百分比"""
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        with self._lock:
            return {
                'total': self.total,
                'completed': self.completed,
                'failed': self.failed,
                'success': self.completed - self.failed,
                'running': self.running,
                'pending': self.pending,
                'progress': self.get_progress(),
            }
