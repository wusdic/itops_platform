# -*- coding: utf-8 -*-
"""
ITOps Platform - SSH Collector
SSH协议数据采集
"""
import asyncio
from typing import Any, Dict, Optional
from paramiko import SSHClient, AutoAddKey
from core.log import get_logger

logger = get_logger(__name__)


class SSHCollector:
    """SSH采集器"""
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: str = None,
        key_file: str = None,
        timeout: int = 30
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.timeout = timeout
        self._client: Optional[SSHClient] = None
    
    async def connect(self) -> bool:
        """建立SSH连接"""
        loop = asyncio.get_event_loop()
        
        def sync_connect():
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddKey())
            
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": self.timeout,
            }
            
            if self.key_file:
                connect_kwargs["key_filename"] = self.key_file
            else:
                connect_kwargs["password"] = self.password
            
            client.connect(**connect_kwargs)
            return client
        
        try:
            self._client = await loop.run_in_executor(None, sync_connect)
            return True
        except Exception as e:
            logger.error(f"SSH连接失败 {self.host}: {e}")
            return False
    
    async def execute(self, command: str) -> Dict[str, Any]:
        """执行命令"""
        if not self._client:
            await self.connect()
        
        loop = asyncio.get_event_loop()
        
        def sync_execute():
            stdin, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='ignore')
            stderr_data = stderr.read().decode('utf-8', errors='ignore')
            
            return {
                "exit_code": exit_code,
                "stdout": stdout_data,
                "stderr": stderr_data,
            }
        
        return await loop.run_in_executor(None, sync_execute)
    
    async def collect(self, commands: Dict[str, str]) -> Dict[str, Any]:
        """批量执行命令采集"""
        results = {}
        
        for name, command in commands.items():
            try:
                result = await self.execute(command)
                results[name] = result
            except Exception as e:
                logger.error(f"SSH命令执行失败 {self.host}/{name}: {e}")
                results[name] = {"error": str(e)}
        
        return results
    
    async def collect_cpu(self) -> Dict[str, Any]:
        """采集CPU信息"""
        commands = {
            "usage": "top -bn1 | head -5",
            "load": "uptime",
            "cores": "nproc",
        }
        return await self.collect(commands)
    
    async def collect_memory(self) -> Dict[str, Any]:
        """采集内存信息"""
        commands = {
            "memory": "free -m",
        }
        return await self.collect(commands)
    
    async def collect_disk(self) -> Dict[str, Any]:
        """采集磁盘信息"""
        commands = {
            "disk": "df -h",
            "usage": "iostat -x 1 1",
        }
        return await self.collect(commands)
    
    async def collect_network(self) -> Dict[str, Any]:
        """采集网络信息"""
        commands = {
            "interfaces": "ip addr show",
            "routes": "ip route show",
            "connections": "netstat -an",
        }
        return await self.collect(commands)
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = await self.execute("echo test")
            return result.get("exit_code") == 0
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
