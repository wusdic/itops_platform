"""
Qdrant向量数据库客户端核心实现

支持向量 CRUD 操作、相似度搜索、范围搜索等核心功能。
"""

import json
import uuid
import random
from typing import Any, Dict, List, Optional, Union
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class QdrantClient:
    """
    Qdrant向量数据库客户端
    
    支持向量存储、搜索、过滤等操作。
    
    Attributes:
        host: Qdrant服务主机地址
        port: REST API端口
        api_key: API密钥
        timeout: 请求超时
        collection_prefix: 集合名称前缀
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6333,
        api_key: Optional[str] = None,
        timeout: int = 30,
        https: bool = False,
        collection_prefix: str = ''
    ):
        """
        初始化Qdrant客户端
        
        Args:
            host: Qdrant服务主机
            port: 端口号
            api_key: API密钥（可选）
            timeout: 超时时间
            https: 是否使用HTTPS
            collection_prefix: 集合名称前缀
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self.prefix = collection_prefix
        
        scheme = 'https' if https else 'http'
        self.base_url = f"{scheme}://{host}:{port}"
        self.collections_url = f"{self.base_url}/collections"
        self.points_url = f"{self.base_url}/points"
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['api-key'] = self.api_key
        return headers
    
    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        if params:
            param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
        body = json.dumps(data).encode('utf-8') if data else None
        
        request = Request(
            url,
            data=body,
            headers=self._get_headers(),
            method=method
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = response.read().decode('utf-8')
                if result:
                    return json.loads(result)
                return {'status': 'ok'}
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            raise ConnectionError(f"HTTP {e.code}: {error_body}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str = 'Cosine',
        vector_params: Optional[Dict] = None,
        sparse_vector_params: Optional[Dict] = None,
        wal_config: Optional[Dict] = None,
        optimizers_config: Optional[Dict] = None,
        shard_number: Optional[int] = None,
        replication_factor: Optional[int] = None,
        on_disk_payload: bool = False
    ) -> Dict[str, Any]:
        """
        创建向量集合
        
        Args:
            name: 集合名称
            vector_size: 向量维度
            distance: 距离度量（Cosine/Dot/Euclid）
            vector_params: 向量参数
            sparse_vector_params: 稀疏向量参数
            wal_config: WAL配置
            optimizers_config: 优化器配置
            shard_number: 分片数
            replication_factor: 副本数
            on_disk_payload: 是否将payload存储在磁盘
            
        Returns:
            创建结果
        """
        collection_name = f"{self.prefix}{name}" if self.prefix else name
        
        vectors_config = {
            'params': vector_params or {
                'size': vector_size,
                'distance': distance
            }
        }
        
        payload = {
            'vectors_config': vectors_config
        }
        
        if sparse_vector_params:
            payload['sparse_vectors'] = sparse_vector_params
        
        config = {
            'wal': wal_config or {'wal_capacity_mb': 32, 'wal_segments_ahead': 0},
            'optimizers_config': optimizers_config or {
                'indexing_threshold': 20000,
                'memmap_threshold': 50000
            }
        }
        
        if shard_number:
            config['shard_number'] = shard_number
        
        if replication_factor:
            config['replication_factor'] = replication_factor
        
        config['on_disk_payload'] = on_disk_payload
        
        payload['config'] = config
        
        return self._make_request('PUT', f"{self.collections_url}/{collection_name}", payload)
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        result = self._make_request('GET', self.collections_url)
        collections = []
        if result.get('result'):
            for col in result['result']['collections']:
                name = col['name']
                if self.prefix and name.startswith(self.prefix):
                    name = name[len(self.prefix):]
                collections.append(name)
        return collections
    
    def get_collection(self, name: str) -> Dict[str, Any]:
        """获取集合信息"""
        collection_name = f"{self.prefix}{name}" if self.prefix else name
        return self._make_request('GET', f"{self.collections_url}/{collection_name}")
    
    def delete_collection(self, name: str) -> Dict[str, Any]:
        """删除集合"""
        collection_name = f"{self.prefix}{name}" if self.prefix else name
        return self._make_request('DELETE', f"{self.collections_url}/{collection_name}")
    
    def collection_exists(self, name: str) -> bool:
        """检查集合是否存在"""
        try:
            collection_name = f"{self.prefix}{name}" if self.prefix else name
            self._make_request('GET', f"{self.collections_url}/{collection_name}")
            return True
        except ConnectionError:
            return False
    
    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        wait: bool = True
    ) -> Dict[str, Any]:
        """
        插入或更新向量点
        
        Args:
            collection_name: 集合名
            points: 点列表，每个点包含:
                - id: 点ID (可选，自动生成UUID)
                - vector: 向量列表
                - payload: 元数据字典 (可选)
            wait: 是否等待索引完成
            
        Returns:
            操作结果
        """
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        formatted_points = []
        for point in points:
            p = {
                'id': point.get('id', str(uuid.uuid4())),
                'vector': point['vector']
            }
            if 'payload' in point:
                p['payload'] = point['payload']
            formatted_points.append(p)
        
        payload = {'points': formatted_points}
        
        if wait:
            payload['wait'] = True
        
        return self._make_request('PUT', f"{self.points_url}/collections/{name}", payload)
    
    def delete(
        self,
        collection_name: str,
        points_ids: Optional[List[str]] = None,
        filter_conditions: Optional[Dict] = None,
        wait: bool = True
    ) -> Dict[str, Any]:
        """
        删除向量点
        
        Args:
            collection_name: 集合名
            points_ids: 要删除的点ID列表
            filter_conditions: 过滤条件
            wait: 是否等待完成
            
        Returns:
            操作结果
        """
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        payload = {}
        if points_ids:
            payload['points'] = points_ids
        elif filter_conditions:
            payload['filter'] = filter_conditions
        
        if wait:
            payload['wait'] = True
        
        return self._make_request('POST', f"{self.points_url}/collections/{name}/points/delete", payload)
    
    def get_points(
        self,
        collection_name: str,
        points_ids: List[str],
        with_vectors: bool = False,
        with_payload: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取向量点
        
        Args:
            collection_name: 集合名
            points_ids: 点ID列表
            with_vectors: 是否返回向量
            with_payload: 是否返回payload
            
        Returns:
            点列表
        """
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        params = {
            'ids': points_ids,
            'with_vectors': with_vectors,
            'with_payload': with_payload
        }
        
        result = self._make_request(
            'POST',
            f"{self.points_url}/collections/{name}/points",
            params=params
        )
        
        return result.get('result', {}).get('points', [])
    
    def search(
        self,
        collection_name: str,
        query_vector: Union[List[float], str],
        limit: int = 10,
        offset: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict] = None,
        params: Optional[Dict] = None,
        with_vectors: bool = False,
        with_payload: bool = True,
        vector_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            collection_name: 集合名
            query_vector: 查询向量或命名的查询向量
            limit: 返回结果数量
            offset: 跳过前N个结果
            score_threshold: 最低分数阈值
            filter_conditions: 过滤条件
            params: 搜索参数（hnsw_ef, exact等）
            with_vectors: 是否返回向量
            with_payload: 是否返回payload
            vector_name: 向量名称（多向量时）
            
        Returns:
            搜索结果列表，按相似度降序排列
        """
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        payload = {
            'vector': query_vector,
            'limit': limit,
            'params': params or {'hnsw_ef': 128},
            'with_vectors': with_vectors,
            'with_payload': with_payload
        }
        
        if offset is not None:
            payload['offset'] = offset
        
        if score_threshold is not None:
            payload['score_threshold'] = score_threshold
        
        if filter_conditions:
            payload['filter'] = filter_conditions
        
        if vector_name:
            payload['vector_name'] = vector_name
        
        result = self._make_request(
            'POST',
            f"{self.collections_url}/{name}/points/search",
            payload
        )
        
        return result.get('result', [])
    
    def recommend(
        self,
        collection_name: str,
        positive: List[Union[str, List[float]]],
        negative: Optional[List[Union[str, List[float]]]] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict] = None,
        params: Optional[Dict] = None,
        with_vectors: bool = False,
        with_payload: bool = True
    ) -> List[Dict[str, Any]]:
        """
        推荐搜索（基于正负示例）
        
        Args:
            collection_name: 集合名
            positive: 正示例ID或向量
            negative: 负示例ID或向量
            limit: 返回数量
            score_threshold: 分数阈值
            filter_conditions: 过滤条件
            params: 搜索参数
            with_vectors: 是否返回向量
            with_payload: 是否返回payload
            
        Returns:
            推荐结果
        """
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        payload = {
            'positive': positive,
            'limit': limit,
            'params': params or {'hnsw_ef': 128},
            'with_vectors': with_vectors,
            'with_payload': with_payload
        }
        
        if negative:
            payload['negative'] = negative
        
        if score_threshold is not None:
            payload['score_threshold'] = score_threshold
        
        if filter_conditions:
            payload['filter'] = filter_conditions
        
        result = self._make_request(
            'POST',
            f"{self.collections_url}/{name}/points/recommend",
            payload
        )
        
        return result.get('result', [])
    
    @staticmethod
    def filter_match(field: str, value: Any) -> Dict[str, Any]:
        """构建精确匹配过滤条件"""
        return {
            'key': field,
            'match': {'value': value} if not isinstance(value, list) else {'any': value}
        }
    
    @staticmethod
    def filter_range(
        field: str,
        gte: Optional[Any] = None,
        gt: Optional[Any] = None,
        lte: Optional[Any] = None,
        lt: Optional[Any] = None
    ) -> Dict[str, Any]:
        """构建范围过滤条件"""
        range_dict = {}
        if gte is not None:
            range_dict['gte'] = gte
        if gt is not None:
            range_dict['gt'] = gt
        if lte is not None:
            range_dict['lte'] = lte
        if lt is not None:
            range_dict['lt'] = lt
        
        return {'key': field, 'range': range_dict}
    
    @staticmethod
    def filter_should(*conditions: Dict) -> Dict[str, Any]:
        """构建Should条件（OR关系）"""
        return {'should': list(conditions)}
    
    @staticmethod
    def filter_must(*conditions: Dict) -> Dict[str, Any]:
        """构建Must条件（AND关系）"""
        return {'must': list(conditions)}
    
    @staticmethod
    def filter_must_not(*conditions: Dict) -> Dict[str, Any]:
        """构建Must Not条件（NOT关系）"""
        return {'must_not': list(conditions)}
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self._make_request('GET', f"{self.base_url}/health")
            return result.get('status') == 'ok'
        except Exception:
            return False
    
    def count(
        self,
        collection_name: str,
        filter_conditions: Optional[Dict] = None,
        exact: bool = True
    ) -> int:
        """统计向量数量"""
        name = f"{self.prefix}{collection_name}" if self.prefix else collection_name
        
        payload = {'exact': exact}
        if filter_conditions:
            payload['filter'] = filter_conditions
        
        result = self._make_request(
            'POST',
            f"{self.points_url}/collections/{name}/points/count",
            payload
        )
        
        return result.get('result', {}).get('count', 0)
    
    def close(self):
        """关闭连接"""
        pass


if __name__ == '__main__':
    # 配置连接参数
    config = {
        'host': 'localhost',
        'port': 6333,
        'api_key': None,
        'collection_prefix': 'itops_'
    }
    
    client = QdrantClient(**config)
    
    # 创建集合
    client.create_collection(
        name='device_embeddings',
        vector_size=128,
        distance='Cosine'
    )
    
    # 生成示例向量
    vectors = []
    for i in range(10):
        vector = [random.random() for _ in range(128)]
        vectors.append({
            'id': f'vector_{i}',
            'vector': vector,
            'payload': {
                'device_id': f'DEV_{i:04d}',
                'device_type': 'server' if i % 2 == 0 else 'router',
                'location': f'datacenter-{i % 3 + 1}'
            }
        })
    
    # 插入向量
    result = client.upsert('device_embeddings', vectors)
    print(f"Upsert result: {result}")
    
    # 搜索
    query = [random.random() for _ in range(128)]
    results = client.search(
        collection_name='device_embeddings',
        query_vector=query,
        limit=5,
        score_threshold=0.5
    )
    
    print(f"Search results: {len(results)} found")
    for r in results:
        print(f"  ID: {r['id']}, Score: {r['score']:.4f}")
    
    # 过滤搜索
    filter_cond = QdrantClient.filter_must(
        QdrantClient.filter_match('device_type', 'server')
    )
    
    results = client.search(
        collection_name='device_embeddings',
        query_vector=query,
        limit=5,
        filter_conditions=filter_cond
    )
    
    print(f"Filtered results: {len(results)}")
    client.close()
