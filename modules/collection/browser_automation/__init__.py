"""
浏览器自动化模块
"""

from .browser_driver import BrowserConfig, BrowserDriver, ElementSelector, BrowserType, BrowserPool
from .script_recorder import ScriptRecorder, RecordingSession, RecordedAction, ActionType, TaskExporter
from .task_executor import Task, TaskExecutor, TaskQueue, TaskStatus, TaskPriority, TaskResult
from .adapters import (
    BaseDeviceAdapter,
    DeviceCredential,
    HuaweiDeviceAdapter,
    GenericDeviceAdapter,
    TopSecAdapter,
    NSFOCUSAdapter,
    HillstoneAdapter,
    create_adapter
)


__all__ = [
    # Browser Driver
    'BrowserConfig',
    'BrowserDriver',
    'ElementSelector',
    'BrowserType',
    'BrowserPool',
    # Script Recorder
    'ScriptRecorder',
    'RecordingSession',
    'RecordedAction',
    'ActionType',
    'TaskExporter',
    # Task Executor
    'Task',
    'TaskExecutor',
    'TaskQueue',
    'TaskStatus',
    'TaskPriority',
    'TaskResult',
    # Adapters
    'BaseDeviceAdapter',
    'DeviceCredential',
    'HuaweiDeviceAdapter',
    'GenericDeviceAdapter',
    'TopSecAdapter',
    'NSFOCUSAdapter',
    'HillstoneAdapter',
    'create_adapter'
]
