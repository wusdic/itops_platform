"""
浏览器登录采集器
通过 Playwright 无头浏览器登录设备 Web 管理界面采集监控数据
适用于没有 API、没有 SNMP/SSH，但有 Web 管理界面的设备
"""
import asyncio
import logging
import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BrowserCollectorConfig:
    """浏览器采集器配置"""
    host: str = ''
    port: int = 80
    protocol: str = 'http'  # http 或 https
    
    # 登录信息
    login_url: str = ''           # 完整登录 URL，留空则自动构造
    username: str = ''
    password: str = ''
    username_field: str = 'input[name="username"], input[id="username"], input[type="text"]'
    password_field: str = 'input[name="password"], input[type="password"]'
    submit_button: str = 'button[type="submit"], input[type="submit"], .login-btn'
    
    # 页面导航
    dashboard_url: str = ''       # 登录后跳转的页面，留空则不跳转
    page_load_timeout: int = 15000   # 页面加载超时（毫秒）
    wait_after_login: int = 3000     # 登录后等待时间（毫秒）
    
    # 数据提取配置
    data_selectors: Dict[str, str] = field(default_factory=dict)
    # 示例: {"cpu": "#cpu_usage", "memory": "#mem-usage", "status": ".status"}
    
    # Cookie/会话
    session_cookie_names: List[str] = field(default_factory=list)
    
    # SSL
    verify_ssl: bool = True
    
    # 其他
    screenshot_on_error: bool = False
    headless: bool = True


class BrowserCollector:
    """
    通过浏览器登录访问采集设备监控数据
    
    使用场景:
    - 设备无 SNMP/SSH/API
    - 设备有 Web 管理界面可以查看监控数据
    - 需要登录才能访问监控数据
    
    示例配置 (adapters.yaml):
    
    browser:
      enabled: true
      login_url: "http://192.168.1.1/login"
      username: "admin"
      password: "admin123"
      username_field: "input[name='username']"
      password_field: "input[name='password']"
      submit_button: "button[type='submit']"
      dashboard_url: "http://192.168.1.1/monitor"
      data_selectors:
        cpu: "#cpu_usage"
        memory: "#memory_usage"
        status: ".device-status"
      wait_after_login: 3000
    """
    
    def __init__(self, config: BrowserCollectorConfig):
        self.config = config
        self._page = None
        self._browser = None
        self._context = None
    
    def connect(self):
        """建立浏览器连接（实际上是启动浏览器）"""
        from playwright.sync_api import sync_playwright
        
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context_options = {
            'ignore_https_errors': not self.config.verify_ssl,
        }
        self._context = self._browser.new_context(**context_options)
        self._page = self._context.new_page()
        
        # 设置超时
        self._page.set_default_timeout(self.config.page_load_timeout)
        
        logger.info(f"Browser collector connected to {self.config.host}:{self.config.port}")
    
    def login(self) -> bool:
        """执行登录操作"""
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        login_url = self.config.login_url
        if not login_url:
            scheme = 'https' if self.config.port == 443 else 'http'
            login_url = f"{scheme}://{self.config.host}:{self.config.port}/login"
        
        try:
            # 访问登录页面
            response = self._page.goto(login_url, wait_until='networkidle', timeout=self.config.page_load_timeout)
            if response and response.status >= 400:
                logger.warning(f"Login page returned status {response.status}")
            
            time.sleep(0.5)  # 等待页面稳定
            
            # 填写用户名
            try:
                self._page.fill(self.config.username_field, self.config.username)
            except Exception as e:
                logger.warning(f"Could not fill username field: {e}")
            
            # 填写密码
            try:
                self._page.fill(self.config.password_field, self.config.password)
            except Exception as e:
                logger.warning(f"Could not fill password field: {e}")
            
            # 点击提交按钮
            try:
                self._page.click(self.config.submit_button)
            except Exception as e:
                logger.warning(f"Could not click submit button: {e}")
                # 尝试按 Enter
                try:
                    self._page.press(self.config.password_field, 'Enter')
                except:
                    pass
            
            # 等待登录完成
            time.sleep(self.config.wait_after_login / 1000)
            
            # 检查是否登录成功（通过 URL 或页面内容判断）
            current_url = self._page.url
            logger.info(f"After login, URL: {current_url}")
            
            # 如果配置了 dashboard_url，跳转到监控页面
            if self.config.dashboard_url:
                try:
                    self._page.goto(self.config.dashboard_url, wait_until='networkidle', timeout=self.config.page_load_timeout)
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Could not navigate to dashboard: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            if self.config.screenshot_on_error:
                try:
                    self._page.screenshot(path=f"/tmp/login_error_{self.config.host}.png")
                except:
                    pass
            return False
    
    def collect(self) -> Dict[str, Any]:
        """
        采集数据 - 从页面提取指标
        
        Returns:
            包含提取的指标数据的字典
        """
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        collected = {}
        
        for metric_name, selector in self.config.data_selectors.items():
            try:
                # 尝试直接提取文本
                element = self._page.query_selector(selector)
                if element:
                    text = element.inner_text()
                    # 清理文本
                    text = text.strip()
                    # 尝试提取数字
                    number_match = re.search(r'[\d.]+', text)
                    if number_match:
                        value = float(number_match.group())
                        # 判断是否是百分比
                        if '%' in text:
                            value = value  # 保留为小数形式
                        collected[metric_name] = value
                    else:
                        collected[metric_name] = text
                else:
                    # 尝试 evaluate 获取数值
                    try:
                        result = self._page.evaluate(f'''
                            () => {{
                                const el = document.querySelector("{selector}");
                                if (!el) return null;
                                const text = el.innerText || el.textContent || '';
                                const num = parseFloat(text.match(/[\\d.]+/)?.[0] || '');
                                return isNaN(num) ? text.trim() : num;
                            }}
                        ''')
                        if result is not None:
                            collected[metric_name] = result
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"Failed to collect metric '{metric_name}' with selector '{selector}': {e}")
        
        return collected
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        执行完整的采集流程：连接 → 登录 → 采集 → 关闭
        """
        try:
            self.connect()
            login_ok = self.login()
            if not login_ok:
                return {'_login_success': False}
            
            data = self.collect()
            data['_login_success'] = True
            return data
            
        except Exception as e:
            logger.error(f"Browser collection failed: {e}")
            return {'_login_success': False, '_error': str(e)}
        
        finally:
            self.close()
    
    def close(self):
        """关闭浏览器"""
        try:
            if self._page:
                self._page.close()
                self._page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.close()
                self._browser = None
            if hasattr(self, '_playwright'):
                self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncBrowserCollector:
    """异步版本的浏览器采集器（用于设备管理器）"""
    
    def __init__(self, config: BrowserCollectorConfig):
        self.config = config
        self._sync_collector: Optional[BrowserCollector] = None
    
    def connect(self):
        """同步连接，用于 ThreadPoolExecutor"""
        self._sync_collector = BrowserCollector(self.config)
        self._sync_collector.connect()
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """采集所有指标"""
        if self._sync_collector is None:
            self.connect()
        return self._sync_collector.collect_all_metrics()
    
    def close(self):
        """关闭"""
        if self._sync_collector:
            self._sync_collector.close()
            self._sync_collector = None
