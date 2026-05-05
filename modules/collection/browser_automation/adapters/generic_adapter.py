"""
通用Web设备适配器
用于适配其他厂商的网络设备和安全设备
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class GenericDeviceAdapter(BaseDeviceAdapter):
    """
    通用Web设备适配器
    
    通用的设备适配器，支持配置自定义选择器和页面导航
    """
    
    DEVICE_TYPE = "generic"
    
    def __init__(self, credential: DeviceCredential, 
                 browser_config: BrowserConfig = None,
                 custom_selectors: Dict[str, str] = None,
                 page_map: Dict[str, str] = None):
        """
        初始化通用适配器
        
        Args:
            credential: 设备凭证
            browser_config: 浏览器配置
            custom_selectors: 自定义选择器
            page_map: 页面路径映射
        """
        super().__init__(credential, browser_config)
        
        # 默认选择器
        self._selectors = {
            'username': '#username, input[name="username"], .username-input',
            'password': '#password, input[name="password"], .password-input',
            'submit': '#loginBtn, button[type="submit"], .login-btn',
            'main_content': '#mainContent, .main-content, #content',
            'data_table': 'table.data-table, .data-table, table',
            'form_submit': 'button[type="submit"], .submit-btn, .save-btn'
        }
        
        # 合并自定义选择器
        if custom_selectors:
            self._selectors.update(custom_selectors)
        
        # 页面路径映射
        self._page_map = page_map or {
            'login': '/login',
            'dashboard': '/dashboard',
            'status': '/status',
            'config': '/config',
            'interface': '/interface',
            'system': '/system'
        }
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': None,
            'dashboard': await self._collect_dashboard(),
            'system_status': await self._collect_system_status(),
            'interface_status': await self._collect_interface_status()
        }
        
        return data
    
    async def _collect_dashboard(self) -> Dict[str, Any]:
        """采集仪表盘数据"""
        try:
            await self._navigate_to_page('dashboard')
            await asyncio.sleep(1)
            
            dashboard = {}
            
            # 采集系统信息
            info_selectors = [
                '.system-info .item',
                '.info-card',
                '.dashboard-stat'
            ]
            
            for selector in info_selectors:
                items = await self._driver.find_elements(
                    ElementSelector(selector, 'css')
                )
                for item in items:
                    text = await item.text_content()
                    if text:
                        # 解析文本获取键值对
                        parts = text.split(':')
                        if len(parts) >= 2:
                            key = parts[0].strip()
                            value = ':'.join(parts[1:]).strip()
                            dashboard[key] = value
            
            return dashboard
        except Exception as e:
            logger.error(f"采集仪表盘数据失败: {e}")
        
        return {}
    
    async def _collect_system_status(self) -> Dict[str, Any]:
        """采集系统状态"""
        try:
            if await self._navigate_to_page('status'):
                await asyncio.sleep(1)
                
                status = {}
                
                # 采集CPU、内存等指标
                metric_selectors = [
                    '.metric-value',
                    '.status-value',
                    '[data-metric]'
                ]
                
                for selector in metric_selectors:
                    elements = await self._driver.find_elements(
                        ElementSelector(selector, 'css')
                    )
                    for el in elements:
                        metric = await el.get_attribute('data-metric')
                        if metric:
                            value = await el.text_content()
                            status[metric] = value
                
                return status
        except Exception as e:
            logger.error(f"采集系统状态失败: {e}")
        
        return {}
    
    async def _collect_interface_status(self) -> List[Dict[str, Any]]:
        """采集接口状态"""
        try:
            if await self._navigate_to_page('interface'):
                await asyncio.sleep(1)
                
                interfaces = []
                
                # 查找数据表格
                rows = await self._driver.find_elements(
                    ElementSelector(f'{self._selectors["data_table"]} tr', 'css')
                )
                
                for row in rows:
                    cells = await row.query_selector_all('td')
                    if cells:
                        interface = {
                            'port': await cells[0].text_content() if len(cells) > 0 else None,
                            'status': await cells[1].text_content() if len(cells) > 1 else None,
                            'speed': await cells[2].text_content() if len(cells) > 2 else None,
                            'duplex': await cells[3].text_content() if len(cells) > 3 else None
                        }
                        interfaces.append(interface)
                
                return interfaces
        except Exception as e:
            logger.error(f"采集接口状态失败: {e}")
        
        return []
    
    async def _navigate_to_page(self, page_name: str) -> bool:
        """
        导航到页面
        
        Args:
            page_name: 页面名称
        
        Returns:
            是否成功
        """
        try:
            page_path = self._page_map.get(page_name)
            if not page_path:
                logger.warning(f"未找到页面映射: {page_name}")
                return False
            
            base_url = self.credential.get_login_url().rstrip('/')
            page_url = f"{base_url}{page_path}"
            
            await self._driver.navigate(page_url)
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"导航到页面失败: {page_name} - {e}")
            return False
    
    async def collect_table_data(self, table_selector: str = None) -> List[Dict[str, Any]]:
        """
        采集表格数据
        
        Args:
            table_selector: 表格选择器
        
        Returns:
            表格数据列表
        """
        selector = table_selector or self._selectors.get('data_table', 'table')
        
        try:
            rows = await self._driver.find_elements(
                ElementSelector(f'{selector} tr', 'css')
            )
            
            if not rows:
                return []
            
            # 获取表头
            header_row = rows[0]
            headers = await header_row.query_selector_all('th, td')
            header_texts = []
            for h in headers:
                text = await h.text_content()
                header_texts.append(text.strip() if text else '')
            
            # 解析数据行
            data = []
            for row in rows[1:]:
                cells = await row.query_selector_all('td')
                if cells and len(cells) == len(headers):
                    row_data = {}
                    for i, cell in enumerate(cells):
                        text = await cell.text_content()
                        key = header_texts[i] if i < len(header_texts) else f'col_{i}'
                        row_data[key] = text.strip() if text else ''
                    data.append(row_data)
            
            return data
        except Exception as e:
            logger.error(f"采集表格数据失败: {e}")
            return []
    
    async def execute_form_action(self, form_selector: str, 
                                   form_data: Dict[str, str] = None,
                                   submit: bool = True) -> Dict[str, Any]:
        """
        执行表单操作
        
        Args:
            form_selector: 表单选择器
            form_data: 表单数据
            submit: 是否提交
        
        Returns:
            执行结果
        """
        try:
            form = await self._driver.find_element(
                ElementSelector(form_selector, 'css')
            )
            
            if not form:
                return {'success': False, 'error': 'Form not found'}
            
            # 填充表单数据
            if form_data:
                for field_name, value in form_data.items():
                    field_selector = f'{form_selector} [name="{field_name}"], {form_selector} #{field_name}'
                    await self._driver.fill(
                        ElementSelector(field_selector, 'css'),
                        value
                    )
            
            # 提交表单
            if submit:
                submit_selector = f'{form_selector} button[type="submit"]'
                await self._driver.click(
                    ElementSelector(submit_selector, 'css')
                )
                await asyncio.sleep(2)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class TopSecAdapter(GenericDeviceAdapter):
    """
    天融信设备适配器
    """
    
    DEVICE_TYPE = "topsec"
    
    DEFAULT_SELECTORS = {
        'username': '#UserName, input[name="username"]',
        'password': '#Password, input[name="password"]',
        'submit': '#btnLogin, .login-submit'
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        super().__init__(
            credential, 
            browser_config,
            custom_selectors=self.DEFAULT_SELECTORS,
            page_map={
                'login': '/login',
                'dashboard': '/main/index',
                'status': '/monitor/status',
                'firewall': '/firewall/policy',
                'system': '/system/info'
            }
        )


class NSFOCUSAdapter(GenericDeviceAdapter):
    """
    绿盟设备适配器
    """
    
    DEVICE_TYPE = "nsfocus"
    
    DEFAULT_SELECTORS = {
        'username': '#account, input[name="account"]',
        'password': '#password, input[name="password"]',
        'submit': '.login-btn, button[type="submit"]'
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        super().__init__(
            credential, 
            browser_config,
            custom_selectors=self.DEFAULT_SELECTORS,
            page_map={
                'login': '/login',
                'dashboard': '/index',
                'logs': '/log/query',
                'attack': '/attack/defense',
                'system': '/system/info'
            }
        )


class HillstoneAdapter(GenericDeviceAdapter):
    """
    山石网科设备适配器
    """
    
    DEVICE_TYPE = "hillstone"
    
    DEFAULT_SELECTORS = {
        'username': '#login-user, input[name="username"]',
        'password': '#login-pass, input[name="password"]',
        'submit': '#login-btn, .login-btn'
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        super().__init__(
            credential, 
            browser_config,
            custom_selectors=self.DEFAULT_SELECTORS,
            page_map={
                'login': '/login',
                'dashboard': '/main',
                'policy': '/firewall/policy',
                'system': '/system/status'
            }
        )


# 向后兼容别名
HillstoneAdapter = HillstoneAdapter
TopSecAdapter = TopSecAdapter
NSFOCUSAdapter = NSFOCUSAdapter
__all__ = ['GenericDeviceAdapter', 'TopSecAdapter', 'NSFOCUSAdapter', 'HillstoneAdapter']
