"""
Windows系统信息采集器
"""

import logging
from typing import Any, Dict, List

from ..winrm_client import WinRMClient, WinRMConfig

logger = logging.getLogger(__name__)


class WindowsCollector:
    """
    Windows系统信息采集器
    
    通过WinRM采集Windows系统信息
    """
    
    def __init__(self, client: WinRMClient):
        """
        初始化采集器
        
        Args:
            client: WinRM客户端
        """
        self._client = client
    
    def collect_system_info(self) -> Dict[str, Any]:
        """
        采集系统信息
        
        Returns:
            系统信息字典
        """
        return self._client.collect_system_info()
    
    def collect_disk_info(self) -> List[Dict[str, Any]]:
        """
        采集磁盘信息
        
        Returns:
            磁盘信息列表
        """
        return self._client.collect_disk_info()
    
    def collect_network_info(self) -> List[Dict[str, Any]]:
        """
        采集网络信息
        
        Returns:
            网络信息列表
        """
        return self._client.collect_network_info()
    
    def collect_service_info(self, service_name: str = None) -> List[Dict[str, Any]]:
        """
        采集服务信息
        
        Args:
            service_name: 服务名称，为空则获取所有
        
        Returns:
            服务信息列表
        """
        return self._client.collect_service_info(service_name)
    
    def collect_process_info(self) -> List[Dict[str, Any]]:
        """
        采集进程信息
        
        Returns:
            进程信息列表
        """
        return self._client.collect_process_info()
    
    def collect_event_log(self, log_name: str = 'System',
                          level: str = 'Error',
                          hours: int = 24) -> List[Dict[str, Any]]:
        """
        采集事件日志
        
        Args:
            log_name: 日志名称
            level: 级别
            hours: 时间范围
        
        Returns:
            事件日志列表
        """
        return self._client.collect_event_log(log_name, level, hours)
    
    def collect_installed_software(self) -> List[Dict[str, Any]]:
        """
        采集已安装软件列表
        
        Returns:
            软件列表
        """
        script = '''
        Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* |
            Where-Object { $_.DisplayName } |
            Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
            ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self._client.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("软件列表JSON解析失败")
                return []
        
        return []
    
    def collect_updates(self) -> List[Dict[str, Any]]:
        """
        采集已安装更新
        
        Returns:
            更新列表
        """
        script = '''
        Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy |
            ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self._client.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("更新列表JSON解析失败")
                return []
        
        return []
    
    def collect_performance(self) -> Dict[str, Any]:
        """
        采集性能计数器
        
        Returns:
            性能数据
        """
        script = '''
        $counters = @{}
        
        # CPU使用率
        $cpu = Get-Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1
        $counters.CPUUsage = [math]::Round($cpu.CounterSamples[0].CookedValue, 2)
        
        # 内存使用率
        $mem = Get-Counter '\\Memory\\% Committed Bytes In Use' -SampleInterval 1 -MaxSamples 1
        $counters.MemoryUsage = [math]::Round($mem.CounterSamples[0].CookedValue, 2)
        
        # 磁盘使用率
        $disk = Get-Counter '\\LogicalDisk(C:)\\% Free Space' -SampleInterval 1 -MaxSamples 1
        $counters.DiskUsage = [math]::Round(100 - $disk.CounterSamples[0].CookedValue, 2)
        
        # 网络接口
        $net = Get-Counter '\\Network Interface(*)\\Bytes Total/sec' -SampleInterval 1 -MaxSamples 1
        $counters.NetworkBytesPerSec = $net.CounterSamples[0].CookedValue
        
        $counters | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self._client.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                logger.warning("性能数据JSON解析失败")
                return {}
        
        return {}
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有系统信息
        
        Returns:
            完整的系统信息
        """
        data = {
            'host': self._client._config.host,
            'timestamp': None,
            'system': self.collect_system_info(),
            'disks': self.collect_disk_info(),
            'network': self.collect_network_info(),
            'services': self.collect_service_info(),
            'processes': self.collect_process_info(),
            'event_errors': self.collect_event_log('System', 'Error', 24),
            'event_warnings': self.collect_event_log('System', 'Warning', 24),
            'software': self.collect_installed_software()[:50],  # 限制数量
            'updates': self.collect_updates()[:50],  # 限制数量
            'performance': self.collect_performance()
        }
        
        return data
