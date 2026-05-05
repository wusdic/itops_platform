# -*- coding: utf-8 -*-
"""
ITOps Platform - API Collector
API协议数据采集
"""
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from core.log import get_logger

logger = get_logger(__name__)


class APICollector:
    """API采集器"""
    
    def __init__(
        self,
        base_url: str,
        auth_type: str = "none",  # none, basic, bearer, api_key
        username: str = None,
        password: str = None,
        token: str = None,
        api_key: str = None,
        api_key_header: str = "X-API-Key",
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.auth_type = auth_type
        self.username = username
        self.password = password
        self.token = token
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            headers = {}
            
            if self.auth_type == "bearer" and self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            elif self.auth_type == "api_key" and self.api_key:
                headers[self.api_key_header] = self.api_key
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout)
            )
        
        return self._client
    
    async def collect(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """采集数据"""
        client = await self.connect()
        
        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            
            if "application/json" in response.headers.get("content-type", ""):
                return {"status": "success", "data": response.json()}
            else:
                return {"status": "success", "data": response.text}
        
        except httpx.HTTPError as e:
            logger.error(f"API采集失败 {self.base_url}/{endpoint}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def collect_multi(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量采集"""
        tasks = []
        
        for item in endpoints:
            endpoint = item.get("endpoint")
            params = item.get("params", {})
            name = item.get("name", endpoint)
            tasks.append(self.collect(endpoint, params))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            name: result if not isinstance(result, Exception) else {"status": "error", "error": str(result)}
            for name, result in zip([e.get("name", e.get("endpoint")) for e in endpoints], results)
        }
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 尝试访问根路径或健康检查端点
            endpoints = ["/health", "/api/health", "/", ""]
            
            for endpoint in endpoints:
                try:
                    client = await self.connect()
                    response = await client.get(endpoint)
                    if response.status_code < 500:
                        return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # Prometheus采集
    @staticmethod
    async def collect_prometheus(url: str, query: str) -> Dict[str, Any]:
        """采集Prometheus指标"""
        client = httpx.AsyncClient(timeout=30)
        
        try:
            response = await client.get(
                f"{url}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except httpx.HTTPError as e:
            return {"status": "error", "error": str(e)}
        finally:
            await client.aclose()
    
    @staticmethod
    async def collect_prometheus_range(url: str, query: str, start: float, end: float, step: str) -> Dict[str, Any]:
        """采集Prometheus范围指标"""
        client = httpx.AsyncClient(timeout=30)
        
        try:
            response = await client.get(
                f"{url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step
                }
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except httpx.HTTPError as e:
            return {"status": "error", "error": str(e)}
        finally:
            await client.aclose()
    
    # Zabbix采集
    @staticmethod
    async def collect_zabbix(url: str, auth: str, items: List[Dict]) -> Dict[str, Any]:
        """采集Zabbix指标"""
        client = httpx.AsyncClient(timeout=30)
        
        try:
            response = await client.post(
                f"{url}/api_jsonrpc.php",
                json={
                    "jsonrpc": "2.0",
                    "method": "item.get",
                    "params": {
                        "itemids": [item.get("itemid") for item in items],
                        "output": "extend"
                    },
                    "auth": auth,
                    "id": 1
                }
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except httpx.HTTPError as e:
            return {"status": "error", "error": str(e)}
        finally:
            await client.aclose()
