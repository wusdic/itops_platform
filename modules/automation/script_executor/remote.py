"""
远程执行 (remote.py)

提供SSH远程执行、WinRM远程执行、批量并行执行、执行进度跟踪等功能
"""

import json
import os
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml


class RemoteProtocol(Enum):
    """远程执行协议"""
    SSH = "ssh"
    WINRM = "winrm"
    LOCAL = "local"


class RemoteStatus(Enum):
    """远程执行状态"""
    PENDING = "pending"
    CONNECTING = "connecting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    DISCONNECTED = "disconnected"


@dataclass
class Host:
    """主机定义"""
    host_id: str
    hostname: str
    ip: str
    port: int = 22
    protocol: RemoteProtocol = RemoteProtocol.SSH
    username: str = ""
    password: str = ""
    private_key: str = ""
    private_key_path: str = ""
    sudo_password: Optional[str] = None
    timeout: int = 30
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'host_id': self.host_id,
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
            'protocol': self.protocol.value,
            'username': self.username,
            'password': '***' if self.password else '',
            'private_key': '***' if self.private_key else '',
            'private_key_path': self.private_key_path,
            'sudo_password': '***' if self.sudo_password else None,
            'timeout': self.timeout,
            'description': self.description,
            'tags': self.tags,
            'metadata': self.metadata,
        }


@dataclass
class RemoteResult:
    """远程执行结果"""
    task_id: str
    host: Host
    status: RemoteStatus
    return_code: int = -1
    stdout: str = ""
    stderr: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    error_message: str = ""
    script_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'host_id': self.host.host_id,
            'hostname': self.host.hostname,
            'ip': self.host.ip,
            'status': self.status.value,
            'return_code': self.return_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'error_message': self.error_message,
            'script_name': self.script_name,
        }


class BaseExecutor:
    """远程执行器基类"""
    
    def __init__(self, host: Host):
        self.host = host
        self._connected = False
        self._connection = None
    
    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接"""
        raise NotImplementedError
    
    def execute(
        self,
        command: str,
        timeout: int = 300,
        sudo: bool = False,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间
            sudo: 是否使用sudo执行
            capture_output: 是否捕获输出
            
        Returns:
            Tuple[int, str, str]: (返回码, stdout, stderr)
        """
        raise NotImplementedError
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> bool:
        """上传文件"""
        raise NotImplementedError
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """下载文件"""
        raise NotImplementedError
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class SSHExecutor(BaseExecutor):
    """
    SSH远程执行器
    
    基于Paramiko实现SSH远程执行
    """
    
    def __init__(self, host: Host):
        super().__init__(host)
        self._paramiko_client = None
    
    def connect(self) -> bool:
        """建立SSH连接"""
        try:
            import paramiko
            
            self._paramiko_client = paramiko.SSHClient()
            self._paramiko_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
            
            # 构建连接参数
            connect_kwargs = {
                'hostname': self.host.ip,
                'port': self.host.port,
                'username': self.host.username,
                'timeout': self.host.timeout,
            }
            
            # 认证方式
            if self.host.private_key_path:
                connect_kwargs['key_filename'] = self.host.private_key_path
            elif self.host.private_key:
                connect_kwargs['pkey'] = paramiko.RSAKey.from_private_key(
                    self.host.private_key
                )
            elif self.host.password:
                connect_kwargs['password'] = self.host.password
            
            self._paramiko_client.connect(**connect_kwargs)
            self._connected = True
            return True
            
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"SSH connection failed: {str(e)}")
    
    def disconnect(self):
        """断开SSH连接"""
        if self._paramiko_client:
            try:
                self._paramiko_client.close()
            except:
                pass
            self._paramiko_client = None
        self._connected = False
    
    def execute(
        self,
        command: str,
        timeout: int = 300,
        sudo: bool = False,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """执行命令"""
        if not self._connected:
            raise ConnectionError("Not connected")
        
        # 处理sudo
        if sudo and self.host.sudo_password:
            command = f"echo '{self.host.sudo_password}' | sudo -S {command}"
        elif sudo:
            command = f"sudo {command}"
        
        stdin, stdout, stderr = self._paramiko_client.exec_command(
            command,
            timeout=timeout,
            get_pty=capture_output and sudo,
        )
        
        # 获取输出
        stdout_data = stdout.read().decode('utf-8', errors='ignore')
        stderr_data = stderr.read().decode('utf-8', errors='ignore')
        
        # 获取返回码
        return_code = stdout.channel.recv_exit_status()
        
        return return_code, stdout_data, stderr_data
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> bool:
        """上传文件"""
        if not self._connected:
            raise ConnectionError("Not connected")
        
        try:
            sftp = self._paramiko_client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return True
        except Exception as e:
            raise IOError(f"Upload failed: {str(e)}")
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """下载文件"""
        if not self._connected:
            raise ConnectionError("Not connected")
        
        try:
            sftp = self._paramiko_client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return True
        except Exception as e:
            raise IOError(f"Download failed: {str(e)}")
    
    def execute_script(
        self,
        script_content: str,
        script_type: str = "shell",
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
        sudo: bool = False,
        working_dir: str = "/tmp",
    ) -> Tuple[int, str, str]:
        """
        执行脚本
        
        Args:
            script_content: 脚本内容
            script_type: 脚本类型 (shell, python, powershell)
            parameters: 脚本参数
            timeout: 超时时间
            sudo: 是否使用sudo
            working_dir: 工作目录
            
        Returns:
            Tuple[int, str, str]: (返回码, stdout, stderr)
        """
        # 生成临时文件名
        import tempfile
        import hashlib
        
        script_hash = hashlib.md5(script_content.encode()).hexdigest()[:8]
        extensions = {
            'shell': '.sh',
            'python': '.py',
            'powershell': '.ps1',
        }
        ext = extensions.get(script_type, '.sh')
        remote_path = f"{working_dir}/script_{script_hash}{ext}"
        
        try:
            # 上传脚本
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
                f.write(script_content)
                local_path = f.name
            
            self.upload_file(local_path, remote_path)
            
            # 添加执行权限
            chmod_cmd = f"chmod +x {remote_path}"
            self.execute(chmod_cmd, timeout=30, sudo=sudo)
            
            # 构建执行命令
            if script_type == 'python':
                cmd = f"python3 {remote_path}"
            elif script_type == 'powershell':
                cmd = f"pwsh -NoProfile -NonInteractive -File {remote_path}"
            else:
                cmd = f"/bin/bash {remote_path}"
            
            # 添加参数
            if parameters:
                param_str = ' '.join(
                    f'--{k}="{v}"' if isinstance(v, str) else f'--{k}={v}'
                    for k, v in parameters.items()
                )
                cmd = f"{cmd} {param_str}"
            
            return self.execute(cmd, timeout=timeout, sudo=sudo)
            
        finally:
            # 清理临时文件
            try:
                self.execute(f"rm -f {remote_path}", timeout=30, sudo=sudo)
            except:
                pass
            try:
                os.unlink(local_path)
            except:
                pass


class WinRMExecutor(BaseExecutor):
    """
    WinRM远程执行器
    
    基于pywinrm实现Windows远程执行
    """
    
    def __init__(self, host: Host):
        super().__init__(host)
        self._winrm_session = None
    
    def connect(self) -> bool:
        """建立WinRM连接"""
        try:
            import winrm
            
            # 构建URL
            protocol = 'http' if self.host.port == 5985 else 'https'
            url = f"{protocol}://{self.host.ip}:{self.host.port}/wsman"
            
            self._winrm_session = winrm.Session(
                url,
                auth=(
                    self.host.username,
                    self.host.password,
                ),
                transport='ntlm',
            )
            
            # 测试连接
            self._winrm_session.run_cmd('echo', ['test'])
            self._connected = True
            return True
            
        except ImportError:
            raise ImportError("pywinrm is required for WinRM execution")
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"WinRM connection failed: {str(e)}")
    
    def disconnect(self):
        """断开WinRM连接"""
        self._winrm_session = None
        self._connected = False
    
    def execute(
        self,
        command: str,
        timeout: int = 300,
        sudo: bool = False,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """执行命令"""
        if not self._connected:
            raise ConnectionError("Not connected")
        
        try:
            # WinRM不支持sudo，使用原生命令
            result = self._winrm_session.run_cmd(
                command,
                timeout=timeout,
            )
            
            return_code = result.status_code
            stdout = result.std_out.decode('utf-8', errors='ignore') if result.std_out else ""
            stderr = result.std_err.decode('utf-8', errors='ignore') if result.std_err else ""
            
            return return_code, stdout, stderr
            
        except Exception as e:
            return -1, "", str(e)
    
    def execute_ps(
        self,
        script_content: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
    ) -> Tuple[int, str, str]:
        """
        执行PowerShell脚本
        
        Args:
            script_content: PowerShell脚本内容
            parameters: 脚本参数
            timeout: 超时时间
            
        Returns:
            Tuple[int, str, str]: (返回码, stdout, stderr)
        """
        if not self._connected:
            raise ConnectionError("Not connected")
        
        try:
            import winrm
            
            # 添加参数
            ps_script = script_content
            if parameters:
                param_block = '\n'.join(
                    f'${k} = "{v}"' if isinstance(v, str) else f'${k} = {v}'
                    for k, v in parameters.items()
                )
                ps_script = f"{param_block}\n{ps_script}"
            
            ps_script = ps_script.encode('utf-16-le').decode('utf-8')
            
            result = self._winrm_session.run_ps(
                ps_script,
                timeout=timeout,
            )
            
            return_code = result.status_code
            stdout = result.std_out.decode('utf-8', errors='ignore') if result.std_out else ""
            stderr = result.std_err.decode('utf-8', errors='ignore') if result.std_err else ""
            
            return return_code, stdout, stderr
            
        except Exception as e:
            return -1, "", str(e)
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> bool:
        """上传文件"""
        try:
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # 使用base64编码传输
            import base64
            encoded = base64.b64encode(content).decode('utf-8')
            
            # PowerShell命令写入文件
            cmd = f'powershell -Command "[System.IO.File]::WriteAllBytes(\'{remote_path}\', [System.Convert]::FromBase64String(\'{encoded}\'))"'
            return_code, _, _ = self.execute(cmd)
            
            return return_code == 0
        except Exception as e:
            raise IOError(f"Upload failed: {str(e)}")
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """下载文件"""
        try:
            # 使用PowerShell读取文件并base64编码
            cmd = f'powershell -Command "[System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes(\'{remote_path}\'))"'
            return_code, stdout, stderr = self.execute(cmd)
            
            if return_code == 0:
                import base64
                content = base64.b64decode(stdout.strip())
                with open(local_path, 'wb') as f:
                    f.write(content)
                return True
            
            return False
        except Exception as e:
            raise IOError(f"Download failed: {str(e)}")


class RemoteExecutor:
    """
    远程执行管理器
    
    提供统一的远程执行接口，支持SSH和WinRM
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._executors: Dict[str, BaseExecutor] = {}
        self._lock = threading.Lock()
        
        # 默认配置
        self._default_timeout = self.config.get('default_timeout', 300)
        self._connection_timeout = self.config.get('connection_timeout', 30)
    
    def get_executor(self, host: Host) -> BaseExecutor:
        """
        获取或创建执行器
        
        Args:
            host: 主机对象
            
        Returns:
            BaseExecutor: 执行器实例
        """
        with self._lock:
            if host.host_id in self._executors:
                executor = self._executors[host.host_id]
                if executor.is_connected:
                    return executor
                else:
                    # 尝试重连
                    try:
                        executor.connect()
                        return executor
                    except:
                        pass
            
            # 创建新执行器
            if host.protocol == RemoteProtocol.SSH:
                executor = SSHExecutor(host)
            elif host.protocol == RemoteProtocol.WINRM:
                executor = WinRMExecutor(host)
            else:
                raise ValueError(f"Unsupported protocol: {host.protocol}")
            
            # 连接
            executor.connect()
            self._executors[host.host_id] = executor
            
            return executor
    
    def execute(
        self,
        host: Host,
        command: str,
        timeout: Optional[int] = None,
        sudo: bool = False,
    ) -> RemoteResult:
        """
        在远程主机执行命令
        
        Args:
            host: 主机对象
            command: 要执行的命令
            timeout: 超时时间
            sudo: 是否使用sudo
            
        Returns:
            RemoteResult: 执行结果
        """
        task_id = f"remote_{uuid.uuid4().hex[:12]}"
        timeout = timeout or self._default_timeout
        
        result = RemoteResult(
            task_id=task_id,
            host=host,
            status=RemoteStatus.RUNNING,
            start_time=datetime.now(),
        )
        
        try:
            executor = self.get_executor(host)
            return_code, stdout, stderr = executor.execute(
                command=command,
                timeout=timeout,
                sudo=sudo,
            )
            
            result.return_code = return_code
            result.stdout = stdout
            result.stderr = stderr
            result.status = RemoteStatus.SUCCESS if return_code == 0 else RemoteStatus.FAILED
            
        except Exception as e:
            result.status = RemoteStatus.FAILED
            result.error_message = str(e)
        finally:
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def execute_script(
        self,
        host: Host,
        script_content: str,
        script_type: str = "shell",
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        sudo: bool = False,
    ) -> RemoteResult:
        """
        在远程主机执行脚本
        
        Args:
            host: 主机对象
            script_content: 脚本内容
            script_type: 脚本类型
            parameters: 脚本参数
            timeout: 超时时间
            sudo: 是否使用sudo
            
        Returns:
            RemoteResult: 执行结果
        """
        task_id = f"remote_{uuid.uuid4().hex[:12]}"
        timeout = timeout or self._default_timeout
        
        result = RemoteResult(
            task_id=task_id,
            host=host,
            status=RemoteStatus.RUNNING,
            start_time=datetime.now(),
        )
        
        try:
            executor = self.get_executor(host)
            
            if isinstance(executor, WinRMExecutor):
                return_code, stdout, stderr = executor.execute_ps(
                    script_content=script_content,
                    parameters=parameters,
                    timeout=timeout,
                )
            else:
                return_code, stdout, stderr = executor.execute_script(
                    script_content=script_content,
                    script_type=script_type,
                    parameters=parameters,
                    timeout=timeout,
                    sudo=sudo,
                )
            
            result.return_code = return_code
            result.stdout = stdout
            result.stderr = stderr
            result.status = RemoteStatus.SUCCESS if return_code == 0 else RemoteStatus.FAILED
            
        except Exception as e:
            result.status = RemoteStatus.FAILED
            result.error_message = str(e)
        finally:
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def disconnect(self, host_id: str = None):
        """
        断开连接
        
        Args:
            host_id: 主机ID，为None时断开所有连接
        """
        with self._lock:
            if host_id:
                if host_id in self._executors:
                    self._executors[host_id].disconnect()
                    del self._executors[host_id]
            else:
                for executor in self._executors.values():
                    executor.disconnect()
                self._executors.clear()


class BatchExecutor:
    """
    批量并行执行器
    
    支持在多台主机上并行执行命令或脚本
    """
    
    def __init__(self, remote_executor: Optional[RemoteExecutor] = None):
        self.remote_executor = remote_executor or RemoteExecutor()
        self._progress_callbacks: List[Callable[[Dict], None]] = []
        self._cancellation_flags: Dict[str, threading.Event] = {}
    
    def add_progress_callback(self, callback: Callable[[Dict], None]):
        """添加进度回调"""
        self._progress_callbacks.append(callback)
    
    def execute_on_hosts(
        self,
        hosts: List[Host],
        command: str,
        timeout: Optional[int] = None,
        parallel: bool = True,
        max_workers: int = 10,
        on_host_result: Optional[Callable[[RemoteResult], None]] = None,
    ) -> List[RemoteResult]:
        """
        在多台主机上执行命令
        
        Args:
            hosts: 主机列表
            command: 要执行的命令
            timeout: 超时时间
            parallel: 是否并行执行
            max_workers: 最大并行数
            on_host_result: 单个主机完成回调
            
        Returns:
            List[RemoteResult]: 所有执行结果
        """
        results = []
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        if parallel:
            # 并行执行
            results = self._execute_parallel(
                batch_id=batch_id,
                hosts=hosts,
                execute_func=lambda h: self.remote_executor.execute(h, command, timeout),
                max_workers=max_workers,
                on_result=on_host_result,
            )
        else:
            # 串行执行
            for host in hosts:
                result = self._execute_single(
                    batch_id=batch_id,
                    host=host,
                    execute_func=lambda h: self.remote_executor.execute(h, command, timeout),
                    on_result=on_host_result,
                )
                results.append(result)
        
        return results
    
    def execute_scripts_on_hosts(
        self,
        hosts: List[Host],
        script_content: str,
        script_type: str = "shell",
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        parallel: bool = True,
        max_workers: int = 10,
        on_host_result: Optional[Callable[[RemoteResult], None]] = None,
    ) -> List[RemoteResult]:
        """
        在多台主机上执行脚本
        
        Args:
            hosts: 主机列表
            script_content: 脚本内容
            script_type: 脚本类型
            parameters: 脚本参数
            timeout: 超时时间
            parallel: 是否并行执行
            max_workers: 最大并行数
            on_host_result: 单个主机完成回调
            
        Returns:
            List[RemoteResult]: 所有执行结果
        """
        results = []
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        def exec_func(host):
            return self.remote_executor.execute_script(
                host, script_content, script_type, parameters, timeout
            )
        
        if parallel:
            results = self._execute_parallel(
                batch_id=batch_id,
                hosts=hosts,
                execute_func=exec_func,
                max_workers=max_workers,
                on_result=on_host_result,
            )
        else:
            for host in hosts:
                result = self._execute_single(
                    batch_id=batch_id,
                    host=host,
                    execute_func=exec_func,
                    on_result=on_host_result,
                )
                results.append(result)
        
        return results
    
    def _execute_parallel(
        self,
        batch_id: str,
        hosts: List[Host],
        execute_func: Callable,
        max_workers: int = 10,
        on_result: Optional[Callable[[RemoteResult], None]] = None,
    ) -> List[RemoteResult]:
        """并行执行"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        results_lock = threading.Lock()
        completed = 0
        total = len(hosts)
        
        def worker(host: Host) -> Tuple[Host, Any]:
            """工作函数"""
            task_id = f"{batch_id}_{host.host_id}"
            cancel_event = threading.Event()
            self._cancellation_flags[task_id] = cancel_event
            
            try:
                result = execute_func(host)
                return (host, result)
            finally:
                self._cancellation_flags.pop(task_id, None)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(worker, host): host
                for host in hosts
            }
            
            for future in as_completed(futures):
                host = futures[future]
                try:
                    _, result = future.result()
                    
                    with results_lock:
                        results.append(result)
                        completed += 1
                        
                        # 触发进度回调
                        progress = {
                            'batch_id': batch_id,
                            'total': total,
                            'completed': completed,
                            'progress': (completed / total) * 100,
                            'result': result,
                        }
                        for callback in self._progress_callbacks:
                            callback(progress)
                        
                        if on_result:
                            on_result(result)
                        
                except Exception as e:
                    # 创建失败结果
                    failed_result = RemoteResult(
                        task_id=f"{batch_id}_{host.host_id}",
                        host=host,
                        status=RemoteStatus.FAILED,
                        error_message=str(e),
                    )
                    results.append(failed_result)
                    
                    with results_lock:
                        completed += 1
                        for callback in self._progress_callbacks:
                            callback({
                                'batch_id': batch_id,
                                'total': total,
                                'completed': completed,
                                'progress': (completed / total) * 100,
                                'result': failed_result,
                            })
        
        return results
    
    def _execute_single(
        self,
        batch_id: str,
        host: Host,
        execute_func: Callable,
        on_result: Optional[Callable[[RemoteResult], None]] = None,
    ) -> RemoteResult:
        """串行执行"""
        task_id = f"{batch_id}_{host.host_id}"
        cancel_event = threading.Event()
        self._cancellation_flags[task_id] = cancel_event
        
        try:
            result = execute_func(host)
            if on_result:
                on_result(result)
            return result
        finally:
            self._cancellation_flags.pop(task_id, None)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._cancellation_flags:
            self._cancellation_flags[task_id].set()
            return True
        return False
    
    def cancel_batch(self, batch_id: str) -> int:
        """取消整个批次"""
        count = 0
        for task_id in list(self._cancellation_flags.keys()):
            if task_id.startswith(batch_id):
                if self.cancel_task(task_id):
                    count += 1
        return count


class HostManager:
    """
    主机管理器
    
    管理主机配置，支持从文件加载/保存主机列表
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self._hosts: Dict[str, Host] = {}
        self._storage_path = storage_path
        self._lock = threading.Lock()
        
        if storage_path:
            self._load_hosts()
    
    def add_host(
        self,
        hostname: str,
        ip: str,
        protocol: RemoteProtocol = RemoteProtocol.SSH,
        port: int = 22,
        username: str = "",
        password: str = "",
        private_key: str = "",
        private_key_path: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Host:
        """添加主机"""
        with self._lock:
            host_id = f"host_{uuid.uuid4().hex[:8]}"
            host = Host(
                host_id=host_id,
                hostname=hostname,
                ip=ip,
                port=port,
                protocol=protocol,
                username=username,
                password=password,
                private_key=private_key,
                private_key_path=private_key_path,
                description=description,
                tags=tags or [],
            )
            self._hosts[host_id] = host
            self._save_hosts()
            return host
    
    def get_host(self, host_id: str) -> Optional[Host]:
        """获取主机"""
        return self._hosts.get(host_id)
    
    def update_host(self, host_id: str, **kwargs) -> Optional[Host]:
        """更新主机"""
        with self._lock:
            host = self._hosts.get(host_id)
            if not host:
                return None
            
            for key, value in kwargs.items():
                if hasattr(host, key) and key != 'host_id':
                    setattr(host, key, value)
            
            self._save_hosts()
            return host
    
    def delete_host(self, host_id: str) -> bool:
        """删除主机"""
        with self._lock:
            if host_id in self._hosts:
                del self._hosts[host_id]
                self._save_hosts()
                return True
            return False
    
    def list_hosts(
        self,
        protocol: Optional[RemoteProtocol] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Host]:
        """列出主机"""
        hosts = list(self._hosts.values())
        
        if protocol:
            hosts = [h for h in hosts if h.protocol == protocol]
        if tags:
            hosts = [h for h in hosts if any(t in h.tags for t in tags)]
        
        return hosts
    
    def _load_hosts(self):
        """从文件加载主机"""
        if not self._storage_path:
            return
        
        filepath = os.path.join(self._storage_path, "hosts.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        host = Host(
                            host_id=item['host_id'],
                            hostname=item['hostname'],
                            ip=item['ip'],
                            port=item.get('port', 22),
                            protocol=RemoteProtocol(item.get('protocol', 'ssh')),
                            username=item.get('username', ''),
                            password=item.get('password', ''),
                            private_key=item.get('private_key', ''),
                            private_key_path=item.get('private_key_path', ''),
                            description=item.get('description', ''),
                            tags=item.get('tags', []),
                        )
                        self._hosts[host.host_id] = host
            except:
                pass
    
    def _save_hosts(self):
        """保存主机到文件"""
        if not self._storage_path:
            return
        
        filepath = os.path.join(self._storage_path, "hosts.json")
        data = [h.to_dict() for h in self._hosts.values()]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_hosts(self, filepath: str):
        """导出主机列表"""
        data = [h.to_dict() for h in self._hosts.values()]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_hosts(self, filepath: str, overwrite: bool = False):
        """导入主机列表"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        with self._lock:
            for item in data:
                host_id = item['host_id']
                if host_id in self._hosts and not overwrite:
                    continue
                
                host = Host(
                    host_id=host_id,
                    hostname=item['hostname'],
                    ip=item['ip'],
                    port=item.get('port', 22),
                    protocol=RemoteProtocol(item.get('protocol', 'ssh')),
                    username=item.get('username', ''),
                    password=item.get('password', ''),
                    private_key=item.get('private_key', ''),
                    private_key_path=item.get('private_key_path', ''),
                    description=item.get('description', ''),
                    tags=item.get('tags', []),
                )
                self._hosts[host_id] = host
            
            self._save_hosts()


class ExecutionProgress:
    """执行进度跟踪"""
    
    def __init__(self, batch_id: str, total: int):
        self.batch_id = batch_id
        self.total = total
        self.completed = 0
        self.succeeded = 0
        self.failed = 0
        self.running = 0
        self.pending = 0
        self.start_time = datetime.now()
        self.results: List[RemoteResult] = []
        self._lock = threading.Lock()
    
    def update(self, result: RemoteResult):
        """更新执行结果"""
        with self._lock:
            self.results.append(result)
            self.completed += 1
            
            if result.status == RemoteStatus.SUCCESS:
                self.succeeded += 1
            elif result.status == RemoteStatus.FAILED:
                self.failed += 1
            elif result.status == RemoteStatus.RUNNING:
                self.running += 1
            else:
                self.pending += 1
    
    def get_progress(self) -> float:
        """获取进度百分比"""
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        with self._lock:
            return {
                'batch_id': self.batch_id,
                'total': self.total,
                'completed': self.completed,
                'succeeded': self.succeeded,
                'failed': self.failed,
                'running': self.running,
                'pending': self.pending,
                'progress': self.get_progress(),
                'start_time': self.start_time.isoformat(),
                'duration': (datetime.now() - self.start_time).total_seconds(),
            }
    
    def get_failed_hosts(self) -> List[Dict[str, Any]]:
        """获取失败的主机"""
        return [
            r.to_dict() for r in self.results
            if r.status in (RemoteStatus.FAILED, RemoteStatus.TIMEOUT)
        ]
