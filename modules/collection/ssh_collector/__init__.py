"""
SSH采集模块
"""

from .ssh_client import SSHConfig, SSHClient, SSHConnectionPool
from .winrm_client import WinRMConfig, WinRMClient
from .collectors.linux_collector import LinuxCollector
from .collectors.windows_collector import WindowsCollector
from .collectors.kylin_collector import KylinCollector
from .config_deployer import (
    ConfigBackup,
    ConfigDeployer,
    ConfigFileManager,
    DeployTask,
    DeployResult,
    DeployStatus
)


__all__ = [
    # SSH Client
    'SSHConfig',
    'SSHClient',
    'SSHConnectionPool',
    # WinRM Client
    'WinRMConfig',
    'WinRMClient',
    # Collectors
    'LinuxCollector',
    'WindowsCollector',
    'KylinCollector',
    # Config Deployer
    'ConfigBackup',
    'ConfigDeployer',
    'ConfigFileManager',
    'DeployTask',
    'DeployResult',
    'DeployStatus'
]
