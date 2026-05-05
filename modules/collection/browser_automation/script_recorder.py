"""
浏览器脚本录制器
录制浏览器操作并生成可执行脚本
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .browser_driver import BrowserConfig, BrowserDriver, ElementSelector

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """操作类型枚举"""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    CHECK = "check"
    HOVER = "hover"
    WAIT = "wait"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    WAIT_FOR_LOAD_STATE = "wait_for_load_state"
    SCREENSHOT = "screenshot"
    UPLOAD = "upload"
    PRESS_KEY = "press_key"
    EXECUTE_SCRIPT = "execute_script"
    SLEEP = "sleep"


@dataclass
class RecordedAction:
    """录制动作"""
    action_type: ActionType
    timestamp: float
    selector: Optional[str] = None
    selector_type: str = "css"
    value: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0  # 操作耗时
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'action_type': self.action_type.value,
            'timestamp': self.timestamp,
            'selector': self.selector,
            'selector_type': self.selector_type,
            'value': self.value,
            'extra': self.extra,
            'duration': self.duration,
            'success': self.success,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordedAction':
        """从字典创建"""
        return cls(
            action_type=ActionType(data['action_type']),
            timestamp=data['timestamp'],
            selector=data.get('selector'),
            selector_type=data.get('selector_type', 'css'),
            value=data.get('value'),
            extra=data.get('extra', {}),
            duration=data.get('duration', 0),
            success=data.get('success', True),
            error=data.get('error')
        )


@dataclass
class RecordingSession:
    """录制会话"""
    id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    actions: List[RecordedAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_action(self, action: RecordedAction):
        """添加动作"""
        self.actions.append(action)
    
    def stop(self):
        """停止录制"""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """录制时长"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'actions': [a.to_dict() for a in self.actions],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordingSession':
        """从字典创建"""
        session = cls(
            id=data['id'],
            name=data['name'],
            start_time=data['start_time'],
            end_time=data.get('end_time'),
            metadata=data.get('metadata', {})
        )
        session.actions = [RecordedAction.from_dict(a) for a in data.get('actions', [])]
        return session


class ScriptRecorder:
    """
    浏览器脚本录制器
    
    功能特性：
    1. 录制浏览器操作
    2. 生成Python脚本
    3. 导出为可执行任务
    """
    
    def __init__(self, name: str = "recorded_script"):
        """
        初始化录制器
        
        Args:
            name: 录制名称
        """
        import uuid
        self.name = name
        self.session = RecordingSession(
            id=str(uuid.uuid4()),
            name=name,
            start_time=time.time()
        )
        self._driver: Optional[BrowserDriver] = None
        self._enabled = False
    
    def start_recording(self, driver: BrowserDriver):
        """
        开始录制
        
        Args:
            driver: 浏览器驱动
        """
        self._driver = driver
        self._enabled = True
        self.session = RecordingSession(
            id=str(uuid.uuid4()),
            name=self.name,
            start_time=time.time()
        )
        logger.info(f"开始录制: {self.name}")
    
    def stop_recording(self) -> RecordingSession:
        """
        停止录制
        
        Returns:
            录制会话
        """
        self._enabled = False
        self.session.stop()
        logger.info(f"停止录制: {self.name}, 共{len(self.session.actions)}个动作")
        return self.session
    
    def _record(self, action: RecordedAction):
        """记录动作"""
        if self._enabled:
            self.session.add_action(action)
    
    def record_navigate(self, url: str, success: bool = True, error: str = None):
        """录制导航操作"""
        action = RecordedAction(
            action_type=ActionType.NAVIGATE,
            timestamp=time.time(),
            value=url,
            success=success,
            error=error
        )
        self._record(action)
    
    def record_click(self, selector: ElementSelector, duration: float = 0,
                     success: bool = True, error: str = None):
        """录制点击操作"""
        action = RecordedAction(
            action_type=ActionType.CLICK,
            timestamp=time.time(),
            selector=selector.selector,
            selector_type=selector.selector_type,
            duration=duration,
            success=success,
            error=error
        )
        self._record(action)
    
    def record_fill(self, selector: ElementSelector, value: str, duration: float = 0,
                    success: bool = True, error: str = None):
        """录制填充操作"""
        action = RecordedAction(
            action_type=ActionType.FILL,
            timestamp=time.time(),
            selector=selector.selector,
            selector_type=selector.selector_type,
            value=value,
            duration=duration,
            success=success,
            error=error
        )
        self._record(action)
    
    def record_type(self, selector: ElementSelector, value: str, duration: float = 0,
                    success: bool = True, error: str = None):
        """录制输入操作"""
        action = RecordedAction(
            action_type=ActionType.TYPE,
            timestamp=time.time(),
            selector=selector.selector,
            selector_type=selector.selector_type,
            value=value,
            duration=duration,
            success=success,
            error=error
        )
        self._record(action)
    
    def record_screenshot(self, path: str, duration: float = 0,
                          success: bool = True, error: str = None):
        """录制截图操作"""
        action = RecordedAction(
            action_type=ActionType.SCREENSHOT,
            timestamp=time.time(),
            value=path,
            duration=duration,
            success=success,
            error=error
        )
        self._record(action)
    
    def record_wait(self, seconds: float, success: bool = True):
        """录制等待操作"""
        action = RecordedAction(
            action_type=ActionType.SLEEP,
            timestamp=time.time(),
            value=str(seconds),
            success=success
        )
        self._record(action)
    
    def record_action(self, action_type: ActionType, selector: str = None,
                      selector_type: str = "css", value: str = None,
                      extra: Dict[str, Any] = None, duration: float = 0,
                      success: bool = True, error: str = None):
        """录制通用操作"""
        action = RecordedAction(
            action_type=action_type,
            timestamp=time.time(),
            selector=selector,
            selector_type=selector_type,
            value=value,
            extra=extra or {},
            duration=duration,
            success=success,
            error=error
        )
        self._record(action)
    
    def generate_script(self, include_imports: bool = True, 
                        add_screenshot: bool = True) -> str:
        """
        生成Python脚本
        
        Args:
            include_imports: 是否包含导入语句
            add_screenshot: 是否添加截图代码
        
        Returns:
            Python脚本代码
        """
        lines = []
        
        if include_imports:
            lines.extend([
                '"""',
                f'自动生成的浏览器脚本: {self.session.name}',
                f'生成时间: {datetime.now().isoformat()}',
                '"""',
                '',
                'import asyncio',
                'import logging',
                'from pathlib import Path',
                '',
                'from browser_automation import BrowserDriver, BrowserConfig, ElementSelector',
                '',
                'logger = logging.getLogger(__name__)',
                ''
            ])
        
        # 脚本主体
        lines.append('async def run_script(driver: BrowserDriver):')
        
        for action in self.session.actions:
            line = self._action_to_code(action, add_screenshot)
            if line:
                lines.append(f'    {line}')
        
        lines.extend(['', '    return True', ''])
        
        # 主函数
        lines.extend([
            'async def main():',
            '    """主函数"""',
            '    logging.basicConfig(level=logging.INFO)',
            '    ',
            '    config = BrowserConfig(headless=False)',
            '    async with BrowserDriver(config) as driver:',
            '        await driver.start()',
            '        await run_script(driver)',
            '',
            '',
            "if __name__ == '__main__':",
            '    asyncio.run(main())',
        ])
        
        return '\n'.join(lines)
    
    def _action_to_code(self, action: RecordedAction, add_screenshot: bool) -> str:
        """将动作转换为代码"""
        selector = f"ElementSelector('{action.selector}', '{action.selector_type}')" if action.selector else None
        
        if action.action_type == ActionType.NAVIGATE:
            return f'await driver.navigate("{action.value}")'
        
        elif action.action_type == ActionType.CLICK:
            return f'await driver.click({selector})'
        
        elif action.action_type == ActionType.FILL:
            return f'await driver.fill({selector}, "{action.value}")'
        
        elif action.action_type == ActionType.TYPE:
            return f'await driver.type_text({selector}, "{action.value}")'
        
        elif action.action_type == ActionType.SELECT:
            return f'await driver.select_option({selector}, value="{action.value}")'
        
        elif action.action_type == ActionType.CHECK:
            checked = action.extra.get('checked', True)
            return f'await driver.check({selector}, checked={checked})'
        
        elif action.action_type == ActionType.HOVER:
            return f'await driver.hover({selector})'
        
        elif action.action_type == ActionType.PRESS_KEY:
            return f'await driver.press_key({selector}, "{action.value}")'
        
        elif action.action_type == ActionType.SCREENSHOT:
            if add_screenshot:
                return f'await driver.screenshot("{action.value}")'
            return None
        
        elif action.action_type == ActionType.WAIT_FOR_SELECTOR:
            state = action.extra.get('state', 'visible')
            return f'await driver.wait_for_selector({selector}, state="{state}")'
        
        elif action.action_type == ActionType.WAIT_FOR_LOAD_STATE:
            state = action.value or 'load'
            return f'await driver.wait_for_load_state("{state}")'
        
        elif action.action_type == ActionType.SLEEP:
            return f'await asyncio.sleep({action.value})'
        
        elif action.action_type == ActionType.EXECUTE_SCRIPT:
            return f'await driver.execute_script("""{action.value}""")'
        
        return None
    
    def save_recording(self, path: str):
        """
        保存录制会话
        
        Args:
            path: 保存路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.session.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"录制已保存: {path}")
    
    def load_recording(self, path: str):
        """
        加载录制会话
        
        Args:
            path: 加载路径
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.session = RecordingSession.from_dict(data)
        self.name = self.session.name
        logger.info(f"录制已加载: {path}")
    
    def export_script(self, path: str, include_imports: bool = True):
        """
        导出为Python脚本
        
        Args:
            path: 导出路径
            include_imports: 是否包含导入语句
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        script = self.generate_script(include_imports=include_imports)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        logger.info(f"脚本已导出: {path}")


class TaskExporter:
    """
    任务导出器
    
    将录制导出为可执行任务配置
    """
    
    @staticmethod
    def export_task_config(recording: RecordingSession,
                           output_path: str,
                           schedule: str = None,
                           device_id: str = None,
                           credentials: Dict[str, Any] = None) -> str:
        """
        导出任务配置
        
        Args:
            recording: 录制会话
            output_path: 输出路径
            schedule: 调度规则(cron格式)
            device_id: 设备ID
            credentials: 登录凭证
        
        Returns:
            配置文件路径
        """
        config = {
            'name': recording.name,
            'task_type': 'browser_automation',
            'device_id': device_id,
            'schedule': schedule,
            'script_path': f"{output_path}.py",
            'recording_path': f"{output_path}.json",
            'credentials': credentials,
            'timeout': 300,
            'retry_count': 3,
            'retry_interval': 60,
            'created_at': datetime.now().isoformat(),
            'actions_count': len(recording.actions)
        }
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        config_path = output.with_suffix('.yaml')
        import yaml
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"任务配置已导出: {config_path}")
        return str(config_path)
