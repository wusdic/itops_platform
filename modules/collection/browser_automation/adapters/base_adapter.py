"""
设备适配器基类
无API设备的浏览器适配器基类
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector

logger = logging.getLogger(__name__)


@dataclass
class DeviceCredential:
    """设备凭证"""
    host: str
    username: str
    password: str
    port: int = 443
    protocol: str = "https"  # http, https
    login_url: Optional[str] = None
    login_type: str = "form"  # form, basic, digest
    
    # 元素选择器
    username_selector: str = "#username"
    password_selector: str = "#password"
    submit_selector: str = "#loginBtn"
    
    # 额外配置
    extra: Dict[str, Any] = None
    
    def get_login_url(self) -> str:
        """获取登录URL"""
        if self.login_url:
            return self.login_url
        return f"{self.protocol}://{self.host}:{self.port}"


class BaseDeviceAdapter(ABC):
    """
    设备适配器基类
    
    用于适配无API的网络设备和安全设备
    """
    
    # 设备类型
    DEVICE_TYPE: str = "generic"
    
    # 默认超时
    DEFAULT_TIMEOUT: int = 30000
    
    def __init__(self, credential: DeviceCredential, 
                 browser_config: BrowserConfig = None):
        """
        初始化适配器
        
        Args:
            credential: 设备凭证
            browser_config: 浏览器配置
        """
        self.credential = credential
        self.browser_config = browser_config or BrowserConfig(
            headless=True,
            timeout=self.DEFAULT_TIMEOUT
        )
        self._driver: Optional[BrowserDriver] = None
        self._logged_in = False
    
    async def connect(self) -> bool:
        """
        连接设备
        
        Returns:
            是否成功
        """
        self._driver = BrowserDriver(self.browser_config)
        await self._driver.start()
        
        # 导航到登录页面
        login_url = self.credential.get_login_url()
        if not await self._driver.navigate(login_url):
            logger.error(f"无法访问设备: {login_url}")
            return False
        
        # 执行登录
        return await self.login()
    
    async def disconnect(self):
        """断开连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None
        self._logged_in = False
    
    async def login(self) -> bool:
        """
        执行登录
        
        Returns:
            是否成功
        """
        username = self.credential.username
        password = self.credential.password
        
        if not username or not password:
            logger.error("用户名或密码为空")
            return False
        
        try:
            # 填充用户名
            await self._driver.fill(
                ElementSelector(self.credential.username_selector, 'css'),
                username
            )
            
            # 填充密码
            await self._driver.fill(
                ElementSelector(self.credential.password_selector, 'css'),
                password
            )
            
            # 点击登录按钮
            await self._driver.click(
                ElementSelector(self.credential.submit_selector, 'css')
            )
            
            # 等待登录完成
            await asyncio.sleep(2)
            
            self._logged_in = True
            logger.info(f"登录成功: {self.credential.host}")
            return True
            
        except Exception as e:
            logger.error(f"登录失败: {self.credential.host} - {e}")
            return False
    
    async def collect(self) -> Dict[str, Any]:
        """
        采集数据
        
        Returns:
            采集的数据
        """
        if not self._logged_in:
            return {'error': 'Not logged in'}
        
        return await self._collect_data()
    
    @abstractmethod
    async def _collect_data(self) -> Dict[str, Any]:
        """
        采集设备数据
        
        Returns:
            采集的数据
        """
        pass
    
    async def screenshot(self, path: str) -> bool:
        """
        截图
        
        Args:
            path: 保存路径
        
        Returns:
            是否成功
        """
        if not self._driver:
            return False
        
        result = await self._driver.screenshot(path)
        return result is not None
    
    async def execute_command(self, command: str) -> bool:
        """
        执行命令
        
        Args:
            command: 命令类型
        
        Returns:
            是否成功
        """
        return False
    
    async def navigate_to_menu(self, menu_path: List[str]) -> bool:
        """
        导航到菜单
        
        Args:
            menu_path: 菜单路径，如 ['系统', '配置', '网络']
        
        Returns:
            是否成功
        """
        return False
    
    @property
    def driver(self) -> Optional[BrowserDriver]:
        """获取浏览器驱动"""
        return self._driver
    
    def __enter__(self):
        asyncio.get_event_loop().run_until_complete(self.connect())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.get_event_loop().run_until_complete(self.disconnect())
