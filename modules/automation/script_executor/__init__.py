"""
AM-03 脚本执行模块

提供本地/远程脚本执行、脚本库管理、批量执行等功能
支持Shell、PowerShell、Python、Ansible等脚本类型
"""

from .executor import ScriptExecutor, ExecutionResult, ExecutionStatus
from .library import ScriptLibrary, Script, ScriptCategory, ScriptVersion
from .remote import RemoteExecutor, SSHExecutor, WinRMExecutor, BatchExecutor

__all__ = [
    'ScriptExecutor',
    'ExecutionResult', 
    'ExecutionStatus',
    'ScriptLibrary',
    'Script',
    'ScriptCategory',
    'ScriptVersion',
    'RemoteExecutor',
    'SSHExecutor',
    'WinRMExecutor',
    'BatchExecutor',
]

__version__ = '1.0.0'
