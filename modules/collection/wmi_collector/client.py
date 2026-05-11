"""
Async WinRM Client for Windows WMI/CIM Operations
Supports async/await operations for Windows server management
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Try importing pywinrm for async support
try:
    import winrm
    from winrm.protocol import Protocol
    _winrm_available = True
except ImportError:
    _winrm_available = False
    logger.warning("winrm module not installed. WinRM functionality unavailable.")


class WMIResultStatus(Enum):
    """WMI query result status"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    AUTH_FAILED = "auth_failed"
    CONNECTION_FAILED = "connection_failed"


@dataclass
class WinRMConfig:
    """WinRM configuration for async operations"""
    host: str
    port: int = 5985
    username: str = 'administrator'
    password: str = ''
    transport: str = 'ntlm'  # ntlm, kerberos, plaintext
    ssl: bool = False
    cacert: Optional[str] = None
    timeout: int = 30
    read_timeout: int = 60
    connect_timeout: int = 10

    def get_endpoint(self) -> str:
        """Get WinRM endpoint URL"""
        protocol = 'https' if self.ssl else 'http'
        return f'{protocol}://{self.host}:{self.port}/wsman'


@dataclass
class WMIResult:
    """WMI query result container"""
    status: WMIResultStatus
    data: Any = None
    error_message: str = ''
    execution_time: float = 0.0


@dataclass
class WMIClass:
    """WMI class reference with metadata"""
    name: str
    description: str = ''
    properties: List[str] = field(default_factory=list)


@dataclass
class WMIQueryResult:
    """WMI query execution result"""
    class_name: str
    instances: List[Dict[str, Any]] = field(default_factory=list)
    count: int = 0
    status: WMIResultStatus = WMIResultStatus.SUCCESS
    error: str = ''


class WinRMConnectionPool:
    """Connection pool for WinRM clients"""

    def __init__(self, max_connections: int = 10):
        self._max_connections = max_connections
        self._pool: Dict[str, 'WinRMClient'] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_pool_key(self, config: WinRMConfig) -> str:
        return f"{config.host}:{config.port}"

    async def get_client(self, config: WinRMConfig) -> 'WinRMClient':
        pool_key = self._get_pool_key(config)

        if pool_key not in self._locks:
            self._locks[pool_key] = asyncio.Lock()

        async with self._locks[pool_key]:
            if pool_key in self._pool:
                client = self._pool[pool_key]
                if client.is_connected():
                    return client
                else:
                    await client.connect()
                    return client

            if len(self._pool) >= self._max_connections:
                # Remove oldest connection
                oldest_key = next(iter(self._pool))
                await self._pool[oldest_key].disconnect()
                del self._pool[oldest_key]

            client = WinRMClient(config)
            await client.connect()
            self._pool[pool_key] = client
            return client

    async def release_client(self, config: WinRMConfig):
        """Release client back to pool (no-op for this simple implementation)"""
        pass

    async def close_all(self):
        """Close all connections in pool"""
        for client in self._pool.values():
            await client.disconnect()
        self._pool.clear()


class WinRMClient:
    """
    Async WinRM Client for Windows remote management

    Features:
    - Async command execution (CMD/PowerShell)
    - WMI queries via async PowerShell
    - Connection pooling
    - Timeout handling
    """

    def __init__(self, config: WinRMConfig):
        if not _winrm_available:
            raise ImportError("winrm module not installed. Install with: pip install pywinrm")

        self._config = config
        self._session = None
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = asyncio.Lock()

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected

    async def connect(self) -> bool:
        """
        Establish WinRM connection asynchronously

        Returns:
            True if connection successful
        """
        if self._connected:
            return True

        async with self._lock:
            if self._connected:
                return True

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run sync connect in executor to not block
            def _connect_sync():
                import winrm
                endpoint = self._config.get_endpoint()
                session = winrm.Session(
                    endpoint,
                    auth=(self._config.username, self._config.password),
                    transport=self._config.transport,
                    ca_trust_path=self._config.cacert,
                    timeout=self._config.timeout,
                    read_timeout=self._config.read_timeout
                )
                # Test connection
                rc, stdout, stderr = session.run_cmd('echo test')
                return rc == 0 and 'test' in stdout

            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, _connect_sync),
                    timeout=self._config.connect_timeout
                )

                if result:
                    self._connected = True
                    logger.info(f"WinRM connected: {self._config.username}@{self._config.host}:{self._config.port}")
                    return True
                else:
                    logger.error(f"WinRM connection test failed: {self._config.host}")
                    return False

            except asyncio.TimeoutError:
                logger.error(f"WinRM connection timeout: {self._config.host}")
                return False
            except Exception as e:
                logger.error(f"WinRM connection error: {self._config.host} - {e}")
                return False

    async def disconnect(self):
        """Disconnect from WinRM endpoint"""
        async with self._lock:
            self._session = None
            self._connected = False
            logger.debug(f"WinRM disconnected: {self._config.host}")

    async def execute_cmd(self, command: str, timeout: Optional[int] = None) -> tuple:
        """
        Execute CMD command asynchronously

        Args:
            command: Command to execute
            timeout: Optional timeout override

        Returns:
            (return_code, stdout, stderr)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return -1, '', 'Not connected'

        timeout = timeout or self._config.timeout

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def _run_cmd_sync():
                return self._session.run_cmd(command)

            rc, stdout, stderr = await asyncio.wait_for(
                loop.run_in_executor(None, _run_cmd_sync),
                timeout=timeout
            )
            return rc, stdout, stderr

        except asyncio.TimeoutError:
            logger.error(f"CMD execution timeout: {command[:50]}")
            return -1, '', 'Timeout'
        except Exception as e:
            logger.error(f"CMD execution error: {command[:50]} - {e}")
            return -1, '', str(e)

    async def execute_ps(self, script: str, timeout: Optional[int] = None) -> tuple:
        """
        Execute PowerShell script asynchronously

        Args:
            script: PowerShell script to execute
            timeout: Optional timeout override

        Returns:
            (return_code, stdout, stderr)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return -1, '', 'Not connected'

        timeout = timeout or self._config.timeout

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def _run_ps_sync():
                return self._session.run_ps(script)

            rc, stdout, stderr = await asyncio.wait_for(
                loop.run_in_executor(None, _run_ps_sync),
                timeout=timeout
            )
            return rc, stdout, stderr

        except asyncio.TimeoutError:
            logger.error(f"PowerShell execution timeout: {script[:50]}")
            return -1, '', 'Timeout'
        except Exception as e:
            logger.error(f"PowerShell execution error: {script[:50]} - {e}")
            return -1, '', str(e)

    async def get_wmi_class_async(self, class_name: str) -> WMIQueryResult:
        """
        Get WMI class data asynchronously

        Args:
            class_name: WMI class name (e.g., Win32_OperatingSystem)

        Returns:
            WMIQueryResult with instances
        """
        ps_script = f'''
        $items = Get-WmiObject -Class {class_name} -ErrorAction SilentlyContinue
        if ($items) {{
            $items | ForEach-Object {{
                $obj = @{{}}
                $_.PSObject.Properties | ForEach-Object {{
                    if ($_.Value -ne $null) {{
                        $obj[$_.Name] = $_.Value
                    }}
                }}
                $obj
            }} | ConvertTo-Json -Compress
        }}
        '''

        rc, stdout, stderr = await self.execute_ps(ps_script)

        if rc != 0 or not stdout.strip():
            logger.warning(f"WMI query failed: {class_name} - {stderr}")
            return WMIQueryResult(
                class_name=class_name,
                status=WMIResultStatus.ERROR,
                error=stderr or 'Query returned no data'
            )

        try:
            data = json.loads(stdout.strip())
            instances = data if isinstance(data, list) else [data]
            return WMIQueryResult(
                class_name=class_name,
                instances=instances,
                count=len(instances),
                status=WMIResultStatus.SUCCESS
            )
        except json.JSONDecodeError as e:
            logger.warning(f"WMI parse error: {class_name} - {e}")
            return WMIQueryResult(
                class_name=class_name,
                status=WMIResultStatus.ERROR,
                error=f'JSON parse error: {e}'
            )

    async def query_wql(self, wql: str) -> WMIQueryResult:
        """
        Execute WQL query asynchronously

        Args:
            wql: WQL query string

        Returns:
            WMIQueryResult with matching instances
        """
        ps_script = f'''
        $result = Get-WmiObject -Query "{wql}" -ErrorAction SilentlyContinue
        if ($result) {{
            $result | Select-Object -First 100 | ForEach-Object {{
                $obj = @{{}}
                $_.PSObject.Properties | ForEach-Object {{
                    if ($_.Value -ne $null) {{
                        $obj[$_.Name] = $_.Value
                    }}
                }}
                $obj
            }} | ConvertTo-Json -Compress
        }}
        '''

        rc, stdout, stderr = await self.execute_ps(ps_script)

        if rc != 0 or not stdout.strip():
            return WMIQueryResult(
                class_name='WQL',
                status=WMIResultStatus.ERROR,
                error=stderr or 'Query returned no data'
            )

        try:
            data = json.loads(stdout.strip())
            instances = data if isinstance(data, list) else [data]
            return WMIQueryResult(
                class_name='WQL',
                instances=instances,
                count=len(instances),
                status=WMIResultStatus.SUCCESS
            )
        except json.JSONDecodeError as e:
            return WMIQueryResult(
                class_name='WQL',
                status=WMIResultStatus.ERROR,
                error=f'JSON parse error: {e}'
            )

    async def get_system_info_async(self) -> Dict[str, Any]:
        """
        Get Windows system information asynchronously

        Returns:
            System information dictionary
        """
        info = {}

        # Run multiple queries in parallel
        tasks = [
            self.get_wmi_class_async('Win32_OperatingSystem'),
            self.get_wmi_class_async('Win32_ComputerSystem'),
            self.get_wmi_class_async('Win32_Processor'),
            self.get_wmi_class_async('Win32_BIOS'),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # OS info
        if len(results) > 0 and isinstance(results[0], WMIQueryResult):
            os_result = results[0]
            if os_result.status == WMIResultStatus.SUCCESS and os_result.instances:
                os_data = os_result.instances[0]
                info['os'] = {
                    'caption': os_data.get('Caption', ''),
                    'version': os_data.get('Version', ''),
                    'build_number': os_data.get('BuildNumber', ''),
                    'architecture': os_data.get('OSArchitecture', ''),
                    'total_memory_kb': os_data.get('TotalVisibleMemorySize', 0),
                    'free_memory_kb': os_data.get('FreePhysicalMemory', 0),
                    'cs_name': os_data.get('CSName', ''),
                }

        # Computer system info
        if len(results) > 1 and isinstance(results[1], WMIQueryResult):
            cs_result = results[1]
            if cs_result.status == WMIResultStatus.SUCCESS and cs_result.instances:
                cs_data = cs_result.instances[0]
                info['computer'] = {
                    'name': cs_data.get('Name', ''),
                    'domain': cs_data.get('Domain', ''),
                    'manufacturer': cs_data.get('Manufacturer', ''),
                    'model': cs_data.get('Model', ''),
                    'total_memory_bytes': cs_data.get('TotalPhysicalMemory', 0),
                }

        # CPU info
        if len(results) > 2 and isinstance(results[2], WMIQueryResult):
            cpu_result = results[2]
            if cpu_result.status == WMIResultStatus.SUCCESS and cpu_result.instances:
                cpu_data = cpu_result.instances[0]
                info['cpu'] = {
                    'name': cpu_data.get('Name', ''),
                    'cores': cpu_data.get('NumberOfCores', 0),
                    'logical_processors': cpu_data.get('NumberOfLogicalProcessors', 0),
                    'max_clock_speed': cpu_data.get('MaxClockSpeed', 0),
                }

        # BIOS info
        if len(results) > 3 and isinstance(results[3], WMIQueryResult):
            bios_result = results[3]
            if bios_result.status == WMIResultStatus.SUCCESS and bios_result.instances:
                bios_data = bios_result.instances[0]
                info['bios'] = {
                    'manufacturer': bios_data.get('Manufacturer', ''),
                    'version': bios_data.get('SMBIOSBIOSVersion', ''),
                    'serial': bios_data.get('SerialNumber', ''),
                }

        return info

    async def get_disk_info_async(self) -> List[Dict[str, Any]]:
        """Get disk information asynchronously"""
        result = await self.get_wmi_class_async('Win32_LogicalDisk')
        if result.status == WMIResultStatus.SUCCESS:
            return result.instances
        return []

    async def get_network_info_async(self) -> List[Dict[str, Any]]:
        """Get network configuration asynchronously"""
        result = await self.get_wmi_class_async('Win32_NetworkAdapterConfiguration')
        if result.status == WMIResultStatus.SUCCESS:
            return result.instances
        return []

    async def get_services_async(self) -> List[Dict[str, Any]]:
        """Get Windows services asynchronously"""
        result = await self.get_wmi_class_async('Win32_Service')
        if result.status == WMIResultStatus.SUCCESS:
            return result.instances
        return []

    async def get_processes_async(self) -> List[Dict[str, Any]]:
        """Get process list asynchronously"""
        result = await self.get_wmi_class_async('Win32_Process')
        if result.status == WMIResultStatus.SUCCESS:
            return result.instances
        return []

    async def collect_event_log_async(
        self,
        log_name: str = 'System',
        level: str = 'Error',
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Collect Windows event log entries asynchronously

        Args:
            log_name: Event log name (System, Application, Security)
            level: Level filter (Error, Warning, Information)
            hours: Hours to look back

        Returns:
            List of event entries
        """
        level_filter = {
            'Error': 2,
            'Warning': 3,
            'Information': 4,
        }.get(level, 2)

        ps_script = f'''
        $startTime = (Get-Date).AddHours(-{hours})
        Get-WinEvent -LogName '{log_name}' -MaxEvents 100 |
            Where-Object {{ $_.Level -le {level_filter} -and $_.TimeCreated -ge $startTime }} |
            Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message |
            ConvertTo-Json -Compress
        '''

        rc, stdout, stderr = await self.execute_ps(ps_script)

        if rc != 0 or not stdout.strip():
            logger.warning(f"Event log query failed: {log_name}")
            return []

        try:
            data = json.loads(stdout.strip())
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return []

    async def get_performance_counters_async(self, counter_path: str) -> List[Dict[str, Any]]:
        """
        Get performance counter data asynchronously

        Args:
            counter_path: Performance counter path

        Returns:
            List of counter samples
        """
        ps_script = f'''
        $counters = Get-Counter -Counter "{counter_path}" -ErrorAction SilentlyContinue
        if ($counters) {{
            $counters.CounterSamples | ForEach-Object {{
                @{{
                    Path = $_.Path
                    Value = $_.CookedValue
                    Timestamp = $_.Timestamp
                }}
            }} | ConvertTo-Json -Compress
        }}
        '''

        rc, stdout, stderr = await self.execute_ps(ps_script)

        if rc != 0 or not stdout.strip():
            return []

        try:
            data = json.loads(stdout.strip())
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return []

    async def collect_all_metrics_async(self) -> Dict[str, Any]:
        """
        Collect all monitoring metrics asynchronously

        Returns:
            Complete metrics dictionary
        """
        # Run multiple collection tasks in parallel
        tasks = {
            'system': self.get_system_info_async(),
            'disks': self.get_disk_info_async(),
            'network': self.get_network_info_async(),
            'services': self.get_services_async(),
            'processes': self.get_processes_async(),
        }

        results = await asyncio.gather(
            tasks['system'],
            tasks['disks'],
            tasks['network'],
            tasks['services'],
            tasks['processes'],
            return_exceptions=True
        )

        metrics = {
            'host': self._config.host,
            'timestamp': None,
        }

        if isinstance(results[0], dict):
            metrics['system'] = results[0]
        if isinstance(results[1], list):
            metrics['disks'] = results[1]
        if isinstance(results[2], list):
            metrics['network'] = results[2]
        if isinstance(results[3], list):
            metrics['services'] = results[3]
        if isinstance(results[4], list):
            metrics['processes'] = results[4]

        # Get performance counters
        cpu_result = await self.get_performance_counters_async(r'\Processor(_Total)\% Processor Time')
        if cpu_result:
            metrics['cpu_usage'] = cpu_result[0].get('Value', 0) if cpu_result else 0

        mem_result = await self.get_performance_counters_async(r'\Memory\% Committed Bytes In Use')
        if mem_result:
            metrics['memory_usage'] = mem_result[0].get('Value', 0) if mem_result else 0

        return metrics


# Common WMI Classes registry
WMI_CLASSES: Dict[str, WMIClass] = {
    'Win32_OperatingSystem': WMIClass(
        name='Win32_OperatingSystem',
        description='Operating system information',
        properties=['Caption', 'Version', 'BuildNumber', 'OSArchitecture', 'CSName']
    ),
    'Win32_ComputerSystem': WMIClass(
        name='Win32_ComputerSystem',
        description='Computer system information',
        properties=['Name', 'Domain', 'Manufacturer', 'Model', 'TotalPhysicalMemory']
    ),
    'Win32_Processor': WMIClass(
        name='Win32_Processor',
        description='Processor information',
        properties=['Name', 'NumberOfCores', 'NumberOfLogicalProcessors', 'MaxClockSpeed']
    ),
    'Win32_DiskDrive': WMIClass(
        name='Win32_DiskDrive',
        description='Physical disk drives',
        properties=['Model', 'Size', 'InterfaceType', 'MediaType']
    ),
    'Win32_LogicalDisk': WMIClass(
        name='Win32_LogicalDisk',
        description='Logical disks',
        properties=['DeviceID', 'Size', 'FreeSpace', 'DriveType', 'VolumeName']
    ),
    'Win32_NetworkAdapterConfiguration': WMIClass(
        name='Win32_NetworkAdapterConfiguration',
        description='Network adapter configuration',
        properties=['IPEnabled', 'MACAddress', 'IPAddress', 'DefaultIPGateway']
    ),
    'Win32_Service': WMIClass(
        name='Win32_Service',
        description='Windows services',
        properties=['Name', 'DisplayName', 'State', 'StartMode', 'PathName']
    ),
    'Win32_Process': WMIClass(
        name='Win32_Process',
        description='Running processes',
        properties=['Name', 'ProcessId', 'ExecutablePath', 'CommandLine', 'WorkingSetSize']
    ),
    'Win32_PerfFormattedData_PerfOS_Processor': WMIClass(
        name='Win32_PerfFormattedData_PerfOS_Processor',
        description='Processor performance',
        properties=['PercentProcessorTime', 'PercentUserTime', 'PercentPrivilegedTime']
    ),
    'Win32_PerfFormattedData_PerfOS_Memory': WMIClass(
        name='Win32_PerfFormattedData_PerfOS_Memory',
        description='Memory performance',
        properties=['PercentCommittedBytesInUse', 'AvailableMBytes']
    ),
}
