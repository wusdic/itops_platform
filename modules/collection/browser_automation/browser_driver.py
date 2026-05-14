"""
浏览器驱动模块
基于Playwright的浏览器自动化封装
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import ElementHandle, Browser, BrowserContext, Page
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
else:
    ElementHandle = None
    Browser = None
    BrowserContext = None
    Page = None
    PlaywrightTimeoutError = Exception

# Playwright导入
try:
    from playwright.async_api import async_playwright as _async_playwright
    from playwright.sync_api import sync_playwright as _sync_playwright
    _playwright_available = True
except ImportError:
    _async_playwright = None
    _sync_playwright = None
    _playwright_available = False

# 确保模块级别可访问，以便测试mock
async_playwright = _async_playwright
sync_playwright = _sync_playwright

logger = logging.getLogger(__name__)


class BrowserType(str):
    """浏览器类型"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class WaitStrategy:
    """元素等待策略"""
    ATTACHED = "attached"      # 元素存在于DOM
    DETACHED = "detached"      # 元素从DOM移除
    VISIBLE = "visible"        # 元素可见
    HIDDEN = "hidden"          # 元素隐藏
    NONE = None                # 不等待


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: str = BrowserType.CHROMIUM
    headless: bool = True
    slow_mo: int = 0           # 操作延迟(ms)
    timeout: int = 30000       # 超时时间(ms)
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    downloads_path: str = "/tmp/downloads"
    accept_downloads: bool = True
    ignore_https_errors: bool = True
    
    # 代理配置
    proxy_server: Optional[str] = None
    proxy_bypass: Optional[str] = None
    
    # 浏览器启动参数
    args: List[str] = field(default_factory=list)


@dataclass
class ElementSelector:
    """元素选择器"""
    selector: str
    selector_type: str = "css"  # css, xpath, text, role, id
    
    def to_playwright(self) -> str:
        """转换为Playwright选择器"""
        if self.selector_type == "xpath":
            return f"xpath={self.selector}"
        elif self.selector_type == "text":
            return f"text={self.selector}"
        elif self.selector_type == "role":
            return f'role={self.selector}'
        elif self.selector_type == "id":
            return f"#{self.selector}"
        else:
            return self.selector


class BrowserDriver:
    """
    Playwright浏览器驱动封装
    
    功能特性：
    1. 支持Chromium/Firefox/WebKit
    2. 页面截图功能
    3. 元素定位与交互
    4. 等待策略
    5. 上下文隔离
    """
    
    def __init__(self, config: BrowserConfig = None, **kwargs):
        """
        初始化浏览器驱动
        
        Args:
            config: 浏览器配置
            **kwargs: 配置参数
        """
        if not _playwright_available:
            raise ImportError("playwright未安装，请执行: pip install playwright && playwright install")
        
        self._config = config or BrowserConfig(**kwargs)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # 确保下载目录存在
        Path(self._config.downloads_path).mkdir(parents=True, exist_ok=True)
    
    async def start(self) -> 'BrowserDriver':
        """
        启动浏览器
        
        Returns:
            self
        """
        if self._browser:
            return self
        
        self._playwright = await async_playwright().start()
        
        # 构建启动参数
        launch_args = {
            'headless': self._config.headless,
            'slow_mo': self._config.slow_mo,
            'args': self._config.args or [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        }
        
        # 添加代理配置
        if self._config.proxy_server:
            launch_args['proxy'] = {
                'server': self._config.proxy_server,
                'bypass': self._config.proxy_bypass
            }
        
        # 启动浏览器
        browser_type = getattr(self._playwright, self._config.browser_type)
        self._browser = await browser_type.launch(**launch_args)
        
        # 创建上下文
        context_args = {
            'viewport': {'width': self._config.viewport_width, 'height': self._config.viewport_height},
            'ignore_https_errors': self._config.ignore_https_errors,
            'accept_downloads': self._config.accept_downloads,
            'downloads_path': self._config.downloads_path
        }
        
        if self._config.user_agent:
            context_args['user_agent'] = self._config.user_agent
        
        self._context = await self._browser.new_context(**context_args)
        
        # 创建页面
        self._page = await self._context.new_page()
        
        logger.info(f"浏览器启动成功: {self._config.browser_type}")
        return self
    
    def sync_start(self) -> 'BrowserDriver':
        """同步启动浏览器"""
        asyncio.get_event_loop().run_until_complete(self.start())
        return self
    
    async def navigate(self, url: str, wait_until: str = "load") -> bool:
        """
        导航到URL
        
        Args:
            url: 目标URL
            wait_until: 等待策略 (load, domcontentloaded, networkidle, commit)
        
        Returns:
            是否成功
        """
        if not self._page:
            await self.start()
        
        try:
            await self._page.goto(url, wait_until=wait_until, timeout=self._config.timeout)
            logger.info(f"导航成功: {url}")
            return True
        except Exception as e:
            logger.error(f"导航失败: {url} - {e}")
            return False
    
    def sync_navigate(self, url: str, wait_until: str = "load") -> bool:
        """同步导航"""
        return asyncio.get_event_loop().run_until_complete(self.navigate(url, wait_until))
    
    async def screenshot(self, path: str = None, full_page: bool = False, 
                         element: ElementSelector = None) -> Optional[bytes]:
        """
        页面截图
        
        Args:
            path: 保存路径
            full_page: 是否截取整个页面
            element: 特定元素截图
        
        Returns:
            截图二进制数据
        """
        if not self._page:
            return None
        
        try:
            if element:
                el = await self.find_element(element)
                if el:
                    image = await el.screenshot(path=path, type='png')
                else:
                    return None
            else:
                image = await self._page.screenshot(path=path, full_page=full_page, type='png')
            
            if path:
                logger.info(f"截图已保存: {path}")
            
            return image
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def sync_screenshot(self, path: str = None, full_page: bool = False) -> Optional[bytes]:
        """同步截图"""
        return asyncio.get_event_loop().run_until_complete(self.screenshot(path, full_page))
    
    async def find_element(self, selector: ElementSelector, 
                          timeout: int = None) -> Optional['ElementHandle']:
        """
        查找单个元素
        
        Args:
            selector: 元素选择器
            timeout: 超时时间(ms)
        
        Returns:
            元素句柄
        """
        if not self._page:
            return None
        
        timeout = timeout or self._config.timeout
        playwright_selector = selector.to_playwright()
        
        try:
            element = await self._page.wait_for_selector(
                playwright_selector, 
                timeout=timeout,
                state='visible'
            )
            return element
        except PlaywrightTimeoutError:
            logger.debug(f"元素未找到: {playwright_selector}")
            return None
        except Exception as e:
            logger.debug(f"查找元素失败: {playwright_selector} - {e}")
            return None
    
    async def find_elements(self, selector: ElementSelector) -> List['ElementHandle']:
        """
        查找多个元素
        
        Args:
            selector: 元素选择器
        
        Returns:
            元素列表
        """
        if not self._page:
            return []
        
        playwright_selector = selector.to_playwright()
        
        try:
            elements = await self._page.query_selector_all(playwright_selector)
            return elements
        except Exception as e:
            logger.debug(f"查找元素失败: {playwright_selector} - {e}")
            return []
    
    async def click(self, selector: ElementSelector, timeout: int = None,
                    wait_after: int = 0) -> bool:
        """
        点击元素
        
        Args:
            selector: 元素选择器
            timeout: 超时时间
            wait_after: 点击后等待时间(ms)
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector, timeout)
        if not element:
            return False
        
        try:
            await element.click(timeout=timeout or self._config.timeout)
            if wait_after:
                await asyncio.sleep(wait_after / 1000)
            return True
        except Exception as e:
            logger.error(f"点击失败: {selector.selector} - {e}")
            return False
    
    async def fill(self, selector: ElementSelector, value: str, 
                   timeout: int = None) -> bool:
        """
        填充输入框
        
        Args:
            selector: 元素选择器
            value: 填充值
            timeout: 超时时间
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector, timeout)
        if not element:
            return False
        
        try:
            await element.fill(value)
            return True
        except Exception as e:
            logger.error(f"填充失败: {selector.selector} - {e}")
            return False
    
    async def type_text(self, selector: ElementSelector, text: str,
                        delay: int = 50) -> bool:
        """
        逐字输入文本
        
        Args:
            selector: 元素选择器
            text: 文本内容
            delay: 每个字符延迟(ms)
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            await element.type(text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {selector.selector} - {e}")
            return False
    
    async def get_text(self, selector: ElementSelector) -> Optional[str]:
        """
        获取元素文本
        
        Args:
            selector: 元素选择器
        
        Returns:
            文本内容
        """
        element = await self.find_element(selector)
        if not element:
            return None
        
        try:
            return await element.text_content()
        except Exception as e:
            logger.debug(f"获取文本失败: {selector.selector} - {e}")
            return None
    
    async def get_attribute(self, selector: ElementSelector, 
                            attribute: str) -> Optional[str]:
        """
        获取元素属性
        
        Args:
            selector: 元素选择器
            attribute: 属性名
        
        Returns:
            属性值
        """
        element = await self.find_element(selector)
        if not element:
            return None
        
        try:
            return await element.get_attribute(attribute)
        except Exception as e:
            logger.debug(f"获取属性失败: {selector.selector} - {e}")
            return None
    
    async def wait_for_selector(self, selector: ElementSelector,
                                 state: str = "visible",
                                 timeout: int = None) -> bool:
        """
        等待元素
        
        Args:
            selector: 元素选择器
            state: 等待状态 (attached, detached, visible, hidden)
            timeout: 超时时间
        
        Returns:
            是否成功
        """
        if not self._page:
            return False
        
        timeout = timeout or self._config.timeout
        playwright_selector = selector.to_playwright()
        
        try:
            await self._page.wait_for_selector(
                playwright_selector,
                state=state,
                timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            return False
    
    async def wait_for_load_state(self, state: str = "load", 
                                   timeout: int = None) -> bool:
        """
        等待页面加载状态
        
        Args:
            state: 加载状态 (load, domcontentloaded, networkidle)
            timeout: 超时时间
        
        Returns:
            是否成功
        """
        if not self._page:
            return False
        
        timeout = timeout or self._config.timeout
        
        try:
            await self._page.wait_for_load_state(state, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False
    
    async def wait_for_function(self, func: str, timeout: int = None,
                                 *args, **kwargs) -> bool:
        """
        等待JavaScript函数返回true
        
        Args:
            func: JavaScript函数
            timeout: 超时时间
        
        Returns:
            是否成功
        """
        if not self._page:
            return False
        
        timeout = timeout or self._config.timeout
        
        try:
            await self._page.wait_for_function(func, timeout=timeout, *args, **kwargs)
            return True
        except PlaywrightTimeoutError:
            return False
    
    async def execute_script(self, script: str, *args) -> Any:
        """
        执行JavaScript
        
        Args:
            script: JavaScript代码
            *args: 传给脚本的参数
        
        Returns:
            脚本执行结果
        """
        if not self._page:
            return None
        
        try:
            return await self._page.evaluate(script, *args)
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return None
    
    async def select_option(self, selector: ElementSelector, 
                            value: Union[str, List[str]] = None,
                            label: str = None,
                            index: int = None) -> bool:
        """
        选择下拉选项
        
        Args:
            selector: 选择器
            value: 选项值
            label: 选项标签
            index: 选项索引
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            if value is not None:
                await element.select_option(value=value)
            elif label:
                await element.select_option(label=label)
            elif index is not None:
                await element.select_option(index=index)
            return True
        except Exception as e:
            logger.error(f"选择选项失败: {selector.selector} - {e}")
            return False
    
    async def check(self, selector: ElementSelector, checked: bool = True) -> bool:
        """
        勾选/取消勾选复选框
        
        Args:
            selector: 选择器
            checked: 是否勾选
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            await element.set_checked(checked)
            return True
        except Exception as e:
            logger.error(f"设置复选框失败: {selector.selector} - {e}")
            return False
    
    async def hover(self, selector: ElementSelector) -> bool:
        """
        鼠标悬停
        
        Args:
            selector: 选择器
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            await element.hover()
            return True
        except Exception as e:
            logger.error(f"悬停失败: {selector.selector} - {e}")
            return False
    
    async def press_key(self, selector: ElementSelector, key: str) -> bool:
        """
        按键
        
        Args:
            selector: 选择器
            key: 按键名称
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            await element.press(key)
            return True
        except Exception as e:
            logger.error(f"按键失败: {selector.selector} - {e}")
            return False
    
    async def upload_file(self, selector: ElementSelector, 
                          file_path: Union[str, List[str]]) -> bool:
        """
        上传文件
        
        Args:
            selector: 选择器
            file_path: 文件路径
        
        Returns:
            是否成功
        """
        element = await self.find_element(selector)
        if not element:
            return False
        
        try:
            await element.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error(f"上传文件失败: {selector.selector} - {e}")
            return False
    
    async def get_cookies(self) -> List[Dict[str, Any]]:
        """获取所有cookies"""
        if not self._context:
            return []
        return await self._context.cookies()
    
    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """设置cookies"""
        if not self._context:
            return False
        try:
            await self._context.add_cookies(cookies)
            return True
        except Exception as e:
            logger.error(f"设置cookies失败: {e}")
            return False
    
    async def add_script_tag(self, content: str = None, 
                              url: str = None) -> bool:
        """
        添加脚本标签
        
        Args:
            content: 脚本内容
            url: 脚本URL
        
        Returns:
            是否成功
        """
        if not self._page:
            return False
        
        try:
            if content:
                await self._page.add_script_tag(content=content)
            elif url:
                await self._page.add_script_tag(url=url)
            return True
        except Exception as e:
            logger.error(f"添加脚本标签失败: {e}")
            return False
    
    async def add_style_tag(self, content: str = None,
                             url: str = None) -> bool:
        """
        添加样式标签
        
        Args:
            content: 样式内容
            url: 样式URL
        
        Returns:
            是否成功
        """
        if not self._page:
            return False
        
        try:
            if content:
                await self._page.add_style_tag(content=content)
            elif url:
                await self._page.add_style_tag(url=url)
            return True
        except Exception as e:
            logger.error(f"添加样式标签失败: {e}")
            return False
    
    @property
    def page(self) -> Optional[Page]:
        """获取当前页面"""
        return self._page
    
    @property
    def context(self) -> Optional[BrowserContext]:
        """获取当前上下文"""
        return self._context
    
    async def new_page(self) -> Page:
        """创建新页面"""
        if not self._context:
            await self.start()
        return await self._context.new_page()
    
    async def close_page(self, page: Page = None):
        """关闭页面"""
        page = page or self._page
        if page:
            await page.close()
    
    async def close(self):
        """关闭浏览器"""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("浏览器已关闭")
    
    def sync_close(self):
        """同步关闭"""
        asyncio.get_event_loop().run_until_complete(self.close())
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def __enter__(self):
        self.sync_start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_close()


class BrowserPool:
    """
    浏览器池
    
    用于管理多个浏览器实例的复用
    """
    
    def __init__(self, config: BrowserConfig = None, pool_size: int = 3):
        """
        初始化浏览器池
        
        Args:
            config: 浏览器配置
            pool_size: 池大小
        """
        self._config = config or BrowserConfig()
        self._pool_size = pool_size
        self._pool: List[BrowserDriver] = []
        self._in_use: set = set()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> BrowserDriver:
        """
        获取浏览器实例
        
        Returns:
            浏览器驱动
        """
        async with self._lock:
            # 查找空闲实例
            for driver in self._pool:
                if id(driver) not in self._in_use:
                    self._in_use.add(id(driver))
                    return driver
            
            # 创建新实例
            if len(self._pool) < self._pool_size:
                driver = BrowserDriver(self._config)
                await driver.start()
                self._pool.append(driver)
                self._in_use.add(id(driver))
                return driver
            
            # 等待空闲实例
            while True:
                await asyncio.sleep(0.5)
                for driver in self._pool:
                    if id(driver) not in self._in_use:
                        self._in_use.add(id(driver))
                        return driver
    
    async def release(self, driver: BrowserDriver):
        """
        释放浏览器实例
        
        Args:
            driver: 浏览器驱动
        """
        async with self._lock:
            self._in_use.discard(id(driver))
    
    @asynccontextmanager
    async def get_driver(self):
        """
        获取驱动上下文管理器
        
        使用示例:
            async with pool.get_driver() as driver:
                await driver.navigate("https://example.com")
        """
        driver = await self.acquire()
        try:
            yield driver
        finally:
            await self.release(driver)
    
    async def close_all(self):
        """关闭所有浏览器"""
        async with self._lock:
            for driver in self._pool:
                await driver.close()
            self._pool.clear()
            self._in_use.clear()
