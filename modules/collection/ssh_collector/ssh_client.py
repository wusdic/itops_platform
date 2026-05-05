"""
SSH客户端模块
基于Paramiko的SSH客户端封装
"""

import io
import logging
import os
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from paramiko import SSHClient as ParamikoSSHClient
    from paramiko import SFTPClient as ParamikoSFTPClient
    from paramiko.channel import Channel as ParamikoChannel
    from paramiko.sftp_attr import SFTPAttributes as ParamikoSFTPAttributes

logger = logging.getLogger(__name__)

# Paramiko导入
try:
    import paramiko
    from paramiko import SSHClient as ParamikoSSHClient
    from paramiko import SFTPClient as ParamikoSFTPClient
    from paramiko import AutoAddPolicy
    from paramiko.channel import Channel
    from paramiko.ssh_exception import (
        SSHException, AuthenticationException, 
        NoValidConnectionsError, BadHostKeyException
    )
    _paramiko_available = True
except ImportError:
    _paramiko_available = False
    ParamikoSSHClient = object
    ParamikoSFTPClient = object


@dataclass
class SSHConfig:
    """SSH配置"""
    host: str
    port: int = 22
    username: str = 'root'
    password: Optional[str] = None
    key_file: Optional[str] = None
    key_password: Optional[str] = None
    timeout: int = 10
    banner_timeout: int = 15
    auth_timeout: int = 15
    look_for_keys: bool = True
    allow_agent: bool = True
    compress: bool = False
    # 代理配置
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    # 连接池配置
    keepalive_interval: int = 0  # 0表示禁用
    # 编码配置
    encoding: str = 'utf-8'


class SSHClient:
    """
    SSH客户端
    
    功能特性：
    1. 支持密码/密钥认证
    2. 命令执行与输出获取
    3. SFTP文件传输
    4. 会话复用（连接池）
    """
    
    def __init__(self, config: SSHConfig = None, **kwargs):
        """
        初始化SSH客户端
        
        Args:
            config: SSH配置
            **kwargs: 配置参数
        """
        if not _paramiko_available:
            raise ImportError("paramiko未安装，请执行: pip install paramiko")
        
        self._config = config or SSHConfig(**kwargs)
        self._client: Optional['ParamikoSSHClient'] = None
        self._transport = None
        self._sftp: Optional['ParamikoSFTPClient'] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        建立SSH连接
        
        Returns:
            连接是否成功
        """
        if self._connected and self._client:
            return True
        
        try:
            self._client = ParamikoSSHClient()
            
            # 设置主机密钥策略
            self._client.set_missing_host_key_policy(AutoAddPolicy())
            
            # 构建连接参数
            connect_kwargs = {
                'hostname': self._config.host,
                'port': self._config.port,
                'username': self._config.username,
                'timeout': self._config.timeout,
                'banner_timeout': self._config.banner_timeout,
                'auth_timeout': self._config.auth_timeout,
                'look_for_keys': self._config.look_for_keys,
                'allow_agent': self._config.allow_agent,
                'compress': self._config.compress
            }
            
            # 认证方式
            if self._config.password:
                connect_kwargs['password'] = self._config.password
            elif self._config.key_file:
                import paramiko
                if os.path.exists(self._config.key_file):
                    key = paramiko.RSAKey.from_private_key_file(
                        self._config.key_file,
                        password=self._config.key_password
                    )
                else:
                    key = paramiko.RSAKey.from_private_key_file(
                        io.StringIO(self._config.key_file),
                        password=self._config.key_password
                    )
                connect_kwargs['pkey'] = key
            elif self._config.key_file is None and self._config.password is None:
                # 无密码认证，使用默认密钥
                connect_kwargs['look_for_keys'] = True
            
            # 代理连接
            if self._config.proxy_host:
                proxy = ParamikoSSHClient()
                proxy.connect(
                    self._config.proxy_host,
                    self._config.proxy_port or 22,
                    username=self._config.username,
                    password=self._config.password,
                    timeout=self._config.timeout
                )
                transport = proxy.get_transport()
                dest_addr = (self._config.host, self._config.port)
                local_addr = ('127.0.0.1', 0)
                channel = transport.open_channel('direct-tcpip', dest_addr, local_addr)
                connect_kwargs['sock'] = channel
            
            # 建立连接
            self._client.connect(**connect_kwargs)
            
            # 启用keepalive
            if self._config.keepalive_interval > 0:
                self._transport = self._client.get_transport()
                self._transport.set_keepalive(self._config.keepalive_interval)
            
            self._connected = True
            logger.info(f"SSH连接成功: {self._config.username}@{self._config.host}:{self._config.port}")
            return True
            
        except AuthenticationException:
            logger.error(f"SSH认证失败: {self._config.username}@{self._config.host}")
            self._connected = False
            return False
        except socket.timeout:
            logger.error(f"SSH连接超时: {self._config.host}:{self._config.port}")
            self._connected = False
            return False
        except socket.error as e:
            logger.error(f"SSH连接错误: {self._config.host} - {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"SSH连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def execute(self, command: str, timeout: int = None, 
                block: bool = True) -> Tuple[int, str, str]:
        """
        执行命令
        
        Args:
            command: 命令
            timeout: 超时时间
            block: 是否等待执行完成
        
        Returns:
            (返回码, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        timeout = timeout or self._config.timeout
        
        try:
            # 执行命令
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout,
                get_pty=block
            )
            
            # 等待命令完成
            if block:
                exit_code = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode(self._config.encoding, errors='ignore')
                stderr_data = stderr.read().decode(self._config.encoding, errors='ignore')
                
                return exit_code, stdout_data, stderr_data
            else:
                return 0, '', ''
            
        except socket.timeout:
            return -1, '', 'Command timeout'
        except Exception as e:
            logger.error(f"命令执行失败: {command[:50]} - {e}")
            return -1, '', str(e)
    
    def execute_sudo(self, command: str, password: str = None, 
                     timeout: int = None) -> Tuple[int, str, str]:
        """
        执行sudo命令
        
        Args:
            command: 命令
            password: sudo密码（如果需要）
            timeout: 超时时间
        
        Returns:
            (返回码, stdout, stderr)
        """
        sudo_cmd = f"sudo {command}"
        
        # 如果没有提供密码且需要sudo认证
        if not password and not self._config.password:
            # 检查是否需要密码
            return self.execute(sudo_cmd, timeout)
        
        # 使用pty执行sudo命令
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        timeout = timeout or self._config.timeout
        
        try:
            channel = self._client.get_transport().open_session()
            channel.get_pty()
            channel.settimeout(timeout)
            
            channel.exec_command(sudo_cmd)
            
            # 如果需要密码，输入密码
            if password or self._config.password:
                pwd = password or self._config.password
                while True:
                    resp = channel.recv(1024).decode(self._config.encoding, errors='ignore')
                    if 'password' in resp.lower():
                        channel.send(f"{pwd}\n".encode(self._config.encoding))
                        break
                    if not resp:
                        break
            
            # 获取输出
            stdout = io.StringIO()
            stderr = io.StringIO()
            
            while True:
                if channel.exit_status_ready():
                    break
                try:
                    rl, wl, xl = select.select([channel], [], [], 0.5)
                    if rl:
                        data = channel.recv(1024)
                        if not data:
                            break
                        stdout.write(data.decode(self._config.encoding, errors='ignore'))
                except Exception:
                    break
            
            # 读取剩余输出
            while channel.recv_ready():
                stdout.write(channel.recv(1024).decode(self._config.encoding, errors='ignore'))
            
            exit_code = channel.recv_exit_status()
            channel.close()
            
            return exit_code, stdout.getvalue(), stderr.getvalue()
            
        except Exception as e:
            logger.error(f"Sudo命令执行失败: {e}")
            return -1, '', str(e)
    
    def execute_batch(self, commands: List[str], 
                      stop_on_error: bool = False) -> List[Dict[str, Any]]:
        """
        批量执行命令
        
        Args:
            commands: 命令列表
            stop_on_error: 遇到错误是否停止
        
        Returns:
            命令执行结果列表
        """
        results = []
        
        for cmd in commands:
            exit_code, stdout, stderr = self.execute(cmd)
            results.append({
                'command': cmd,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr
            })
            
            if stop_on_error and exit_code != 0:
                logger.warning(f"命令执行失败，停止批量执行: {cmd}")
                break
        
        return results
    
    def open_sftp(self) -> 'ParamikoSFTPClient':
        """
        打开SFTP会话
        
        Returns:
            SFTP客户端
        """
        if not self._connected:
            if not self.connect():
                raise Exception("Not connected")
        
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        
        return self._sftp
    
    def upload_file(self, local_path: Union[str, BinaryIO], 
                    remote_path: str, progress_callback=None) -> bool:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径或文件对象
            remote_path: 远程文件路径
            progress_callback: 进度回调函数
        
        Returns:
            是否成功
        """
        try:
            sftp = self.open_sftp()
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    # 递归创建目录
                    dirs = remote_dir.split('/')
                    for i in range(1, len(dirs) + 1):
                        dir_path = '/'.join(dirs[:i])
                        try:
                            sftp.stat(dir_path)
                        except FileNotFoundError:
                            sftp.mkdir(dir_path)
            
            # 上传文件
            if isinstance(local_path, str):
                sftp.put(local_path, remote_path, confirm=True, progress_callback=progress_callback)
            else:
                sftp.putfo(local_path, remote_path, confirm=True, progress_callback=progress_callback)
            
            logger.info(f"文件上传成功: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return False
    
    def download_file(self, remote_path: str, 
                      local_path: Union[str, BinaryIO] = None,
                      progress_callback=None) -> Optional[Union[str, io.BytesIO]]:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径，为空则返回BytesIO
            progress_callback: 进度回调函数
        
        Returns:
            下载的文件路径或BytesIO对象
        """
        try:
            sftp = self.open_sftp()
            
            if local_path is None:
                local_path = io.BytesIO()
            
            if isinstance(local_path, str):
                sftp.get(remote_path, local_path, progress_callback=progress_callback)
                logger.info(f"文件下载成功: {remote_path} -> {local_path}")
                return local_path
            else:
                sftp.getfo(remote_path, local_path, progress_callback=progress_callback)
                local_path.seek(0)
                return local_path
                
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return None
    
    def list_dir(self, remote_path: str) -> List['ParamikoSFTPAttributes']:
        """
        列出目录
        
        Args:
            remote_path: 远程目录路径
        
        Returns:
            文件属性列表
        """
        try:
            sftp = self.open_sftp()
            return sftp.listdir_attr(remote_path)
        except Exception as e:
            logger.error(f"列出目录失败: {remote_path} - {e}")
            return []
    
    def file_exists(self, remote_path: str) -> bool:
        """检查文件是否存在"""
        try:
            sftp = self.open_sftp()
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
    
    def create_dir(self, remote_path: str, mode: int = 0o755) -> bool:
        """创建目录"""
        try:
            sftp = self.open_sftp()
            sftp.mkdir(remote_path, mode)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {remote_path} - {e}")
            return False
    
    def remove_file(self, remote_path: str) -> bool:
        """删除文件"""
        try:
            sftp = self.open_sftp()
            sftp.remove(remote_path)
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {remote_path} - {e}")
            return False
    
    def remove_dir(self, remote_path: str, recursive: bool = False) -> bool:
        """删除目录"""
        try:
            sftp = self.open_sftp()
            if recursive:
                self._rmdir_recursive(sftp, remote_path)
            else:
                sftp.rmdir(remote_path)
            return True
        except Exception as e:
            logger.error(f"删除目录失败: {remote_path} - {e}")
            return False
    
    def _rmdir_recursive(self, sftp, remote_path: str):
        """递归删除目录"""
        for item in sftp.listdir(remote_path):
            item_path = f"{remote_path}/{item}"
            try:
                stat = sftp.stat(item_path)
                if stat.st_mode & 0o170000 == 0o040000:  # 目录
                    self._rmdir_recursive(sftp, item_path)
                else:
                    sftp.remove(item_path)
            except:
                pass
        sftp.rmdir(remote_path)
    
    def shell(self) -> 'ParamikoChannel':
        """
        获取交互式shell会话
        
        Returns:
            通道对象
        """
        if not self._connected:
            if not self.connect():
                raise Exception("Not connected")
        
        return self._client.invoke_shell()
    
    def close(self):
        """关闭连接"""
        if self._sftp:
            try:
                self._sftp.close()
            except:
                pass
            self._sftp = None
        
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None
        
        self._connected = False
        logger.debug(f"SSH连接已关闭: {self._config.host}")
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        if self._client:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        return False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SSHConnectionPool:
    """
    SSH连接池
    
    用于管理多个SSH连接，实现会话复用
    """
    
    def __init__(self, max_connections: int = 10, 
                 config: SSHConfig = None, **kwargs):
        """
        初始化连接池
        
        Args:
            max_connections: 最大连接数
            config: 默认配置
            **kwargs: 默认配置参数
        """
        self._max_connections = max_connections
        self._default_config = config or SSHConfig(**kwargs)
        self._pool: Dict[str, SSHClient] = {}
        self._lock = __import__('threading').RLock()
    
    def _get_pool_key(self, config: SSHConfig) -> str:
        """获取连接池键"""
        return f"{config.username}@{config.host}:{config.port}"
    
    def get_client(self, config: SSHConfig = None) -> SSHClient:
        """
        获取SSH客户端
        
        Args:
            config: 配置，为空则使用默认配置
        
        Returns:
            SSH客户端
        """
        config = config or self._default_config
        pool_key = self._get_pool_key(config)
        
        with self._lock:
            # 检查是否存在可用连接
            if pool_key in self._pool:
                client = self._pool[pool_key]
                if client.is_connected:
                    return client
                else:
                    # 连接已失效，重新连接
                    try:
                        client.close()
                    except:
                        pass
                    del self._pool[pool_key]
            
            # 检查连接数限制
            if len(self._pool) >= self._max_connections:
                # 关闭一个空闲连接
                self._close_idle_connections()
            
            # 创建新连接
            client = SSHClient(config)
            if not client.connect():
                raise Exception(f"无法连接到: {config.host}")
            
            self._pool[pool_key] = client
            return client
    
    def _close_idle_connections(self):
        """关闭空闲连接"""
        for key, client in list(self._pool.items()):
            if not client.is_connected:
                try:
                    client.close()
                except:
                    pass
                del self._pool[key]
                return
    
    def release(self, config: SSHConfig):
        """
        释放连接（放回池中）
        
        Args:
            config: 配置
        """
        # SSH连接默认保持，直接close即可
        pass
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for client in self._pool.values():
                try:
                    client.close()
                except:
                    pass
            self._pool.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()


@asynccontextmanager
async def async_ssh_client(config: SSHConfig):
    """
    异步SSH客户端上下文管理器
    
    使用示例:
        async with async_ssh_client(config) as client:
            exit_code, stdout, stderr = await client.execute_async('ls -la')
    """
    client = SSHClient(config)
    try:
        client.connect()
        yield client
    finally:
        client.close()
