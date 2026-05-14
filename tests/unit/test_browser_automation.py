"""
浏览器自动化单元测试
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.collection.browser_automation.browser_driver import (
    BrowserConfig, BrowserDriver, ElementSelector, BrowserType
)
from modules.collection.browser_automation.script_recorder import (
    ScriptRecorder, RecordingSession, RecordedAction, ActionType
)
from modules.collection.browser_automation.adapters import (
    DeviceCredential, HuaweiDeviceAdapter, GenericDeviceAdapter, create_adapter
)


class TestBrowserConfig(unittest.TestCase):
    """浏览器配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = BrowserConfig()
        
        self.assertEqual(config.browser_type, BrowserType.CHROMIUM)
        self.assertTrue(config.headless)
        self.assertEqual(config.timeout, 30000)
        self.assertEqual(config.viewport_width, 1920)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BrowserConfig(
            browser_type=BrowserType.FIREFOX,
            headless=False,
            viewport_width=1280,
            viewport_height=720
        )
        
        self.assertEqual(config.browser_type, BrowserType.FIREFOX)
        self.assertFalse(config.headless)
        self.assertEqual(config.viewport_width, 1280)
        self.assertEqual(config.viewport_height, 720)


class TestElementSelector(unittest.TestCase):
    """元素选择器测试"""
    
    def test_css_selector(self):
        """CSS选择器"""
        selector = ElementSelector('#username', 'css')
        self.assertEqual(selector.selector, '#username')
        self.assertEqual(selector.selector_type, 'css')
        self.assertEqual(selector.to_playwright(), '#username')
    
    def test_xpath_selector(self):
        """XPath选择器"""
        selector = ElementSelector('//div[@id="login"]', 'xpath')
        self.assertEqual(selector.to_playwright(), 'xpath=//div[@id="login"]')
    
    def test_text_selector(self):
        """文本选择器"""
        selector = ElementSelector('登录', 'text')
        self.assertEqual(selector.to_playwright(), 'text=登录')
    
    def test_id_selector(self):
        """ID选择器"""
        selector = ElementSelector('password', 'id')
        self.assertEqual(selector.to_playwright(), '#password')


class TestRecordingSession(unittest.TestCase):
    """录制会话测试"""
    
    def test_session_creation(self):
        """测试会话创建"""
        session = RecordingSession(
            id='test-id',
            name='Test Session',
            start_time=1234567890.0
        )
        
        self.assertEqual(session.id, 'test-id')
        self.assertEqual(session.name, 'Test Session')
        self.assertEqual(len(session.actions), 0)
    
    def test_add_action(self):
        """测试添加动作"""
        session = RecordingSession(
            id='test-id',
            name='Test Session',
            start_time=1234567890.0
        )
        
        action = RecordedAction(
            action_type=ActionType.CLICK,
            timestamp=1234567891.0,
            selector='#button',
            selector_type='css'
        )
        
        session.add_action(action)
        self.assertEqual(len(session.actions), 1)
    
    def test_session_duration(self):
        """测试会话时长"""
        session = RecordingSession(
            id='test-id',
            name='Test Session',
            start_time=1000.0
        )
        
        session.end_time = 2000.0
        self.assertEqual(session.duration, 1000.0)


class TestRecordedAction(unittest.TestCase):
    """录制动作测试"""
    
    def test_action_to_dict(self):
        """测试动作转字典"""
        action = RecordedAction(
            action_type=ActionType.NAVIGATE,
            timestamp=1234567890.0,
            value='https://example.com',
            success=True
        )
        
        data = action.to_dict()
        
        self.assertEqual(data['action_type'], 'navigate')
        self.assertEqual(data['value'], 'https://example.com')
        self.assertTrue(data['success'])
    
    def test_action_from_dict(self):
        """测试从字典创建动作"""
        data = {
            'action_type': 'click',
            'timestamp': 1234567890.0,
            'selector': '#button',
            'selector_type': 'css',
            'value': None,
            'extra': {},
            'duration': 0.5,
            'success': True,
            'error': None
        }
        
        action = RecordedAction.from_dict(data)
        
        self.assertEqual(action.action_type, ActionType.CLICK)
        self.assertEqual(action.selector, '#button')
        self.assertTrue(action.success)


class TestScriptRecorder(unittest.TestCase):
    """脚本录制器测试"""
    
    def setUp(self):
        """设置测试"""
        self.recorder = ScriptRecorder('test_script')
    
    def test_recorder_initialization(self):
        """测试录制器初始化"""
        self.assertEqual(self.recorder.name, 'test_script')
        self.assertIsNotNone(self.recorder.session)
        self.assertEqual(self.recorder.session.name, 'test_script')
    
    def test_record_navigate(self):
        """测试录制导航"""
        self.recorder.record_navigate('https://example.com')
        
        self.assertEqual(len(self.recorder.session.actions), 1)
        action = self.recorder.session.actions[0]
        self.assertEqual(action.action_type, ActionType.NAVIGATE)
        self.assertEqual(action.value, 'https://example.com')
    
    def test_record_click(self):
        """测试录制点击"""
        selector = ElementSelector('#button', 'css')
        self.recorder.record_click(selector, duration=0.3)
        
        self.assertEqual(len(self.recorder.session.actions), 1)
        action = self.recorder.session.actions[0]
        self.assertEqual(action.action_type, ActionType.CLICK)
        self.assertEqual(action.selector, '#button')
        self.assertEqual(action.duration, 0.3)
    
    def test_generate_script(self):
        """测试生成脚本"""
        self.recorder.record_navigate('https://example.com')
        
        selector = ElementSelector('#username', 'css')
        self.recorder.record_fill(selector, 'admin')
        
        script = self.recorder.generate_script()
        
        self.assertIn('navigate', script)
        self.assertIn('example.com', script)
        self.assertIn('fill', script)
        self.assertIn('admin', script)
    
    def test_generate_script_code_conversion(self):
        """测试动作到代码转换"""
        self.recorder.record_navigate('https://example.com')
        
        script = self.recorder.generate_script(include_imports=False)
        lines = script.strip().split('\n')
        
        # 检查是否包含导航代码
        navigate_found = any('navigate' in line for line in lines)
        self.assertTrue(navigate_found)


class TestDeviceCredential(unittest.TestCase):
    """设备凭证测试"""
    
    def test_credential_creation(self):
        """测试凭证创建"""
        credential = DeviceCredential(
            host='192.168.1.1',
            port=443,
            username='admin',
            password='password',
            protocol='https'
        )
        
        self.assertEqual(credential.host, '192.168.1.1')
        self.assertEqual(credential.port, 443)
        self.assertEqual(credential.username, 'admin')
    
    def test_get_login_url(self):
        """测试获取登录URL"""
        credential = DeviceCredential(
            host='192.168.1.1',
            username='admin',
            password='secret',
            port=443,
            protocol='https'
        )
        
        self.assertEqual(credential.get_login_url(), 'https://192.168.1.1:443')
        
        credential.login_url = 'https://192.168.1.1:443/custom_login'
        self.assertEqual(credential.get_login_url(), 'https://192.168.1.1:443/custom_login')


class TestAdapterFactory(unittest.TestCase):
    """适配器工厂测试"""
    
    def test_create_huawei_adapter(self):
        """测试创建华为适配器"""
        credential = DeviceCredential(
            host='192.168.1.1',
            username='admin',
            password='password'
        )
        
        adapter = create_adapter('huawei', credential)
        
        self.assertIsInstance(adapter, HuaweiDeviceAdapter)
        self.assertEqual(adapter.DEVICE_TYPE, 'huawei')
    
    def test_create_generic_adapter(self):
        """测试创建通用适配器"""
        credential = DeviceCredential(
            host='192.168.1.1',
            username='admin',
            password='password'
        )
        
        adapter = create_adapter('generic', credential)
        
        self.assertIsInstance(adapter, GenericDeviceAdapter)
    
    def test_invalid_device_type(self):
        """测试无效设备类型"""
        credential = DeviceCredential(
            host='192.168.1.1',
            username='admin',
            password='password'
        )
        
        with self.assertRaises(ValueError):
            create_adapter('invalid', credential)


class TestBrowserAutomationAsync(unittest.IsolatedAsyncioTestCase):
    """浏览器自动化异步测试"""
    
    @patch('modules.collection.browser_automation.browser_driver._playwright_available', True)
    @patch('modules.collection.browser_automation.browser_driver.async_playwright')
    async def test_browser_start(self, mock_playwright):
        """测试浏览器启动"""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        mock_playwright_instance = AsyncMock()
        type(mock_playwright_instance).chromium = PropertyMock(return_value=mock_browser)
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        
        config = BrowserConfig()
        driver = BrowserDriver(config)
        
        await driver.start()
        
        self.assertIsNotNone(driver._browser)
        self.assertIsNotNone(driver._context)
        self.assertIsNotNone(driver._page)
    
    @patch('modules.collection.browser_automation.browser_driver._playwright_available', True)
    @patch('modules.collection.browser_automation.browser_driver.async_playwright')
    async def test_navigate(self, mock_playwright):
        """测试页面导航"""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        # 直接给 driver 的内部属性赋值，跳过复杂的 playwright mock 链
        config = BrowserConfig()
        driver = BrowserDriver(config)
        driver._browser = mock_browser
        driver._context = mock_context
        driver._page = mock_page

        result = await driver.navigate('https://example.com')

        self.assertTrue(result)
        mock_page.goto.assert_called_once()
        # 检查 URL 正确（timeout 等参数可能有默认值差异）
        call_args = mock_page.goto.call_args
        self.assertEqual(call_args[0][0], 'https://example.com')


class TestTaskExecutor(unittest.TestCase):
    """任务执行器测试（基础功能）"""
    
    def test_task_creation(self):
        """测试任务创建"""
        from modules.collection.browser_automation.task_executor import Task, TaskPriority
        
        task = Task(
            id='test-task',
            name='Test Task',
            script_path='/tmp/test.py',
            priority=TaskPriority.HIGH
        )
        
        self.assertEqual(task.id, 'test-task')
        self.assertEqual(task.name, 'Test Task')
        self.assertEqual(task.priority, TaskPriority.HIGH)
    
    def test_task_to_dict(self):
        """测试任务转字典"""
        from modules.collection.browser_automation.task_executor import Task
        
        task = Task(
            id='test-task',
            name='Test Task',
            script_path='/tmp/test.py'
        )
        
        data = task.to_dict()
        
        self.assertEqual(data['id'], 'test-task')
        self.assertEqual(data['name'], 'Test Task')
        self.assertEqual(data['script_path'], '/tmp/test.py')


if __name__ == '__main__':
    unittest.main()
