"""
Windows远程管理客户端 (WinRM)
用于Windows系统的远程管理和数据采集
"""

import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# WinRM导入
try:
    import winrm
    from winrm import Session as WinRMSession
    from winrm.exceptions import WinRMError
    _winrm_available = True
except ImportError:
    _winrm_available = False
    WinRMSession = object


@dataclass
class WinRMConfig:
    """WinRM配置"""
    host: str
    username: str
    password: str
    port: int = 5985  # HTTP
    https_port: int = 5986  # HTTPS
    transport: str = 'ntlm'  # ntlm, kerberos, basic
    use_https: bool = False
    ca_trust_path: Optional[str] = None
    server_cert_validation: str = 'ignore'  # ignore, flexible, strict
    read_timeout: int = 30
    operation_timeout: int = 30
    connection_timeout: int = 10
    encoding: str = 'utf-8'


class WinRMClient:
    """
    WinRM客户端
    
    功能特性：
    1. PowerShell命令执行
    2. Windows WMI查询
    3. 批量脚本执行
    """
    
    def __init__(self, config: WinRMConfig = None, **kwargs):
        """
        初始化WinRM客户端
        
        Args:
            config: WinRM配置
            **kwargs: 配置参数
        """
        if not _winrm_available:
            # 提供备选方案：使用subprocess调用winrs
            logger.warning("winrm库未安装，将使用subprocess方式")
        
        self._config = config or WinRMConfig(**kwargs)
        self._session: Optional[WinRMSession] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        建立WinRM连接
        
        Returns:
            连接是否成功
        """
        if _winrm_available:
            return self._connect_winrm()
        else:
            return self._connect_subprocess()
    
    def _connect_winrm(self) -> bool:
        """使用winrm库连接"""
        try:
            endpoint = self._get_endpoint()
            
            self._session = WinRMSession(
                endpoint,
                auth=(self._config.username, self._config.password),
                transport=self._config.transport,
                ca_trust_path=self._config.ca_trust_path,
                server_cert_validation=self._config.server_cert_validation,
                read_timeout=self._config.read_timeout,
                operation_timeout=self._config.operation_timeout,
                connection_timeout=self._config.connection_timeout
            )
            
            # 测试连接
            result = self._session.run_cmd('echo test')
            if result.status_code == 0:
                self._connected = True
                logger.info(f"WinRM连接成功: {self._config.host}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"WinRM连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def _connect_subprocess(self) -> bool:
        """使用subprocess调用winrs"""
        try:
            # 测试连接
            cmd = self._build_winrs_command('echo test')
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                self._connected = True
                logger.info(f"WinRM连接成功: {self._config.host}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"WinRM连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def _get_endpoint(self) -> str:
        """获取WinRM端点URL"""
        if self._config.use_https:
            return f"https://{self._config.host}:{self._config.https_port}/wsman"
        else:
            return f"http://{self._config.host}:{self._config.port}/wsman"
    
    def _build_winrs_command(self, command: str) -> List[str]:
        """构建winrs命令"""
        port = self._config.https_port if self._config.use_https else self._config.port
        protocol = 'https' if self._config.use_https else 'http'
        
        cmd = [
            'winrs',
            f'-r:{protocol}://{self._config.host}:{port}',
            '-u', self._config.username,
            '-p', self._config.password,
            '-d', 'wsman',
            command
        ]
        
        return cmd
    
    def execute(self, command: str, timeout: int = None) -> Tuple[int, str, str]:
        """
        执行PowerShell命令
        
        Args:
            command: 命令或脚本
            timeout: 超时时间(秒)
        
        Returns:
            (返回码, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        timeout = timeout or self._config.read_timeout
        
        try:
            if _winrm_available and self._session:
                result = self._session.run_cmd(command, timeout=timeout)
                return result.status_code, result.std_out, result.std_err
            else:
                # 使用subprocess
                cmd = self._build_winrs_command(command)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return -1, '', 'Command timeout'
        except Exception as e:
            logger.error(f"命令执行失败: {command[:50]} - {e}")
            return -1, '', str(e)
    
    def execute_ps(self, script: str, timeout: int = None) -> Tuple[int, str, str]:
        """
        执行PowerShell脚本
        
        Args:
            script: PowerShell脚本内容
            timeout: 超时时间(秒)
        
        Returns:
            (返回码, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return -1, '', 'Not connected'
        
        # 将脚本包装为PowerShell调用
        timeout = timeout or self._config.read_timeout
        
        try:
            if _winrm_available and self._session:
                ps_script = f'''
                $ErrorActionPreference = 'Stop'
                try {{
                    {script}
                }} catch {{
                    Write-Error $_.Exception.Message
                    exit 1
                }}
                '''
                result = self._session.run_ps(ps_script, timeout=timeout)
                return result.status_code, result.std_out, result.std_err
            else:
                cmd = self._build_winrs_command(f'powershell -Command "{script}"')
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return -1, '', 'Script timeout'
        except Exception as e:
            logger.error(f"PowerShell脚本执行失败: {e}")
            return -1, '', str(e)
    
    def collect_system_info(self) -> Dict[str, Any]:
        """
        采集系统信息
        
        Returns:
            系统信息字典
        """
        script = '''
        $info = @{}
        
        # 计算机信息
        $cs = Get-CimInstance Win32_ComputerSystem
        $info.ComputerName = $cs.Name
        $info.Domain = $cs.Domain
        $info.Manufacturer = $cs.Manufacturer
        $info.Model = $cs.Model
        
        # 操作系统信息
        $os = Get-CimInstance Win32_OperatingSystem
        $info.OSName = $os.Caption
        $info.OSVersion = $os.Version
        $info.OSBuild = $os.BuildNumber
        $info.InstallDate = $os.InstallDate
        $info.LastBootTime = $os.LastBootUpTime
        
        # CPU信息
        $cpu = Get-CimInstance Win32_Processor
        $info.CPUName = $cpu.Name
        $info.CPUCores = $cpu.NumberOfCores
        $info.CPULogicalProcessors = $cpu.NumberOfLogicalProcessors
        $info.CPUMaxSpeed = $cpu.MaxClockSpeed
        
        # 内存信息
        $info.TotalMemoryGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
        $info.FreeMemoryGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
        
        $info | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                logger.warning("系统信息JSON解析失败")
                return {'raw_output': stdout}
        
        return {'error': stderr or '采集失败'}
    
    def collect_disk_info(self) -> List[Dict[str, Any]]:
        """
        采集磁盘信息
        
        Returns:
            磁盘信息列表
        """
        script = '''
        Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
            @{
                Drive = $_.DeviceID
                VolumeName = $_.VolumeName
                FileSystem = $_.FileSystem
                TotalGB = [math]::Round($_.Size / 1GB, 2)
                FreeGB = [math]::Round($_.FreeSpace / 1GB, 2)
                UsedPercent = [math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 1)
            }
        } | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("磁盘信息JSON解析失败")
                return []
        
        return []
    
    def collect_network_info(self) -> List[Dict[str, Any]]:
        """
        采集网络信息
        
        Returns:
            网络接口信息列表
        """
        script = '''
        Get-CimInstance Win32_NetworkAdapterConfiguration -Filter IPEnabled=True | ForEach-Object {
            @{
                Description = $_.Description
                MACAddress = $_.MACAddress
                IPAddress = $_.IPAddress
                SubnetMask = $_.IPSubnet
                Gateway = $_.DefaultIPGateway
                DNS = $_.DNSServerSearchOrder
                DHCPEnabled = $_.DHCPEnabled
                DHCPServer = $_.DHCPServer
            }
        } | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("网络信息JSON解析失败")
                return []
        
        return []
    
    def collect_service_info(self, service_name: str = None) -> List[Dict[str, Any]]:
        """
        采集服务信息
        
        Args:
            service_name: 服务名称，为空则获取所有服务
        
        Returns:
            服务信息列表
        """
        if service_name:
            script = f'''
            Get-Service -Name "{service_name}" | ForEach-Object {{
                @{{
                    Name = $_.Name
                    DisplayName = $_.DisplayName
                    Status = $_.Status.ToString()
                    StartType = $_.StartType.ToString()
                }}
            }} | ConvertTo-Json -Compress
            '''
        else:
            script = '''
            Get-Service | ForEach-Object {
                @{
                    Name = $_.Name
                    DisplayName = $_.DisplayName
                    Status = $_.Status.ToString()
                    StartType = $_.StartType.ToString()
                }
            } | ConvertTo-Json -Compress
            '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("服务信息JSON解析失败")
                return []
        
        return []
    
    def collect_process_info(self) -> List[Dict[str, Any]]:
        """
        采集进程信息
        
        Returns:
            进程信息列表
        """
        script = '''
        Get-Process | Select-Object -First 100 | ForEach-Object {
            @{
                Name = $_.Name
                PID = $_.Id
                CPU = [math]::Round($_.CPU, 2)
                MemoryMB = [math]::Round($_.WorkingSet64 / 1MB, 2)
                StartTime = $_.StartTime
                Path = $_.Path
            }
        } | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("进程信息JSON解析失败")
                return []
        
        return []
    
    def collect_event_log(self, log_name: str = 'System', 
                          level: str = 'Error',
                          hours: int = 24) -> List[Dict[str, Any]]:
        """
        采集事件日志
        
        Args:
            log_name: 日志名称 (System, Application, Security)
            level: 级别 (Error, Warning, Information)
            hours: 过去几小时
        
        Returns:
            事件日志列表
        """
        script = f'''
        $startTime = (Get-Date).AddHours(-{hours})
        Get-WinEvent -LogName "{log_name}" -MaxEvents 100 |
            Where-Object {{ $_.TimeCreated -gt $startTime -and $_.LevelDisplayName -eq "{level}" }} |
            ForEach-Object {{
                @{{
                    TimeCreated = $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
                    ProviderName = $_.ProviderName
                    Id = $_.Id
                    Level = $_.LevelDisplayName
                    Message = $_.Message.Substring(0, [Math]::Min(200, $_.Message.Length))
                }}
            }} | ConvertTo-Json -Compress
        '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("事件日志JSON解析失败")
                return []
        
        return []
    
    def query_wmi(self, class_name: str, 
                  properties: List[str] = None,
                  filter_expr: str = None) -> List[Dict[str, Any]]:
        """
        执行WMI查询
        
        Args:
            class_name: WMI类名
            properties: 属性列表，为空则获取所有
            filter_expr: 过滤表达式
        
        Returns:
            查询结果列表
        """
        props_str = '*' if not properties else ', '.join(properties)
        
        if filter_expr:
            script = f'''
            Get-CimInstance {class_name} -Filter "{filter_expr}" |
                Select-Object {props_str} |
                ConvertTo-Json -Compress
            '''
        else:
            script = f'''
            Get-CimInstance {class_name} |
                Select-Object {props_str} |
                ConvertTo-Json -Compress
            '''
        
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            import json
            try:
                data = json.loads(stdout)
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                logger.warning("WMI查询结果JSON解析失败")
                return []
        
        return []
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有系统信息
        
        Returns:
            完整的系统信息
        """
        data = {
            'host': self._config.host,
            'timestamp': None,
            'system': self.collect_system_info(),
            'disks': self.collect_disk_info(),
            'network': self.collect_network_info(),
            'services': self.collect_service_info(),
            'processes': self.collect_process_info()[:20],  # 限制数量
            'event_errors': self.collect_event_log('System', 'Error', 24),
            'event_warnings': self.collect_event_log('System', 'Warning', 24)
        }
        
        return data
    
    def start_service(self, service_name: str) -> Tuple[bool, str]:
        """
        启动服务
        
        Args:
            service_name: 服务名称
        
        Returns:
            (是否成功, 消息)
        """
        script = f'Start-Service -Name "{service_name}"; $true'
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            return True, f"服务 {service_name} 已启动"
        else:
            return False, stderr or "启动失败"
    
    def stop_service(self, service_name: str) -> Tuple[bool, str]:
        """
        停止服务
        
        Args:
            service_name: 服务名称
        
        Returns:
            (是否成功, 消息)
        """
        script = f'Stop-Service -Name "{service_name}" -Force; $true'
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            return True, f"服务 {service_name} 已停止"
        else:
            return False, stderr or "停止失败"
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        重启服务
        
        Args:
            service_name: 服务名称
        
        Returns:
            (是否成功, 消息)
        """
        script = f'Restart-Service -Name "{service_name}" -Force; $true'
        exit_code, stdout, stderr = self.execute_ps(script)
        
        if exit_code == 0:
            return True, f"服务 {service_name} 已重启"
        else:
            return False, stderr or "重启失败"
    
    def copy_file(self, source: str, destination: str) -> bool:
        """
        复制文件
        
        Args:
            source: 源路径
            destination: 目标路径
        
        Returns:
            是否成功
        """
        script = f'Copy-Item -Path "{source}" -Destination "{destination}" -Force'
        exit_code, stdout, stderr = self.execute_ps(script)
        
        return exit_code == 0
    
    def close(self):
        """关闭连接"""
        self._connected = False
        self._session = None
        logger.debug(f"WinRM连接已关闭: {self._config.host}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
