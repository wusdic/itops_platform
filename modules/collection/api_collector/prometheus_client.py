"""
Prometheus API客户端

Prometheus是一个开源的监控和告警工具包，本模块提供：
- 查询API（PromQL）
- 范围查询
- 元数据查询
- 规则管理
- 告警管理
- Target/ServiceDiscovery

配置参数：
    url: Prometheus服务器地址
    timeout: 超时时间
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class PrometheusClient:
    """
    Prometheus API客户端
    
    提供与Prometheus服务器的完整API交互能力。
    
    Attributes:
        url: Prometheus服务地址
        timeout: 请求超时
        headers: 请求头
    """
    
    def __init__(
        self,
        url: str = 'http://localhost:9090',
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        初始化Prometheus客户端
        
        Args:
            url: Prometheus服务器地址
            timeout: 超时时间
            headers: 额外请求头
        """
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {}
        
        self._api_url = f"{self.url}/api/v1"
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 查询参数
            method: HTTP方法
            
        Returns:
            API响应
        """
        url = f"{self._api_url}/{endpoint.lstrip('/')}"
        
        if params:
            from urllib.parse import urlencode
            query_string = urlencode(params)
            url = f"{url}?{query_string}"
        
        request = Request(
            url,
            headers=self.headers,
            method=method
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('status') == 'error':
                    raise PrometheusAPIError(
                        type=result.get('errorType', 'unknown'),
                        message=result.get('error', 'Unknown error')
                    )
                
                return result
                
        except HTTPError as e:
            raise ConnectionError(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    # ========== Query API ==========
    
    def query(self, query: str, time: Optional[Union[datetime, float]] = None) -> Dict[str, Any]:
        """
        即时查询
        
        在指定时间点执行PromQL查询，返回单个时间点的数据。
        
        Args:
            query: PromQL查询语句
            time: 查询时间点（可选，默认当前时间）
                  可以是datetime对象或Unix时间戳
            
        Returns:
            查询结果
        """
        params = {'query': query}
        
        if time:
            if isinstance(time, datetime):
                params['time'] = time.timestamp()
            else:
                params['time'] = time
        
        return self._make_request('/query', params)
    
    def query_range(
        self,
        query: str,
        start: Union[datetime, float],
        end: Union[datetime, float],
        step: str = '15s'
    ) -> Dict[str, Any]:
        """
        范围查询
        
        在指定时间范围内执行PromQL查询，返回多个时间点的数据。
        
        Args:
            query: PromQL查询语句
            start: 开始时间
            end: 结束时间
            step: 查询分辨率（如'15s', '1m', '5m', '1h'）
            
        Returns:
            范围查询结果
        """
        params = {
            'query': query,
            'step': step
        }
        
        if isinstance(start, datetime):
            params['start'] = start.timestamp()
        else:
            params['start'] = start
        
        if isinstance(end, datetime):
            params['end'] = end.timestamp()
        else:
            params['end'] = end
        
        return self._make_request('/query_range', params)
    
    # ========== Metadata API ==========
    
    def label_values(self, label: str) -> List[str]:
        """
        获取标签的所有值
        
        Args:
            label: 标签名
            
        Returns:
            标签值列表
        """
        result = self._make_request(f'/label/{label}/values')
        return result.get('data', [])
    
    def series(
        self,
        matches: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        """
        查询时间序列
        
        Args:
            matches: 序列选择器列表（如['up', 'process_cpu_seconds_total']）
            start: 开始时间
            end: 结束时间
            
        Returns:
            时间序列列表，每个序列包含标签集
        """
        params = {'match[]': matches}
        
        if start:
            params['start'] = start.timestamp()
        if end:
            params['end'] = end.timestamp()
        
        result = self._make_request('/series', params)
        return result.get('data', [])
    
    def targets(self) -> Dict[str, Any]:
        """
        获取所有Target信息
        
        Returns:
            Target状态信息
        """
        return self._make_request('/targets')
    
    def targets_metadata(
        self,
        match_target: Optional[str] = None,
        metric: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取Target的元数据
        
        Args:
            match_target: Target匹配器
            metric: 指标名过滤
            limit: 返回限制
            
        Returns:
            元数据列表
        """
        params = {}
        if match_target:
            params['match_target'] = match_target
        if metric:
            params['metric'] = metric
        if limit:
            params['limit'] = limit
        
        return self._make_request('/targets/metadata', params)
    
    # ========== Rules API ==========
    
    def rules(self, type_: Optional[str] = None) -> Dict[str, Any]:
        """
        获取告警和记录规则
        
        Args:
            type_: 规则类型过滤（'alert' 或 'record'）
            
        Returns:
            规则列表
        """
        params = {}
        if type_:
            params['type'] = type_
        
        return self._make_request('/rules', params)
    
    def alerts(self) -> List[Dict[str, Any]]:
        """
        获取当前告警
        
        Returns:
            告警列表
        """
        result = self._make_request('/alerts')
        return result.get('data', {}).get('alerts', [])
    
    # ========== Alertmanagers API ==========
    
    def alertmanagers(self) -> Dict[str, Any]:
        """获取配置的Alertmanager"""
        return self._make_request('/alertmanagers')
    
    # ========== Status API ==========
    
    def status_flags(self) -> Dict[str, Any]:
        """获取运行时标志"""
        return self._make_request('/status/flags')
    
    def status_runtimeinfo(self) -> Dict[str, Any]:
        """获取运行时信息"""
        return self._make_request('/status/runtimeinfo')
    
    def status_buildinfo(self) -> Dict[str, Any]:
        """获取构建信息"""
        return self._make_request('/status/buildinfo')
    
    def status_tsdb(self) -> Dict[str, Any]:
        """获取TSDB状态"""
        return self._make_request('/status/tsdb')
    
    def status_walreplay(self) -> Dict[str, Any]:
        """获取WAL重放状态"""
        return self._make_request('/status/walreplay')
    
    # ========== Graph API ==========
    
    def delete_series(
        self,
        matches: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        删除时间序列（仅在--web.enable-lifecycle开启时可用）
        
        Args:
            matches: 序列选择器
            start: 开始时间
            end: 结束时间
            
        Returns:
            操作结果
        """
        params = {'match[]': matches}
        
        if start:
            params['start'] = start.timestamp()
        if end:
            params['end'] = end.timestamp()
        
        return self._make_request('/admin/tsdb/delete_series', params, method='POST')
    
    def clean_tombstones(self) -> Dict[str, Any]:
        """清理墓碑"""
        return self._make_request('/admin/tsdb/clean_tombstones', method='POST')
    
    # ========== Snapshot API ==========
    
    def create_snapshot(
        self,
        skip_head: bool = False
    ) -> Dict[str, Any]:
        """
        创建快照
        
        Args:
            skip_head: 是否跳过head块
            
        Returns:
            快照信息
        """
        params = {'skip_head': skip_head}
        return self._make_request('/admin/tsdb/snapshot', params, method='POST')
    
    # ========== Metrics API ==========
    
    def metrics(self) -> str:
        """
        获取Prometheus指标（/metrics端点）
        
        Returns:
            原始指标文本
        """
        url = f"{self.url}/metrics"
        request = Request(url, method='GET')
        
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode('utf-8')
    
    # ========== High-Level Utilities ==========
    
    def get_metric_values(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = '15s'
    ) -> List[Dict[str, Any]]:
        """
        获取指标值的高级封装
        
        Args:
            metric_name: 指标名
            labels: 标签过滤
            start: 开始时间
            end: 结束时间
            step: 采样间隔
            
        Returns:
            时间序列数据点列表
        """
        # 构建查询
        query = metric_name
        if labels:
            label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
            query = f'{metric_name}{{{label_str}}}'
        
        # 执行查询
        if start and end:
            result = self.query_range(query, start, end, step)
            return self._parse_range_result(result)
        else:
            result = self.query(query, end or datetime.now())
            return self._parse_instant_result(result)
    
    def get_all_metrics(self) -> List[str]:
        """获取所有指标名"""
        result = self._make_request('/label/__name__/values')
        return result.get('data', [])
    
    def get_metric_info(self, metric_name: str) -> List[Dict[str, Any]]:
        """
        获取指标元信息
        
        Args:
            metric_name: 指标名
            
        Returns:
            指标元信息
        """
        series = self.series([metric_name])
        return series
    
    def get_up_status(
        self,
        job: Optional[str] = None,
        instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取up状态
        
        Args:
            job: 作业名过滤
            instance: 实例过滤
            
        Returns:
            各目标的up状态
        """
        query = 'up'
        conditions = []
        
        if job:
            conditions.append(f'job="{job}"')
        if instance:
            conditions.append(f'instance="{instance}"')
        
        if conditions:
            query = f"up{{{','.join(conditions)}}}"
        
        return self.query(query)
    
    def get_cpu_usage(
        self,
        instance: Optional[str] = None,
        mode: str = 'total',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = '1m'
    ) -> List[Dict[str, Any]]:
        """
        获取CPU使用率
        
        Args:
            instance: 实例过滤
            mode: 模式（total/user/system/idle等）
            start: 开始时间
            end: 结束时间
            step: 采样间隔
            
        Returns:
            CPU使用率数据
        """
        if mode == 'total':
            query = '100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)'
        else:
            query = f'rate(node_cpu_seconds_total{{mode="{mode}"}}[5m]) * 100'
        
        if instance:
            query = f'{query}{{instance="{instance}"}}'
        
        if start and end:
            return self._parse_range_result(self.query_range(query, start, end, step))
        else:
            return self._parse_instant_result(self.query(query))
    
    def get_memory_usage(
        self,
        instance: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = '1m'
    ) -> List[Dict[str, Any]]:
        """
        获取内存使用率
        
        Args:
            instance: 实例过滤
            start: 开始时间
            end: 结束时间
            step: 采样间隔
            
        Returns:
            内存使用率数据
        """
        query = '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100'
        
        if instance:
            query = f'{query}{{instance="{instance}"}}'
        
        if start and end:
            return self._parse_range_result(self.query_range(query, start, end, step))
        else:
            return self._parse_instant_result(self.query(query))
    
    def get_disk_usage(
        self,
        instance: Optional[str] = None,
        device: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = '1m'
    ) -> List[Dict[str, Any]]:
        """
        获取磁盘使用率
        
        Args:
            instance: 实例过滤
            device: 设备过滤
            start: 开始时间
            end: 结束时间
            step: 采样间隔
            
        Returns:
            磁盘使用率数据
        """
        query = '(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100'
        
        filters = []
        if instance:
            filters.append(f'instance="{instance}"')
        if device:
            filters.append(f'device="{device}"')
        
        if filters:
            query = f'{query}{{{",".join(filters)}}}'
        
        if start and end:
            return self._parse_range_result(self.query_range(query, start, end, step))
        else:
            return self._parse_instant_result(self.query(query))
    
    def get_network_traffic(
        self,
        instance: Optional[str] = None,
        interface: Optional[str] = None,
        direction: str = 'receive',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = '1m'
    ) -> List[Dict[str, Any]]:
        """
        获取网络流量
        
        Args:
            instance: 实例过滤
            interface: 网卡过滤
            direction: 方向（receive/transmit）
            start: 开始时间
            end: 结束时间
            step: 采样间隔
            
        Returns:
            网络流量数据（字节/秒）
        """
        if direction == 'receive':
            query = 'rate(node_network_receive_bytes_total[5m])'
        else:
            query = 'rate(node_network_transmit_bytes_total[5m])'
        
        filters = []
        if instance:
            filters.append(f'instance="{instance}"')
        if interface:
            filters.append(f'durface="{interface}"')
        
        if filters:
            query = f'{query}{{{",".join(filters)}}}'
        
        if start and end:
            return self._parse_range_result(self.query_range(query, start, end, step))
        else:
            return self._parse_instant_result(self.query(query))
    
    # ========== Result Parsing ==========
    
    def _parse_instant_result(self, result: Dict) -> List[Dict[str, Any]]:
        """解析即时查询结果"""
        if result.get('status') != 'success':
            return []
        
        data = result.get('data', {})
        if data.get('resultType') == 'vector':
            values = []
            for item in data.get('result', []):
                values.append({
                    'metric': item.get('metric', {}),
                    'value': item.get('value')
                })
            return values
        return []
    
    def _parse_range_result(self, result: Dict) -> List[Dict[str, Any]]:
        """解析范围查询结果"""
        if result.get('status') != 'success':
            return []
        
        data = result.get('data', {})
        if data.get('resultType') == 'matrix':
            series_list = []
            for item in data.get('result', []):
                series_list.append({
                    'metric': item.get('metric', {}),
                    'values': item.get('values', [])
                })
            return series_list
        return []
    
    # ========== Health & Info ==========
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self._make_request('/-/healthy')
            return result.get('status') == 'success'
        except Exception:
            return False
    
    def ready_check(self) -> bool:
        """就绪检查"""
        try:
            result = self._make_request('/-/ready')
            return result.get('status') == 'success'
        except Exception:
            return False
    
    def version(self) -> Dict[str, Any]:
        """获取版本信息"""
        return self.status_buildinfo()
    
    def close(self):
        """关闭客户端"""
        pass


class PrometheusAPIError(Exception):
    """Prometheus API错误"""
    
    def __init__(self, type_: str, message: str):
        self.type = type_
        self.message = message
        super().__init__(f"Prometheus API Error ({type_}): {message}")


# 使用示例
if __name__ == '__main__':
    # 配置连接参数
    config = {
        'url': 'http://localhost:9090',
        'timeout': 30
    }
    
    # 创建客户端
    client = PrometheusClient(**config)
    
    # 健康检查
    print(f"Health check: {client.health_check()}")
    print(f"Ready check: {client.ready_check()}")
    
    # 获取版本
    version = client.version()
    print(f"Version: {version}")
    
    # 获取所有指标
    metrics = client.get_all_metrics()
    print(f"Total metrics: {len(metrics)}")
    print(f"Sample metrics: {metrics[:10]}")
    
    # 即时查询
    result = client.query('up')
    print(f"Up status: {result}")
    
    # 带标签过滤的查询
    result = client.query('up{job="prometheus"}')
    print(f"Prometheus status: {result}")
    
    # 范围查询（最近1小时）
    from datetime import datetime, timedelta
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    result = client.query_range(
        'rate(http_requests_total[5m])',
        start=start_time,
        end=end_time,
        step='1m'
    )
    print(f"Range query: {result}")
    
    # 获取CPU使用率
    cpu_usage = client.get_cpu_usage(
        instance='localhost:9100',
        step='5m'
    )
    print(f"CPU usage: {cpu_usage}")
    
    # 获取内存使用率
    mem_usage = client.get_memory_usage(
        instance='localhost:9100',
        step='5m'
    )
    print(f"Memory usage: {mem_usage}")
    
    # 获取磁盘使用率
    disk_usage = client.get_disk_usage(
        instance='localhost:9100',
        step='5m'
    )
    print(f"Disk usage: {disk_usage}")
    
    # 获取up状态
    up_status = client.get_up_status(job='node')
    print(f"Up status: {up_status}")
    
    # 获取标签值
    jobs = client.label_values('job')
    print(f"Available jobs: {jobs}")
    
    # 获取序列
    series = client.series(['up'])
    print(f"Up series: {len(series)}")
    
    # 获取Targets
    targets = client.targets()
    print(f"Active targets: {targets.get('data', {}).get('activeTargets', [])}")
    
    # 获取告警
    alerts = client.alerts()
    print(f"Active alerts: {alerts}")
    
    # 获取规则
    rules = client.rules()
    print(f"Rules: {rules}")
    
    # 获取TSDB状态
    tsdb_status = client.status_tsdb()
    print(f"TSDB status: {tsdb_status}")
    
    # 高级封装 - 获取指标值
    values = client.get_metric_values(
        'node_cpu_seconds_total',
        labels={'mode': 'idle', 'instance': 'localhost:9100'},
        start=start_time,
        end=end_time,
        step='5m'
    )
    print(f"Metric values: {len(values)} series")
    
    client.close()
