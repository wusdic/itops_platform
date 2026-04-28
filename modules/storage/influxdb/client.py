"""
InfluxDB客户端核心实现

支持InfluxDB 2.x API，提供数据写入（行协议）和查询（Flux）功能。
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class InfluxDBClient:
    """
    InfluxDB 2.x 客户端
    
    Attributes:
        url: InfluxDB服务URL
        token: API Token
        org: 组织名称
        bucket: 默认存储桶
        timeout: 请求超时时间(秒)
    """
    
    def __init__(
        self,
        url: str = 'http://localhost:8086',
        token: str = '',
        org: str = 'myorg',
        bucket: str = 'mybucket',
        timeout: int = 30
    ):
        """
        初始化InfluxDB客户端
        
        Args:
            url: InfluxDB服务地址
            token: API认证令牌
            org: 组织名称
            bucket: 默认存储桶
            timeout: 超时时间
        """
        self.url = url.rstrip('/')
        self.token = token
        self.org = org
        self.bucket = bucket
        self.timeout = timeout
        self._write_url = f"{self.url}/api/v2/write"
        self._query_url = f"{self.url}/api/v2/query"
        self._org_url = f"{self.url}/api/v2/orgs"
    
    def write_line_protocol(
        self,
        measurement: str,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        bucket: Optional[str] = None,
        org: Optional[str] = None
    ) -> bool:
        """
        使用行协议写入单条数据
        
        行协议格式: measurement,tag1=value1 field1=value1 timestamp
        
        Args:
            measurement: 测量名称
            tags: 标签（可选）
            fields: 字段（必须）
            timestamp: 时间戳（可选，默认当前时间）
            bucket: 存储桶（可选，默认使用初始化时的bucket）
            org: 组织（可选，默认使用初始化时的org）
            
        Returns:
            写入是否成功
        """
        if not fields:
            raise ValueError("Fields are required")
        
        # 构建行协议
        line = measurement
        
        if tags:
            tag_str = ','.join([f"{k}={v}" for k, v in tags.items()])
            line += f",{tag_str}"
        
        field_str = ','.join([self._format_field(k, v) for k, v in fields.items()])
        line += f" {field_str}"
        
        if timestamp:
            # 转换为纳秒时间戳
            ts = int(timestamp.timestamp() * 1e9)
            line += f" {ts}"
        
        return self._write_lines([line], bucket, org)
    
    def write_points(
        self,
        points: List[Dict[str, Any]],
        measurement_key: str = 'measurement',
        tags_keys: Optional[List[str]] = None,
        fields_keys: Optional[List[str]] = None,
        time_key: str = 'timestamp',
        bucket: Optional[str] = None,
        org: Optional[str] = None
    ) -> bool:
        """
        批量写入数据点
        
        Args:
            points: 数据点列表
            measurement_key: measurement字段的键名
            tags_keys: 标签字段列表
            fields_keys: 字段键列表（除measurement/tags/time外的所有键）
            time_key: 时间戳键名
            bucket: 存储桶
            org: 组织
            
        Returns:
            写入是否成功
        """
        lines = []
        
        for point in points:
            measurement = point.get(measurement_key)
            if not measurement:
                continue
            
            # 标签
            tags = {}
            if tags_keys:
                for key in tags_keys:
                    if key in point:
                        tags[key] = str(point[key])
            
            # 字段
            fields = {}
            if fields_keys:
                for key in fields_keys:
                    if key in point and key != time_key:
                        fields[key] = point[key]
            else:
                # 默认：所有非特殊键都是字段
                for key, value in point.items():
                    if key not in [measurement_key, time_key] and key not in (tags_keys or []):
                        fields[key] = value
            
            # 时间戳
            timestamp = None
            if time_key in point:
                ts = point[time_key]
                if isinstance(ts, datetime):
                    timestamp = ts
                elif isinstance(ts, (int, float)):
                    timestamp = datetime.fromtimestamp(ts)
            
            # 构建行
            line = measurement
            if tags:
                tag_str = ','.join([f"{k}={v}" for k, v in tags.items()])
                line += f",{tag_str}"
            
            field_str = ','.join([self._format_field(k, v) for k, v in fields.items()])
            line += f" {field_str}"
            
            if timestamp:
                ts = int(timestamp.timestamp() * 1e9)
                line += f" {ts}"
            
            lines.append(line)
        
        return self._write_lines(lines, bucket, org)
    
    def _write_lines(self, lines: List[str], bucket: Optional[str] = None, org: Optional[str] = None) -> bool:
        """写入多行数据"""
        data = '\n'.join(lines)
        
        request = Request(
            self._write_url,
            data=data.encode('utf-8'),
            headers={
                'Authorization': f'Token {self.token}',
                'Content-Type': 'text/plain; charset=utf-8',
                'Accept': 'application/json'
            },
            method='POST'
        )
        
        # 添加查询参数
        bkt = bucket or self.bucket
        org_name = org or self.org
        request.full_url = f"{request.full_url}?org={org_name}&bucket={bkt}"
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status in [200, 201, 204]
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            raise ConnectionError(f"Write Error {e.code}: {error_body}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    def query_flux(
        self,
        query: str,
        org: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        使用Flux查询语言查询数据
        
        Args:
            query: Flux查询语句
            org: 组织名称（可选）
            
        Returns:
            查询结果列表
        """
        request = Request(
            self._query_url,
            data=query.encode('utf-8'),
            headers={
                'Authorization': f'Token {self.token}',
                'Content-Type': 'application/vnd.flux',
                'Accept': 'application/json'
            },
            method='POST'
        )
        
        org_name = org or self.org
        request.full_url = f"{request.full_url}?org={org_name}"
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return self._parse_flux_response(result)
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            raise ValueError(f"Query Error {e.code}: {error_body}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    def query_range(
        self,
        measurement: str,
        start: Union[datetime, str, int],
        end: Optional[Union[datetime, str, int]] = None,
        bucket: Optional[str] = None,
        org: Optional[str] = None,
        where: Optional[str] = None,
        aggregate: Optional[str] = None,
        window_every: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        时间范围查询
        
        Args:
            measurement: 测量名称
            start: 开始时间
            end: 结束时间（默认now）
            bucket: 存储桶
            org: 组织
            where: 额外的过滤条件
            aggregate: 聚合函数（如 mean, max, min）
            window_every: 窗口大小（如 1m, 5s, 1h）
            
        Returns:
            查询结果
        """
        # 构建时间范围
        start_str = self._format_time(start)
        end_str = self._format_time(end) if end else 'now()'
        
        query = f'from(bucket: "{bucket or self.bucket}")\n'
        query += f'  |> range(start: {start_str}, stop: {end_str})\n'
        query += f'  |> filter(fn: (r) => r._measurement == "{measurement}")'
        
        if where:
            query += f'\n  |> filter(fn: (r) => {where})'
        
        if aggregate and window_every:
            query += f'\n  |> aggregateWindow(every: {window_every}, fn: {aggregate})'
        
        return self.query_flux(query, org)
    
    def query_last(
        self,
        measurement: str,
        bucket: Optional[str] = None,
        org: Optional[str] = None,
        where: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        查询最新数据
        
        Args:
            measurement: 测量名称
            bucket: 存储桶
            org: 组织
            where: 过滤条件
            limit: 返回条数
            
        Returns:
            最新数据
        """
        query = f'from(bucket: "{bucket or self.bucket}")\n'
        query += f'  |> range(start: -1h)\n'
        query += f'  |> filter(fn: (r) => r._measurement == "{measurement}")'
        
        if where:
            query += f'\n  |> filter(fn: (r) => {where})'
        
        query += f'\n  |> last()\n'
        query += f'  |> limit(n: {limit})'
        
        return self.query_flux(query, org)
    
    def query_mean(
        self,
        measurement: str,
        field: str,
        start: Union[datetime, str, int],
        end: Optional[Union[datetime, str, int]] = None,
        bucket: Optional[str] = None,
        org: Optional[str] = None,
        where: Optional[str] = None,
        window_every: str = '1h'
    ) -> List[Dict[str, Any]]:
        """
        查询平均值（带时间窗口）
        
        Args:
            measurement: 测量名称
            field: 字段名
            start: 开始时间
            end: 结束时间
            bucket: 存储桶
            org: 组织
            where: 过滤条件
            window_every: 窗口大小
            
        Returns:
            平均值结果
        """
        start_str = self._format_time(start)
        end_str = self._format_time(end) if end else 'now()'
        
        query = f'from(bucket: "{bucket or self.bucket}")\n'
        query += f'  |> range(start: {start_str}, stop: {end_str})\n'
        query += f'  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
        query += f'  |> filter(fn: (r) => r._field == "{field}")'
        
        if where:
            query += f'\n  |> filter(fn: (r) => {where})'
        
        query += f'\n  |> aggregateWindow(every: {window_every}, fn: mean)'
        
        return self.query_flux(query, org)
    
    def _parse_flux_response(self, result: Any) -> List[Dict[str, Any]]:
        """解析Flux响应"""
        records = []
        
        if isinstance(result, list):
            for table in result:
                if isinstance(table, dict) and 'records' in table:
                    for record in table['records']:
                        row = {'table': table.get('table', 0)}
                        # Flux返回的字段名可能包含表名
                        for key, value in record.items():
                            if key not in ['result', 'table']:
                                row[key] = value
                        records.append(row)
        
        return records
    
    def _format_time(self, time_val: Union[datetime, str, int]) -> str:
        """格式化时间参数"""
        if isinstance(time_val, datetime):
            # 转换为RFC3339格式
            return time_val.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(time_val, int):
            # 相对时间（秒）
            if time_val < 0:
                return f'{abs(time_val)}s'
            return f'{time_val}s'
        elif isinstance(time_val, str):
            # 相对时间或绝对时间
            return time_val
        return 'now()'
    
    def _format_field(self, key: str, value: Any) -> str:
        """格式化字段值"""
        if value is None:
            return f'{key}='
        elif isinstance(value, str):
            # 字符串需要转义
            escaped = value.replace('\\', '\\\\').replace(',', '\\,').replace(' ', '\\ ')
            return f'{key}="{escaped}"'
        elif isinstance(value, bool):
            return f'{key}={str(value).lower()}'
        else:
            return f'{key}={value}'
    
    def create_bucket(
        self,
        name: str,
        org: Optional[str] = None,
        retention_rules: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """创建存储桶"""
        bucket_url = f"{self.url}/api/v2/buckets"
        
        data = {
            'org': org or self.org,
            'name': name
        }
        
        if retention_rules:
            data['retentionRules'] = retention_rules
        
        request = Request(
            bucket_url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Authorization': f'Token {self.token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            raise ValueError(f"Create bucket error: {e.read().decode()}")
    
    def delete_measurement(self, measurement: str, bucket: Optional[str] = None) -> bool:
        """删除测量（使用delete predicate）"""
        # InfluxDB 2.x 使用delete predicate API
        delete_url = f"{self.url}/api/v2/delete"
        
        data = {
            'predicate': f'_measurement="{measurement}"',
            'start': '1970-01-01T00:00:00Z',
            'stop': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        request = Request(
            delete_url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Authorization': f'Token {self.token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        # 添加org参数
        request.full_url = f"{request.full_url}?org={self.org}&bucket={bucket or self.bucket}"
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
        except HTTPError as e:
            raise ValueError(f"Delete error: {e.read().decode()}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            health_url = f"{self.url}/health"
            request = Request(health_url, method='GET')
            if self.token:
                request.add_header('Authorization', f'Token {self.token}')
            
            with urlopen(request, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('status') == 'pass'
        except Exception:
            return False
    
    def get_measurements(self, bucket: Optional[str] = None, org: Optional[str] = None) -> List[str]:
        """获取所有测量名称"""
        query = f'''
        import "influxdata/influxdb/schema"
        schema.measurements(bucket: "{bucket or self.bucket}")
        '''
        
        try:
            results = self.query_flux(query, org)
            return [r.get('_value', r.get('value', '')) for r in results]
        except Exception:
            return []
    
    def close(self):
        """关闭连接"""
        pass


# 使用示例
if __name__ == '__main__':
    # 配置连接参数
    config = {
        'url': 'http://localhost:8086',
        'token': 'your-token-here',
        'org': 'myorg',
        'bucket': 'monitoring'
    }
    
    # 创建客户端
    client = InfluxDBClient(**config)
    
    # 写入单条数据（行协议）
    result = client.write_line_protocol(
        measurement='cpu_usage',
        tags={'host': 'server-001', 'region': 'us-east'},
        fields={'value': 45.5, 'core': 4},
        timestamp=datetime.now()
    )
    print(f"Write result: {result}")
    
    # 批量写入
    import random
    points = []
    now = datetime.now()
    
    for i in range(100):
        points.append({
            'measurement': 'sensor_data',
            'host': f'server-{i:03d}',
            'temperature': random.uniform(20, 30),
            'humidity': random.uniform(40, 60),
            'pressure': random.uniform(1000, 1010),
            'timestamp': now - timedelta(hours=i)
        })
    
    result = client.write_points(
        points,
        measurement_key='measurement',
        tags_keys=['host'],
        fields_keys=['temperature', 'humidity', 'pressure'],
        time_key='timestamp'
    )
    print(f"Batch write result: {result}")
    
    # 查询最近24小时数据
    results = client.query_range(
        measurement='cpu_usage',
        start=timedelta(hours=24),
        bucket='monitoring'
    )
    print(f"Query results: {len(results)} records")
    
    # 查询聚合平均值
    results = client.query_mean(
        measurement='cpu_usage',
        field='value',
        start=timedelta(hours=24),
        window_every='1h'
    )
    print(f"Aggregate results: {results}")
    
    # 查询最新数据
    results = client.query_last(
        measurement='cpu_usage',
        where='r.host == "server-001"',
        limit=5
    )
    print(f"Latest data: {results}")
    
    client.close()
