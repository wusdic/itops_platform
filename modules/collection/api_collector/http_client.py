"""
基础HTTP客户端

提供通用的HTTP请求能力，支持：
- 多种认证方式（Basic/Bearer/API Key/OAuth2）
- 自动重试机制
- 请求/响应拦截器
- 超时控制
- SSL配置
- 异步操作
- WebSocket支持
- 厂商适配器模式
"""

import asyncio
import json
import time
import hashlib
import hmac
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP方法枚举"""
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'


class AuthType(str, Enum):
    """认证类型枚举"""
    NONE = 'none'
    BASIC = 'basic'
    BEARER = 'bearer'
    API_KEY = 'api_key'
    OAUTH2 = 'oauth2'
    CUSTOM = 'custom'


class HTTPClient:
    """
    HTTP客户端
    
    提供RESTful API调用能力，支持认证、重试、日志记录等功能。
    
    Attributes:
        base_url: 基础URL
        timeout: 请求超时时间
        headers: 默认请求头
        proxies: 代理配置
    """
    
    def __init__(
        self,
        base_url: str = '',
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
        ssl_verify: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化HTTP客户端
        
        Args:
            base_url: API基础URL
            timeout: 超时时间（秒）
            headers: 默认请求头
            proxies: 代理配置 {'http': 'http://proxy:8080', 'https': 'https://proxy:8080'}
            ssl_verify: 是否验证SSL证书
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url.rstrip('/') if base_url else ''
        self.timeout = timeout
        self.default_headers = headers or {'User-Agent': 'ITOps-HTTPClient/1.0'}
        self.proxies = proxies
        self.ssl_verify = ssl_verify
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 认证配置
        self._auth_type = AuthType.NONE
        self._auth_credentials: Dict[str, Any] = {}
        
        # 拦截器
        self._request_interceptors: List[Callable] = []
        self._response_interceptors: List[Callable] = []
        
        # OAuth2 token
        self._oauth2_token: Optional[str] = None
        self._oauth2_token_expires: float = 0
    
    def set_auth(
        self,
        auth_type: AuthType,
        **credentials
    ) -> 'HTTPClient':
        """
        设置认证信息
        
        Args:
            auth_type: 认证类型
            **credentials: 认证凭据
            
        Returns:
            self
            
        Examples:
            client.set_auth(AuthType.BASIC, username='admin', password='pass')
            client.set_auth(AuthType.BEARER, token='xxx')
            client.set_auth(AuthType.API_KEY, key='xxx', header='X-API-Key')
        """
        self._auth_type = auth_type
        self._auth_credentials = credentials
        return self
    
    def add_request_interceptor(self, func: Callable) -> None:
        """添加请求拦截器"""
        self._request_interceptors.append(func)
    
    def add_response_interceptor(self, func: Callable) -> None:
        """添加响应拦截器"""
        self._response_interceptors.append(func)
    
    def _apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """应用认证到请求头"""
        if self._auth_type == AuthType.NONE:
            pass
        elif self._auth_type == AuthType.BASIC:
            import base64
            username = self._auth_credentials.get('username', '')
            password = self._auth_credentials.get('password', '')
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"
        elif self._auth_type == AuthType.BEARER:
            token = self._auth_credentials.get('token', '')
            headers['Authorization'] = f"Bearer {token}"
        elif self._auth_type == AuthType.API_KEY:
            key = self._auth_credentials.get('key', '')
            header = self._auth_credentials.get('header', 'X-API-Key')
            headers[header] = key
        elif self._auth_type == AuthType.OAUTH2:
            if self._oauth2_token and time.time() < self._oauth2_token_expires:
                headers['Authorization'] = f"Bearer {self._oauth2_token}"
        return headers
    
    def _build_url(self, endpoint: str, params: Optional[Dict]) -> str:
        """构建完整URL"""
        if endpoint:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url
        
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        return url
    
    def request(
        self,
        method: str,
        endpoint: str = '',
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: str = 'X-API-Key',
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法（GET/POST/PUT/DELETE/PATCH）
            endpoint: API端点
            params: URL查询参数
            data: 表单数据
            json_data: JSON数据
            headers: 额外请求头
            auth: Basic认证 (username, password)
            bearer_token: Bearer Token
            api_key: API Key
            api_key_header: API Key头部名称
            
        Returns:
            响应结果 {'status', 'status_code', 'headers', 'data'}
        """
        # 构建URL
        url = self._build_url(endpoint, params)
        
        # 合并请求头
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)
        
        # 添加认证
        if auth:
            import base64
            credentials = f"{auth[0]}:{auth[1]}"
            req_headers['Authorization'] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
        
        if bearer_token:
            req_headers['Authorization'] = f"Bearer {bearer_token}"
        
        if api_key:
            req_headers[api_key_header] = api_key
        
        # 应用默认认证
        req_headers = self._apply_auth(req_headers)
        
        # 构建请求体
        body = None
        if json_data is not None:
            body = json.dumps(json_data).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
        elif data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data).encode('utf-8')
                req_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            else:
                body = str(data).encode('utf-8')
        
        # 创建请求对象
        request = Request(
            url,
            data=body,
            headers=req_headers,
            method=method.upper()
        )
        
        # 应用请求拦截器
        for interceptor in self._request_interceptors:
            request = interceptor(request)
        
        # 发送请求（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._send_request(request)
                
                # 应用响应拦截器
                for interceptor in self._response_interceptors:
                    response = interceptor(response)
                
                return response
                
            except (URLError, HTTPError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
        
        raise last_error or ConnectionError("Request failed")
    
    def _send_request(self, request: Request) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            with urlopen(
                request,
                timeout=self.timeout,
                context=urllib.request.ssl.create_default_context() if self.ssl_verify else None
            ) as response:
                status_code = response.status
                response_headers = dict(response.headers)
                response_data = response.read().decode('utf-8')
                
                # 解析响应体
                content_type = response_headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = json.loads(response_data)
                elif response_data:
                    data = response_data
                else:
                    data = None
                
                return {
                    'status': 'success',
                    'status_code': status_code,
                    'headers': response_headers,
                    'data': data
                }
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            try:
                error_data = json.loads(error_body)
            except json.JSONDecodeError:
                error_data = error_body
            
            return {
                'status': 'error',
                'status_code': e.code,
                'headers': dict(e.headers) if hasattr(e, 'headers') else {},
                'data': error_data,
                'error': f"HTTP {e.code}: {e.reason}"
            }
    
    def get(
        self,
        endpoint: str = '',
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """GET请求"""
        return self.request('GET', endpoint, params=params, **kwargs)
    
    def post(
        self,
        endpoint: str = '',
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """POST请求"""
        return self.request('POST', endpoint, data=data, json_data=json_data, **kwargs)
    
    def put(
        self,
        endpoint: str = '',
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """PUT请求"""
        return self.request('PUT', endpoint, data=data, json_data=json_data, **kwargs)
    
    def patch(
        self,
        endpoint: str = '',
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """PATCH请求"""
        return self.request('PATCH', endpoint, data=data, json_data=json_data, **kwargs)
    
    def delete(
        self,
        endpoint: str = '',
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """DELETE请求"""
        return self.request('DELETE', endpoint, params=params, **kwargs)
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self.get('/health')
            return result.get('status_code', 0) in [200, 201, 204]
        except Exception:
            return False
    
    def close(self):
        """关闭客户端"""
        pass


class AsyncHTTPClient:
    """
    异步HTTP客户端
    
    提供异步RESTful API调用能力。
    """
    
    def __init__(
        self,
        base_url: str = '',
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        ssl_verify: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化异步HTTP客户端
        """
        self.base_url = base_url.rstrip('/') if base_url else ''
        self.timeout = timeout
        self.default_headers = headers or {'User-Agent': 'ITOps-AsyncHTTPClient/1.0'}
        self.ssl_verify = ssl_verify
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 认证配置
        self._auth_type = AuthType.NONE
        self._auth_credentials: Dict[str, Any] = {}
        
        # OAuth2 token
        self._oauth2_token: Optional[str] = None
        self._oauth2_token_expires: float = 0
    
    def set_auth(
        self,
        auth_type: AuthType,
        **credentials
    ) -> 'AsyncHTTPClient':
        """设置认证信息"""
        self._auth_type = auth_type
        self._auth_credentials = credentials
        return self
    
    def _apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """应用认证到请求头"""
        if self._auth_type == AuthType.NONE:
            pass
        elif self._auth_type == AuthType.BASIC:
            import base64
            username = self._auth_credentials.get('username', '')
            password = self._auth_credentials.get('password', '')
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"
        elif self._auth_type == AuthType.BEARER:
            token = self._auth_credentials.get('token', '')
            headers['Authorization'] = f"Bearer {token}"
        elif self._auth_type == AuthType.API_KEY:
            key = self._auth_credentials.get('key', '')
            header = self._auth_credentials.get('header', 'X-API-Key')
            headers[header] = key
        elif self._auth_type == AuthType.OAUTH2:
            if self._oauth2_token and time.time() < self._oauth2_token_expires:
                headers['Authorization'] = f"Bearer {self._oauth2_token}"
        return headers
    
    def _build_url(self, endpoint: str, params: Optional[Dict]) -> str:
        """构建完整URL"""
        if endpoint:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url
        
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        return url
    
    async def request(
        self,
        method: str,
        endpoint: str = '',
        params: Optional[Dict] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: 查询参数
            json_data: JSON数据
            headers: 请求头
            **kwargs: 其他参数
            
        Returns:
            响应结果
        """
        import aiohttp
        
        url = self._build_url(endpoint, params)
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)
        
        req_headers = self._apply_auth(req_headers)
        
        body = None
        if json_data is not None:
            body = json.dumps(json_data)
            req_headers['Content-Type'] = 'application/json'
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        url,
                        data=body,
                        headers=req_headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        ssl=self.ssl_verify if not self.ssl_verify else None
                    ) as response:
                        status_code = response.status
                        response_headers = dict(response.headers)
                        
                        try:
                            data = await response.json()
                        except:
                            data = await response.text()
                        
                        if response.status >= 400:
                            return {
                                'status': 'error',
                                'status_code': status_code,
                                'headers': response_headers,
                                'data': data,
                                'error': f"HTTP {status_code}"
                            }
                        
                        return {
                            'status': 'success',
                            'status_code': status_code,
                            'headers': response_headers,
                            'data': data
                        }
                        
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        return {
            'status': 'error',
            'status_code': -1,
            'error': str(last_error)
        }
    
    async def get(self, endpoint: str = '', params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """异步GET请求"""
        return await self.request('GET', endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str = '', json_data: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """异步POST请求"""
        return await self.request('POST', endpoint, json_data=json_data, **kwargs)
    
    async def put(self, endpoint: str = '', json_data: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """异步PUT请求"""
        return await self.request('PUT', endpoint, json_data=json_data, **kwargs)
    
    async def patch(self, endpoint: str = '', json_data: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """异步PATCH请求"""
        return await self.request('PATCH', endpoint, json_data=json_data, **kwargs)
    
    async def delete(self, endpoint: str = '', params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """异步DELETE请求"""
        return await self.request('DELETE', endpoint, params=params, **kwargs)


class WebSocketClient:
    """
    WebSocket客户端
    
    支持WebSocket连接进行实时数据推送和接收。
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        初始化WebSocket客户端
        
        Args:
            url: WebSocket URL
            headers: 连接头
            timeout: 超时时间
        """
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._ws = None
        self._connected = False
        self._message_handlers: List[Callable] = []
        self._receive_task: Optional[asyncio.Task] = None
    
    def add_message_handler(self, handler: Callable) -> None:
        """添加消息处理器"""
        self._message_handlers.append(handler)
    
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            import websockets
            
            self._ws = await websockets.connect(
                self.url,
                extra_headers=self.headers
            )
            self._connected = True
            
            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            return True
        except Exception as e:
            print(f"WebSocket连接失败: {e}")
            self._connected = False
            return False
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self._ws:
                for handler in self._message_handlers:
                    await handler(message)
        except Exception as e:
            print(f"WebSocket接收错误: {e}")
        finally:
            self._connected = False
    
    async def send(self, data: Union[str, Dict]) -> bool:
        """
        发送消息
        
        Args:
            data: 消息内容（字符串或字典）
            
        Returns:
            是否发送成功
        """
        if not self._connected or not self._ws:
            return False
        
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            await self._ws.send(data)
            return True
        except Exception as e:
            print(f"WebSocket发送失败: {e}")
            return False
    
    async def close(self) -> None:
        """关闭连接"""
        self._connected = False
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            await self._ws.close()


class VendorAPIClient:
    """
    厂商API客户端
    
    针对特定厂商的API进行封装，提供简化的接口。
    """
    
    # 厂商API配置
    VENDOR_CONFIGS: Dict[str, Dict] = {
        'zabbix': {
            'base_url': 'http://localhost/zabbix/api_jsonrpc.php',
            'auth_type': AuthType.NONE,  # 通过API方法认证
            'content_type': 'application/json',
        },
        'prometheus': {
            'base_url': 'http://localhost:9090',
            'auth_type': AuthType.NONE,
            'api_path': '/api/v1',
        },
        'sangfor': {
            'base_url': 'https://{host}:{port}/api/v1',
            'auth_type': AuthType.CUSTOM,
            'login_path': '/api/v1/auth/login',
        },
        'huawei': {
            'base_url': 'https://iam.cn-north-4.myhuaweicloud.com/v3',
            'auth_type': AuthType.OAUTH2,
            'token_path': '/auth/tokens',
        },
        'h3c': {
            'base_url': 'http://{host}:{port}/imcrs',
            'auth_type': AuthType.BASIC,
        },
        'topsec': {
            'base_url': 'http://{host}:{port}/api',
            'auth_type': AuthType.API_KEY,
        },
        'nsfocus': {
            'base_url': 'http://{host}:{port}/api',
            'auth_type': AuthType.BEARER,
        },
        'venustech': {
            'base_url': 'http://{host}:{port}/api/v1',
            'auth_type': AuthType.API_KEY,
        },
        'vmware': {
            'base_url': 'https://{host}/rest',
            'auth_type': AuthType.BASIC,
            'session_path': '/com/vmware/cis/session',
        },
        'kubernetes': {
            'base_url': 'https://{host}:{port}',
            'auth_type': AuthType.BEARER,
            'api_path': '/api/v1',
        },
        'docker': {
            'base_url': 'http://{host}:{port}',
            'auth_type': AuthType.NONE,
            'api_path': '/v1.41',
        },
        'openstack': {
            'base_url': 'http://{host}:{port}/identity/v3',
            'auth_type': AuthType.BEARER,
            'token_path': '/auth/tokens',
        },
    }
    
    def __init__(self, vendor: str, host: str, port: int = 80, **kwargs):
        """
        初始化厂商API客户端
        
        Args:
            vendor: 厂商标识
            host: 主机地址
            port: 端口
            **kwargs: 其他配置参数
        """
        self.vendor = vendor.lower()
        self.host = host
        self.port = port
        self.config = self.VENDOR_CONFIGS.get(self.vendor, {})
        
        # 构建base_url
        base_url = self.config.get('base_url', '')
        if '{host}' in base_url:
            base_url = base_url.replace('{host}', host)
        if '{port}' in base_url:
            base_url = base_url.replace('{port}', str(port))
        
        self.http_client = HTTPClient(base_url=base_url)
        
        # 设置认证
        auth_type = self.config.get('auth_type', AuthType.NONE)
        if auth_type == AuthType.BASIC:
            username = kwargs.get('username', 'admin')
            password = kwargs.get('password', '')
            self.http_client.set_auth(AuthType.BASIC, username=username, password=password)
        elif auth_type == AuthType.BEARER:
            token = kwargs.get('token', '')
            self.http_client.set_auth(AuthType.BEARER, token=token)
        elif auth_type == AuthType.API_KEY:
            api_key = kwargs.get('api_key', '')
            self.http_client.set_auth(AuthType.API_KEY, key=api_key)
        
        # 会话token
        self._session_token: Optional[str] = None
    
    async def login(self, username: str, password: str, **kwargs) -> bool:
        """
        厂商特定登录认证
        
        Args:
            username: 用户名
            password: 密码
            **kwargs: 其他参数
            
        Returns:
            登录是否成功
        """
        if self.vendor == 'zabbix':
            return await self._zabbix_login(username, password)
        elif self.vendor == 'sangfor':
            return await self._sangfor_login(username, password)
        elif self.vendor == 'huawei':
            return await self._huawei_login(username, password, kwargs.get('domain', ''))
        elif self.vendor == 'h3c':
            return await self._h3c_login(username, password)
        elif self.vendor == 'vmware':
            return await self._vmware_login(username, password)
        elif self.vendor == 'openstack':
            return await self._openstack_login(username, password, kwargs.get('project', ''))
        else:
            return True
    
    async def _zabbix_login(self, username: str, password: str) -> bool:
        """Zabbix登录"""
        result = await self._async_post('/api_jsonrpc.php', {
            'jsonrpc': '2.0',
            'method': 'user.login',
            'params': {'user': username, 'password': password},
            'id': 1
        })
        if result.get('result'):
            self._session_token = result['result']
            return True
        return False
    
    async def _sangfor_login(self, username: str, password: str) -> bool:
        """深信服登录"""
        result = await self._async_post('/api/v1/auth/login', {
            'username': username,
            'password': password
        })
        if result.get('status') == 0:
            self._session_token = result.get('data', {}).get('token', '')
            return True
        return False
    
    async def _huawei_login(self, username: str, password: str, domain: str) -> bool:
        """华为云登录"""
        auth_data = {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': username,
                            'password': password,
                            'domain': {'name': domain or username}
                        }
                    }
                },
                'scope': {'project': {'name': 'cn-north-4'}}
            }
        }
        
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.http_client.base_url}/auth/tokens",
                data=json.dumps(auth_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            response = urllib.request.urlopen(req, timeout=30)
            self._session_token = response.headers.get('X-Subject-Token', '')
            return bool(self._session_token)
        except Exception as e:
            print(f"华为云登录失败: {e}")
            return False
    
    async def _h3c_login(self, username: str, password: str) -> bool:
        """H3C iMC登录"""
        import base64
        credentials = f"{username}:{password}"
        self._session_token = base64.b64encode(credentials.encode()).decode()
        self.http_client.set_auth(AuthType.BASIC, username=username, password=password)
        return True
    
    async def _vmware_login(self, username: str, password: str) -> bool:
        """VMware vSphere登录"""
        self.http_client.set_auth(AuthType.BASIC, username=username, password=password)
        result = await self._async_post('/com/vmware/cis/session', None)
        if result.get('value'):
            self._session_token = result['value']
            return True
        return False
    
    async def _openstack_login(self, username: str, password: str, project: str) -> bool:
        """OpenStack登录"""
        auth_data = {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': username,
                            'password': password,
                            'domain': {'name': 'Default'}
                        }
                    }
                },
                'scope': {'project': {'name': project or 'admin'}}
            }
        }
        
        result = await self._async_post('/auth/tokens', auth_data, headers={'Content-Type': 'application/json'})
        if result.get('token'):
            self._session_token = result['token']
            return True
        return False
    
    async def _async_post(self, path: str, data: Any, **kwargs) -> Dict[str, Any]:
        """异步POST请求"""
        if hasattr(self.http_client, 'post'):
            # 同步客户端使用线程池
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.http_client.post(path, json_data=data, **kwargs)
            )
        return {'error': 'No post method available'}
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """
        采集指标数据
        
        Returns:
            厂商特定指标数据
        """
        if self.vendor == 'sangfor':
            return await self._collect_sangfor_metrics()
        elif self.vendor == 'huawei':
            return await self._collect_huawei_metrics()
        elif self.vendor == 'h3c':
            return await self._collect_h3c_metrics()
        elif self.vendor == 'vmware':
            return await self._collect_vmware_metrics()
        elif self.vendor == 'kubernetes':
            return await self._collect_kubernetes_metrics()
        else:
            return {}
    
    async def _collect_sangfor_metrics(self) -> Dict[str, Any]:
        """采集深信服设备指标"""
        try:
            status = await self._async_post('/api/v1/device/status', None)
            flow = await self._async_post('/api/v1/monitor/flow', None)
            
            return {
                'cpu_usage': status.get('data', {}).get('cpu_usage', 0),
                'memory_usage': status.get('data', {}).get('mem_usage', 0),
                'session_count': status.get('data', {}).get('session_count', 0),
                'bandwidth_in': flow.get('data', {}).get('in_bps', 0),
                'bandwidth_out': flow.get('data', {}).get('out_bps', 0),
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def _collect_huawei_metrics(self) -> Dict[str, Any]:
        """采集华为设备指标"""
        # 华为云CES监控
        try:
            result = await self._async_get('/V1.0/metric泉水')
            return result.get('metrics', {})
        except:
            return {}
    
    async def _collect_h3c_metrics(self) -> Dict[str, Any]:
        """采集H3C设备指标"""
        try:
            dev_info = await self._async_get('/imcrs/devinfo')
            return dev_info.get('deviceList', [])
        except:
            return []
    
    async def _collect_vmware_metrics(self) -> Dict[str, Any]:
        """采集VMware指标"""
        try:
            vms = await self._async_get('/vcenter/vm')
            hosts = await self._async_get('/vcenter/host')
            return {
                'vms': vms.get('value', []),
                'hosts': hosts.get('value', []),
            }
        except:
            return {}
    
    async def _collect_kubernetes_metrics(self) -> Dict[str, Any]:
        """采集Kubernetes指标"""
        try:
            pods = await self._async_get('/api/v1/pods')
            nodes = await self._async_get('/api/v1/nodes')
            return {
                'pods': pods.get('items', []),
                'nodes': nodes.get('items', []),
            }
        except:
            return {}
    
    async def _async_get(self, path: str, **kwargs) -> Dict[str, Any]:
        """异步GET请求"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.http_client.get(path, **kwargs)
        )


# 使用示例
if __name__ == '__main__':
    import asyncio
    
    # 同步客户端示例
    client = HTTPClient(
        base_url='https://api.example.com',
        timeout=30,
        max_retries=3
    )
    
    # 设置认证
    client.set_auth(AuthType.BEARER, token='your-token-here')
    
    # GET请求
    result = client.get('/users', params={'page': 1})
    print(f"GET Result: {result}")
    
    # POST请求
    result = client.post('/users', json_data={'name': 'Alice'})
    print(f"POST Result: {result}")
    
    # 厂商API客户端示例
    async def demo_vendor_client():
        # 深信服设备
        sangfor = VendorAPIClient(
            vendor='sangfor',
            host='192.168.1.1',
            port=443,
            username='admin',
            password='password'
        )
        
        if await sangfor.login('admin', 'password'):
            metrics = await sangfor.collect_metrics()
            print(f"Sangfor Metrics: {metrics}")
    
    asyncio.run(demo_vendor_client())
