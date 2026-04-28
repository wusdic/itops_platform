"""
基础HTTP客户端

提供通用的HTTP请求能力，支持：
- 多种认证方式（Basic/Bearer/API Key）
- 自动重试机制
- 请求/响应拦截器
- 超时控制
- SSL配置
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


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
        
        # 拦截器
        self._request_interceptors: List[Callable] = []
        self._response_interceptors: List[Callable] = []
    
    def add_request_interceptor(self, func: Callable) -> None:
        """添加请求拦截器"""
        self._request_interceptors.append(func)
    
    def add_response_interceptor(self, func: Callable) -> None:
        """添加响应拦截器"""
        self._response_interceptors.append(func)
    
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
        api_key_header: str = 'X-API-Key'
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
    
    def _build_url(self, endpoint: str, params: Optional[Dict]) -> str:
        """构建完整URL"""
        # 拼接基础URL和端点
        if endpoint:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url
        
        # 添加查询参数
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        return url
    
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


# 使用示例
if __name__ == '__main__':
    # 创建客户端
    client = HTTPClient(
        base_url='https://api.example.com',
        timeout=30,
        max_retries=3,
        retry_delay=1.0
    )
    
    # 添加请求日志拦截器
    def log_request(request):
        print(f"Request: {request.method} {request.full_url}")
        return request
    
    def log_response(response):
        print(f"Response: {response.get('status_code')}")
        return response
    
    client.add_request_interceptor(log_request)
    client.add_response_interceptor(log_response)
    
    # GET请求
    result = client.get(
        '/users',
        params={'page': 1, 'limit': 10}
    )
    print(f"GET Result: {result}")
    
    # POST请求 with JSON
    result = client.post(
        '/users',
        json_data={'name': 'Alice', 'email': 'alice@example.com'}
    )
    print(f"POST Result: {result}")
    
    # 带认证的请求
    result = client.get(
        '/protected',
        bearer_token='your-token-here'
    )
    print(f"Protected Result: {result}")
    
    # API Key认证
    result = client.get(
        '/api/data',
        api_key='your-api-key',
        api_key_header='X-API-Key'
    )
    print(f"API Key Result: {result}")
    
    client.close()
