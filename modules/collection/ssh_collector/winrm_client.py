"""
WinRM客户端
支持Windows远程管理协议，用于采集Windows服务器监控数据
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import winrm
    from winrm.protocol import Protocol
    _winrm_available = True
except ImportError:
    _winrm_available = False
    logger.warning("winrm模块未安装，WinRM功能将不可用")


@dataclass
class WinRMConfig:
    """WinRM配置"""
    host: str
    port: int = 5985  # HTTP: 5985, HTTPS: 5986
    username: str = 'administrator'
    password: str = ''
    transport: str = 'ntlm'  # ntlm, kerberos, plaintext
    ssl: bool = False
    cacert: Optional[str] = None  # CA证书路径
    timeout: int = 30
    read_timeout: int = 60


class WinRMClient:
    """
    WinRM客户端
    
    用于通过WinRM协议远程管理Windows服务器。
    
    支持:
    - 执行PowerShell命令
    - 执行CMD命令
    - 获取WMI数据
    - 文件传输
    """
    
    def __init__(self, config: WinRMConfig):
        if not _winrm_available:
            raise ImportError("winrm模块未安装，请执行: pip install pywinrm")
        
        self._config = config
        self._session = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        建立WinRM连接
        
        Returns:
            连接是否成功
        """
        try:
            protocol = 'https' if self._config.ssl else 'http'
            endpoint = f'{protocol}://{self._config.host}:{self._config.port}/wsman'
            
            self._session = winrm.Session(
                endpoint,
                auth=(
                    self._config.username,
                    self._config.password
                ),
                transport=self._config.transport,
                ca_trust_path=self._config.cacert,
                timeout=self._config.timeout,
                read_timeout=self._config.read_timeout
            )
            
            # 测试连接 - 执行简单命令
            _, stdout, _ = self._session.run_cmd('echo test')
            self._connected = 'test' in stdout
            logger.info(f"WinRM连接成功: {self._config.username}@{self._config.host}:{self._config.port}")
            return self._connected
            
        except Exception as e:
            logger.error(f"WinRM连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def run_cmd(self, command: str) -> tuple:
        """
        执行CMD命令
        
        Args:
            command: 命令
            
        Returns:
            (返回码, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        try:
            rc, stdout, stderr = self._session.run_cmd(command)
            return rc, stdout, stderr
        except Exception as e:
            logger.error(f"CMD执行失败: {command[:50]} - {e}")
            return -1, '', str(e)
    
    def run_ps(self, script: str) -> tuple:
        """
        执行PowerShell命令
        
        Args:
            script: PowerShell脚本
            
        Returns:
            (返回码, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        try:
            rc, stdout, stderr = self._session.run_ps(script)
            return rc, stdout, stderr
        except Exception as e:
            logger.error(f"PowerShell执行失败: {script[:50]} - {e}")
            return -1, '', str(e)
    
    def get_wmi_class(self, class_name: str) -> List[Dict[str, Any]]:
        """
        获取WMI类数据
        
        Args:
            class_name: WMI类名 (如 Win32_OperatingSystem, Win32_Processor)
            
        Returns:
            WMI实例列表
        """
        ps_script = f'''
        $items = Get-WmiObject -Class {class_name} -ErrorAction SilentlyContinue
        $items | ForEach-Object {{
            $obj = @{{}}
            $_.PSObject.Properties | ForEach-Object {{
                if ($_.Value -ne $null) {{
                    $obj[$_.Name] = $_.Value
                }}
            }}
            $obj
        }} | ConvertTo-Json -Compress
        '''
        
        rc, stdout, stderr = self.run_ps(ps_script)
        
        if rc != 0 or not stdout.strip():
            logger.warning(f"WMI查询失败: {class_name}")
            return []
        
        try:
            import json
            data = json.loads(stdout.strip())
            # 确保返回列表
            if isinstance(data, dict):
                return [data]
            return data
        except json.JSONDecodeError:
            logger.warning(f"WMI解析失败: {class_name}")
            return []
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取Windows系统信息
        
        Returns:
            系统信息字典
        """
        info = {}
        
        # 操作系统信息
        os_info = self.get_wmi_class('Win32_OperatingSystem')
        if os_info:
            os = os_info[0]
            info['os'] = {
                'caption': os.get('Caption', ''),
                'version': os.get('Version', ''),
                'build_number': os.get('BuildNumber', ''),
                'architecture': os.get('OSArchitecture', ''),
                'total_memory': os.get('TotalVisibleMemorySize', 0),
                'free_memory': os.get('FreePhysicalMemory', 0),
                'cs_name': os.get('CSName', ''),
            }
        
        # 计算机系统信息
        cs_info = self.get_wmi_class('Win32_ComputerSystem')
        if cs_info:
            cs = cs_info[0]
            info['computer'] = {
                'name': cs.get('Name', ''),
                'domain': cs.get('Domain', ''),
                'manufacturer': cs.get('Manufacturer', ''),
                'model': cs.get('Model', ''),
                'total_memory': cs.get('TotalPhysicalMemory', 0),
            }
        
        # 处理器信息
        cpu_info = self.get_wmi_class('Win32_Processor')
        if cpu_info:
            info['cpu'] = {
                'name': cpu_info[0].get('Name', ''),
                'cores': cpu_info[0].get('NumberOfCores', 0),
                'logical_processors': cpu_info[0].get('NumberOfLogicalProcessors', 0),
                'max_clock_speed': cpu_info[0].get('MaxClockSpeed', 0),
            }
        
        # BIOS信息
        bios_info = self.get_wmi_class('Win32_BIOS')
        if bios_info:
            info['bios'] = {
                'manufacturer': bios_info[0].get('Manufacturer', ''),
                'version': bios_info[0].get('SMBIOSBIOSVersion', ''),
                'serial': bios_info[0].get('SerialNumber', ''),
            }
        
        return info
    
    def get_services(self) -> List[Dict[str, Any]]:
        """
        获取Windows服务列表
        
        Returns:
            服务列表
        """
        return self.get_wmi_class('Win32_Service')
    
    def get_processes(self) -> List[Dict[str, Any]]:
        """
        获取进程列表
        
        Returns:
            进程列表
        """
        return self.get_wmi_class('Win32_Process')
    
    def get_disk_info(self) -> List[Dict[str, Any]]:
        """
        获取磁盘信息
        
        Returns:
            磁盘信息列表
        """
        return self.get_wmi_class('Win32_LogicalDisk')
    
    def get_network_info(self) -> List[Dict[str, Any]]:
        """
        获取网络配置信息
        
        Returns:
            网络配置列表
        """
        return self.get_wmi_class('Win32_NetworkAdapterConfiguration')
    
    def get_perf_counters(self, counter_path: str) -> List[Dict[str, Any]]:
        """
        获取性能计数器数据
        
        Args:
            counter_path: 性能计数器路径 (如 \\Processor(_Total)\\% Processor Time)
            
        Returns:
            性能数据列表
        """
        ps_script = f'''
        $counters = Get-Counter -Counter "{counter_path}" -ErrorAction SilentlyContinue
        $counters.CounterSamples | ForEach-Object {{
            @{{
                Path = $_.Path
                Value = $_.CookedValue
                Timestamp = $_.Timestamp
            }}
        }} | ConvertTo-Json -Compress
        '''
        
        rc, stdout, stderr = self.run_ps(ps_script)
        
        if rc != 0 or not stdout.strip():
            return []
        
        try:
            import json
            data = json.loads(stdout.strip())
            if isinstance(data, dict):
                return [data]
            return data
        except json.JSONDecodeError:
            return []
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        采集所有监控指标
        
        Returns:
            监控指标数据
        """
        metrics = {
            'host': self._config.host,
            'timestamp': None,
        }
        
        # 系统信息
        metrics['system'] = self.get_system_info()
        
        # 性能计数器 - CPU
        cpu_counters = self.get_perf_counters(r'\Processor(_Total)\% Processor Time')
        if cpu_counters:
            metrics['cpu_usage'] = cpu_counters[0].get('Value', 0)
        
        # 性能计数器 - 内存
        mem_counters = self.get_perf_counters(r'\Memory\% Committed Bytes In Use')
        if mem_counters:
            metrics['memory_usage'] = mem_counters[0].get('Value', 0)
        
        # 磁盘信息
        metrics['disks'] = self.get_disk_info()
        
        # 网络信息
        metrics['network'] = self.get_network_info()
        
        return metrics
    
    def close(self) -> None:
        """关闭连接"""
        self._session = None
        self._connected = False
        logger.debug(f"WinRM连接已关闭: {self._config.host}")


class WMIClient:
    """
    WMI客户端（通过WinRM执行WMI查询）
    
    提供WMI查询能力，用于Windows监控。
    """
    
    def __init__(self, winrm_config: WinRMConfig):
        self._winrm = WinRMClient(winrm_config)
    
    def connect(self) -> bool:
        """建立连接"""
        return self._winrm.connect()
    
    def query(self, wql: str) -> List[Dict[str, Any]]:
        """
        执行WQL查询
        
        Args:
            wql: WQL查询语句
            
        Returns:
            查询结果列表
        """
        ps_script = f'''
        $result = Get-WmiObject -Query "{wql}" -ErrorAction SilentlyContinue
        $result | Select-Object -First 100 | ForEach-Object {{
            $obj = @{{}}
            $_.PSObject.Properties | ForEach-Object {{
                if ($_.Value -ne $null) {{
                    $obj[$_.Name] = $_.Value
                }}
            }}
            $obj
        }} | ConvertTo-Json -Complement
        '''
        
        rc, stdout, stderr = self._winrm.run_ps(ps_script)
        
        if rc != 0 or not stdout.strip():
            return []
        
        try:
            import json
            data = json.loads(stdout.strip())
            if isinstance(data, dict):
                return [data]
            return data
        except json.JSONDecodeError:
            return []
    
    def close(self) -> None:
        """关闭连接"""
        self._winrm.close()


# 常用WMI类
WMI_CLASSES = {
    # 操作系统
    'Win32_OperatingSystem': '操作系统信息',
    'Win32_ComputerSystem': '计算机系统信息',
    'Win32_BIOS': 'BIOS信息',
    'Win32_TimeZone': '时区设置',
    'Win32_WindowsProductActivation': 'Windows激活状态',
    
    # 硬件
    'Win32_Processor': '处理器信息',
    'Win32_PhysicalMemory': '物理内存',
    'Win32_DiskDrive': '磁盘驱动器',
    'Win32_LogicalDisk': '逻辑磁盘',
    'Win32_NetworkAdapter': '网络适配器',
    'Win32_NetworkAdapterConfiguration': '网络配置',
    
    # 软件
    'Win32_InstalledWin32Program': '已安装程序',
    'Win32_SoftwareFeature': '软件特性',
    
    # 服务和进程
    'Win32_Service': '服务信息',
    'Win32_Process': '进程信息',
    'Win32_Thread': '线程信息',
    
    # 事件
    'Win32_NtLogEvent': 'NT日志事件',
    'Win32_OperatingSystem': '操作系统',
    
    # 性能
    'Win32_PerfFormattedData_PerfOS_Processor': '处理器性能',
    'Win32_PerfFormattedData_PerfOS_Memory': '内存性能',
    'Win32_PerfFormattedData_PerfDisk_PhysicalDisk': '磁盘性能',
}
