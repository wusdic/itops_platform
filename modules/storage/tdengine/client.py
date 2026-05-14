"""
TDengine客户端核心实现

提供TDengine时序数据库的完整操作能力，支持REST API和WebSocket连接。
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class TDengineClient:
    """
    TDengine时序数据库客户端
    
    支持通过REST API与TDengine服务通信，提供数据写入、查询、订阅等功能。
    
    Attributes:
        host: TDengine服务主机地址
        port: REST API端口
        username: 认证用户名
        password: 认证密码
        database: 默认数据库名称
        timezone: 时区设置
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6041,
        username: str = 'root',
        password: str = 'taosdata',
        database: str = 'power',
        timezone: str = 'Asia/Shanghai'
    ):
        """
        初始化TDengine客户端
        
        Args:
            host: TDengine服务地址
            port: REST API端口
            username: 用户名
            password: 密码
            database: 默认数据库
            timezone: 时区
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.timezone = timezone
        self._base_url = f"http://{host}:{port}/rest/sql"
    
    def _make_request(self, sql: str) -> Dict[str, Any]:
        """
        发送REST API请求到TDengine
        
        Args:
            sql: SQL语句
            
        Returns:
            JSON响应解析后的字典
            
        Raises:
            ConnectionError: 无法连接到TDengine服务
            ValueError: SQL执行错误
        """
        try:
            # 先执行USE DATABASE确保在正确的数据库上下文
            auth_sql = f'USE {self.database};{sql}'
            
            request = Request(
                self._base_url,
                data=auth_sql.encode('utf-8'),
                headers={
                    'Authorization': f'Basic {self._get_auth()}',
                    'Content-Type': 'text/plain',
                    'Accept': 'application/json'
                },
                method='POST'
            )
            
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('status') == 'error':
                    raise ValueError(f"SQL Error: {result.get('desc', 'Unknown error')}")
                    
                return result
                
        except HTTPError as e:
            raise ConnectionError(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    def _get_auth(self) -> str:
        """生成Basic认证字符串"""
        import base64
        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode()).decode()
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """
        执行任意SQL语句
        
        Args:
            sql: SQL语句
            
        Returns:
            执行结果
        """
        # 移除末尾分号以避免重复
        sql = sql.rstrip(';')
        return self._make_request(sql)
    
    def create_database(
        self,
        database: str,
        keep: int = 365,
        days: int = 10,
        tables: int = 1000,
        cache: int = 256,
        replica: int = 1,
        precision: str = 'ms'
    ) -> Dict[str, Any]:
        """
        创建数据库
        
        Args:
            database: 数据库名
            keep: 数据保留天数
            days: 数据分片天数
            tables: 单节点最大表数
            cache: 缓存大小(MB)
            replica: 副本数
            precision: 时间精度(ms/us/ns)
            
        Returns:
            执行结果
        """
        sql = f"""CREATE DATABASE IF NOT EXISTS {database}
        KEEP {keep} DAYS {days}
        TABLES {tables}
        CACHE {cache}
        REPLICA {replica}
        PRECISION '{precision}'"""
        
        return self._make_request(sql)
    
    def create_stable(
        self,
        stable_name: str,
        tags_schema: Dict[str, str],
        columns_schema: Optional[Dict[str, str]] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建超级表
        
        Args:
            stable_name: 超级表名
            tags_schema: 标签定义 {name: type}
            columns_schema: 普通列定义 {name: type}
            database: 数据库名（默认使用初始化时的数据库）
            
        Returns:
            执行结果
        """
        db = database or self.database
        
        # 基础列
        columns = ['ts TIMESTAMP']
        if columns_schema:
            columns.extend([f"{k} {v}" for k, v in columns_schema.items()])
        
        # 标签
        tags = [f"{k} {v}" for k, v in tags_schema.items()]
        
        sql = f"""CREATE STABLE IF NOT EXISTS {db}.{stable_name}
        ({', '.join(columns)})
        TAGS ({', '.join(tags)})"""
        
        return self._make_request(sql)
    
    def create_subtable(
        self,
        table_name: str,
        stable_name: str,
        tags: Dict[str, Any],
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建子表（基于超级表）
        
        Args:
            table_name: 子表名
            stable_name: 父超级表名
            tags: 标签值 {tag_name: value}
            database: 数据库名
            
        Returns:
            执行结果
        """
        db = database or self.database
        tag_values = self._format_values(list(tags.values()))
        
        sql = f"""CREATE TABLE IF NOT EXISTS {db}.{table_name}
        USING {db}.{stable_name} TAGS ({tag_values})"""
        
        return self._make_request(sql)
    
    def insert(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        timestamp_key: str = 'ts',
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        插入数据
        
        Args:
            table_name: 表名
            data: 数据列表 [{'ts': datetime, 'field1': value1, ...}]
            timestamp_key: 时间戳字段名
            database: 数据库名
            
        Returns:
            执行结果
        """
        if not data:
            return {'status': 'success', 'rows_affected': 0}
        
        db = database or self.database
        
        # 构建列名
        columns = list(data[0].keys())
        columns_str = ', '.join(columns)
        
        # 构建值
        values_list = []
        for row in data:
            values = []
            for col in columns:
                val = row[col]
                if isinstance(val, datetime):
                    # TDengine时间戳格式
                    values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S.%f')}'")
                elif isinstance(val, str):
                    values.append(f"'{val}'")
                elif val is None:
                    values.append('NULL')
                else:
                    values.append(str(val))
            values_list.append(f"({', '.join(values)})")
        
        sql = f"INSERT INTO {db}.{table_name} ({columns_str}) VALUES {', '.join(values_list)}"
        
        return self._make_request(sql)
    
    def query(
        self,
        sql: str,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行查询
        
        Args:
            sql: 查询SQL
            database: 数据库名（会自动添加USE语句）
            
        Returns:
            查询结果
        """
        if database:
            return self._make_request(f"USE {database};{sql}")
        return self._make_request(sql)
    
    def query_range(
        self,
        table_name: str,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        columns: Optional[List[str]] = None,
        interval: Optional[str] = None,
        fill: Optional[str] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        时间范围查询
        
        Args:
            table_name: 表名
            start_time: 开始时间
            end_time: 结束时间
            columns: 查询的列（默认所有）
            interval: 降采样间隔（如'1m', '5s', '1h'）
            fill: 填充方式（prev/next/none/linear/value）
            database: 数据库名
            
        Returns:
            查询结果
        """
        db = database or self.database
        
        col_str = ', '.join(columns) if columns else '*'
        start_str = self._format_timestamp(start_time)
        end_str = self._format_timestamp(end_time)
        
        sql = f"SELECT {col_str} FROM {db}.{table_name} WHERE ts >= {start_str} AND ts <= {end_str}"
        
        if interval:
            sql += f" INTERVAL({interval})"
            if fill:
                sql += f" FILL({fill})"
        
        return self._make_request(sql)
    
    def latest(
        self,
        table_name: str,
        tags: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取最新数据
        
        Args:
            table_name: 表名
            tags: 过滤标签条件
            columns: 查询列
            database: 数据库名
            
        Returns:
            最新记录
        """
        db = database or self.database
        
        col_str = ', '.join(columns) if columns else '*'
        
        sql = f"SELECT {col_str} FROM {db}.{table_name}"
        
        if tags:
            tag_conditions = [f"tbname='{table_name}'"]
            for k, v in tags.items():
                tag_conditions.append(f"{k}='{v}'")
            sql += f" WHERE {' AND '.join(tag_conditions)}"
        
        sql += " ORDER BY ts DESC LIMIT 1"
        
        return self._make_request(sql)
    
    def aggregate(
        self,
        table_name: str,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        function: str = 'AVG',
        column: str = 'value',
        interval: Optional[str] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        聚合查询
        
        Args:
            table_name: 表名
            start_time: 开始时间
            end_time: 结束时间
            function: 聚合函数（AVG/SUM/MAX/MIN/COUNT/STDDEV）
            column: 列名
            interval: 分组间隔
            database: 数据库名
            
        Returns:
            聚合结果
        """
        db = database or self.database
        
        start_str = self._format_timestamp(start_time)
        end_str = self._format_timestamp(end_time)
        
        sql = f"SELECT {function}({column}) FROM {db}.{table_name}"
        sql += f" WHERE ts >= {start_str} AND ts <= {end_str}"
        
        if interval:
            sql += f" INTERVAL({interval})"
        
        return self._make_request(sql)
    
    def drop_table(self, table_name: str, database: Optional[str] = None) -> Dict[str, Any]:
        """删除表"""
        db = database or self.database
        return self._make_request(f"DROP TABLE IF EXISTS {db}.{table_name}")
    
    def drop_stable(self, stable_name: str, database: Optional[str] = None) -> Dict[str, Any]:
        """删除超级表"""
        db = database or self.database
        return self._make_request(f"DROP STABLE IF EXISTS {db}.{stable_name}")
    
    def drop_database(self, database: str) -> Dict[str, Any]:
        """删除数据库"""
        return self._make_request(f"DROP DATABASE IF EXISTS {database}")
    
    def list_tables(self, database: Optional[str] = None) -> List[str]:
        """列出所有表"""
        db = database or self.database
        result = self._make_request(f"SHOW {db}.TABLES")
        tables = []
        if result.get('data'):
            for row in result['data']:
                if row and len(row) > 0:
                    tables.append(row[0])
        return tables
    
    def list_stables(self, database: Optional[str] = None) -> List[str]:
        """列出所有超级表"""
        db = database or self.database
        result = self._make_request(f"SHOW {db}.STABLES")
        stables = []
        if result.get('data'):
            for row in result['data']:
                if row and len(row) > 0:
                    stables.append(row[0])
        return stables
    
    def get_table_info(self, table_name: str, database: Optional[str] = None) -> Dict[str, Any]:
        """获取表结构信息"""
        db = database or self.database
        return self._make_request(f"DESCRIBE {db}.{table_name}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self._make_request("SHOW DATABASES")
            return result.get('status') == 'succ'
        except Exception:
            return False
    
    def _format_timestamp(self, ts: Union[datetime, str]) -> str:
        """格式化时间戳为TDengine格式"""
        if isinstance(ts, datetime):
            return f"'{ts.strftime('%Y-%m-%d %H:%M:%S.%f')}'"
        elif isinstance(ts, str):
            # ISO格式
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return f"'{dt.strftime('%Y-%m-%d %H:%M:%S.%f')}'"
            return f"'{ts}'"
        return str(ts)
    
    def _format_values(self, values: List[Any]) -> str:
        """格式化值列表"""
        formatted = []
        for v in values:
            if isinstance(v, str):
                formatted.append(f"'{v}'")
            elif v is None:
                formatted.append('NULL')
            else:
                formatted.append(str(v))
        return ', '.join(formatted)
    
    def filter_match(self, table_name: str, field: str, value: Any) -> str:
        """
        构建精确匹配的过滤SQL片段
        
        Args:
            table_name: 表名
            field: 字段名
            value: 匹配值
            
        Returns:
            SQL WHERE子句
        """
        return f"SELECT * FROM {table_name} WHERE {field}='{value}'"
    
    def filter_range(
        self, 
        table_name: str, 
        field: str, 
        start: Any, 
        end: Any
    ) -> str:
        """
        构建范围过滤的SQL片段
        
        Args:
            table_name: 表名
            field: 字段名
            start: 范围起始值
            end: 范围结束值
            
        Returns:
            SQL WHERE子句
        """
        return f"SELECT * FROM {table_name} WHERE {field}>={start} AND {field}<={end}"
    
    def close(self):
        """关闭连接（REST API无连接池，保留接口）"""
        pass


# 使用示例
if __name__ == '__main__':
    # 配置连接参数
    config = {
        'host': 'localhost',
        'port': 6041,
        'username': 'root',
        'password': 'taosdata',
        'database': 'power'
    }
    
    # 创建客户端
    client = TDengineClient(**config)
    client.health_check()  # 测试连接
    
    # 创建数据库
    client.create_database('monitor', keep=30, days=1, precision='ms')
    
    # 创建超级表（用于存储设备指标）
    client.create_stable(
        stable_name='device_metrics',
        columns_schema={
            'cpu_usage': 'FLOAT',
            'memory_usage': 'FLOAT',
            'disk_usage': 'FLOAT'
        },
        tags_schema={
            'device_id': 'INT',
            'device_type': 'BINARY(50)',
            'location': 'BINARY(100)'
        }
    )
    
    # 创建子表（具体设备）
    client.create_subtable(
        table_name='server_001',
        stable_name='device_metrics',
        tags={'device_id': 1, 'device_type': 'server', 'location': ' datacenter-1'}
    )
    
    # 插入数据
    import random
    from datetime import datetime, timedelta
    
    now = datetime.now()
    data = []
    for i in range(10):
        data.append({
            'ts': now - timedelta(minutes=i * 5),
            'cpu_usage': random.uniform(20, 80),
            'memory_usage': random.uniform(30, 70),
            'disk_usage': random.uniform(40, 60)
        })
    
    result = client.insert('server_001', data)
    print(f"Insert result: {result}")
    
    # 查询最近1小时数据
    result = client.query_range(
        'server_001',
        start_time=now - timedelta(hours=1),
        end_time=now,
        interval='10m',
        fill='prev'
    )
    print(f"Query result: {result}")
    
    # 聚合查询
    result = client.aggregate(
        'server_001',
        start_time=now - timedelta(hours=24),
        end_time=now,
        function='AVG',
        column='cpu_usage',
        interval='1h'
    )
    print(f"Aggregate result: {result}")
    
    # 获取最新数据
    result = client.latest('server_001')
    print(f"Latest data: {result}")
    
    client.close()
