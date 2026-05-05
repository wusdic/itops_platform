"""
Docker API客户端
支持Docker Engine API，用于采集容器监控数据
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import docker
    from docker import APIClient as DockerAPIClient
    _docker_available = True
except ImportError:
    _docker_available = False
    docker = None
    DockerAPIClient = None


@dataclass
class DockerConfig:
    """Docker配置"""
    host: str = 'unix:///var/run/docker.sock'
    port: int = 2375
    tls_config: Optional[Any] = None
    api_version: str = '1.41'
    timeout: int = 30


class DockerClient:
    """
    Docker API客户端
    
    用于监控Docker容器和镜像。
    
    支持:
    - 容器列表和状态
    - 镜像管理
    - 网络信息
    - 卷管理
    - 容器统计
    - 日志读取
    
    使用示例:
    >>> client = DockerClient(host='tcp://192.168.1.1:2375')
    >>> client.connect()
    >>> containers = client.get_containers()
    >>> stats = client.get_container_stats('nginx')
    >>> client.close()
    """
    
    def __init__(self, config: DockerConfig = None, **kwargs):
        """
        初始化Docker客户端
        
        Args:
            config: Docker配置
            **kwargs: 直接传入的参数 (host, port, tls等)
        """
        if not _docker_available:
            raise ImportError("docker模块未安装，请执行: pip install docker")
        
        if config:
            self._config = config
        else:
            # 从kwargs构建配置
            host = kwargs.get('host', 'unix:///var/run/docker.sock')
            if not host.startswith('tcp://') and not host.startswith('unix://'):
                # 自动添加协议
                if kwargs.get('port'):
                    host = f"tcp://{host}:{kwargs['port']}"
            
            self._config = DockerConfig(
                host=host,
                port=kwargs.get('port', 2375),
                tls_config=kwargs.get('tls_config'),
                api_version=kwargs.get('api_version', '1.41'),
            )
        
        self._client: Optional[DockerAPIClient] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        连接Docker守护进程
        
        Returns:
            连接是否成功
        """
        try:
            self._client = docker.Client(
                base_url=self._config.host,
                version=self._config.api_version,
                timeout=self._config.timeout,
                tls=self._config.tls_config,
            )
            
            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info(f"Docker连接成功: {self._config.host}")
            return True
            
        except Exception as e:
            logger.error(f"Docker连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def get_version(self) -> Dict[str, Any]:
        """
        获取Docker版本信息
        
        Returns:
            版本信息
        """
        if not self._connected:
            return {}
        
        try:
            return self._client.version()
        except Exception as e:
            logger.error(f"获取Docker版本失败: {e}")
            return {}
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取Docker系统信息
        
        Returns:
            系统信息
        """
        if not self._connected:
            return {}
        
        try:
            return self._client.info()
        except Exception as e:
            logger.error(f"获取Docker信息失败: {e}")
            return {}
    
    def get_containers(
        self,
        all: bool = True,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        获取容器列表
        
        Args:
            all: 是否显示所有容器（包括已停止）
            filters: 过滤条件
            
        Returns:
            容器列表
        """
        if not self._connected:
            return []
        
        try:
            containers = self._client.containers(
                all=all,
                filters=filters,
                quiet=False,
                sparse=True,
            )
            
            return [self._parse_container(c) for c in containers]
        except Exception as e:
            logger.error(f"获取容器列表失败: {e}")
            return []
    
    def _parse_container(self, container: Dict) -> Dict[str, Any]:
        """解析容器数据"""
        return {
            'id': container.get('Id', '')[:12],
            'full_id': container.get('Id', ''),
            'names': container.get('Names', []),
            'image': container.get('Image', ''),
            'image_id': container.get('ImageID', ''),
            'command': container.get('Command', ''),
            'created': container.get('Created', 0),
            'state': container.get('State', ''),
            'status': container.get('Status', ''),
            'ports': container.get('Ports', []),
            'labels': container.get('Labels', {}),
            'mounts': container.get('Mounts', []),
            'network_settings': container.get('NetworkSettings', {}),
        }
    
    def get_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个容器详情
        
        Args:
            container_id: 容器ID或名称
            
        Returns:
            容器详情
        """
        if not self._connected:
            return None
        
        try:
            container = self._client.inspect_container(container_id)
            
            return {
                'id': container['Id'][:12],
                'full_id': container['Id'],
                'name': container['Name'],
                'created': container['Created'],
                'state': {
                    'status': container['State'].get('Status', ''),
                    'running': container['State'].get('Running', False),
                    'paused': container['State'].get('Paused', False),
                    'restarting': container['State'].get('Restarting', False),
                    'pid': container['State'].get('Pid', 0),
                    'exit_code': container['State'].get('ExitCode', 0),
                    'started_at': container['State'].get('StartedAt', ''),
                    'finished_at': container['State'].get('FinishedAt', ''),
                    'error': container['State'].get('Error', ''),
                },
                'config': {
                    'image': container['Config']['Image'],
                    'cmd': container['Config']['Cmd'],
                    'entrypoint': container['Config']['Entrypoint'],
                    'env': container['Config'].get('Env', []),
                    'labels': container['Config'].get('Labels', {}),
                    'working_dir': container['Config'].get('WorkingDir', ''),
                    'tty': container['Config'].get('Tty', False),
                    'open_stdin': container['Config'].get('OpenStdin', False),
                },
                'host_config': {
                    'network_mode': container['HostConfig'].get('NetworkMode', ''),
                    'restart_policy': container['HostConfig'].get('RestartPolicy', {}),
                    'port_bindings': container['HostConfig'].get('PortBindings', {}),
                    'binds': container['HostConfig'].get('Binds', []),
                    'memory': container['HostConfig'].get('Memory', 0),
                    'cpu_shares': container['HostConfig'].get('CpuShares', 0),
                    'privileged': container['HostConfig'].get('Privileged', False),
                },
                'network_settings': {
                    'networks': container['NetworkSettings'].get('Networks', {}),
                    'ports': container['NetworkSettings'].get('Ports', {}),
                    'ip_address': container['NetworkSettings'].get('IPAddress', ''),
                    'gateway': container['NetworkSettings'].get('Gateway', ''),
                    'mac_address': container['NetworkSettings'].get('MacAddress', ''),
                },
                'mounts': container.get('Mounts', []),
            }
        except Exception as e:
            logger.error(f"获取容器详情失败: {container_id} - {e}")
            return None
    
    def get_container_stats(
        self,
        container_id: str,
        stream: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取容器资源使用统计
        
        Args:
            container_id: 容器ID或名称
            stream: 是否流式输出
            
        Returns:
            资源统计
        """
        if not self._connected:
            return None
        
        try:
            stats = self._client.stats(container_id, stream=stream, decode=True)
            
            # 如果是generator，取第一条
            if hasattr(stats, '__iter__') and not isinstance(stats, dict):
                stats = next(iter(stats))
            
            return self._parse_stats(stats)
        except Exception as e:
            logger.error(f"获取容器统计失败: {container_id} - {e}")
            return None
    
    def _parse_stats(self, stats: Dict) -> Dict[str, Any]:
        """解析资源统计"""
        # CPU统计
        cpu_stats = stats.get('cpu_stats', {})
        pre_cpu_stats = stats.get('precpu_stats', {})
        
        cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                    pre_cpu_stats.get('cpu_usage', {}).get('total_usage', 0)
        system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                       pre_cpu_stats.get('system_cpu_usage', 0)
        
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(cpu_stats.get('cpu_usage', {}).get('percpu_usage', []))
        
        # 内存统计
        memory_stats = stats.get('memory_stats', {})
        memory_usage = memory_stats.get('usage', 0) - memory_stats.get('stats', {}).get('cache', 0)
        memory_limit = memory_stats.get('limit', 1)
        memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
        
        # 网络统计
        networks = stats.get('networks', {})
        network_rx = 0
        network_tx = 0
        for net_data in networks.values():
            network_rx += net_data.get('rx_bytes', 0)
            network_tx += net_data.get('tx_bytes', 0)
        
        # 块设备统计
        blkio_stats = stats.get('blkio_stats', {})
        io_service_bytes = blkio_stats.get('io_service_bytes_recursive', [])
        read_bytes = 0
        write_bytes = 0
        for entry in io_service_bytes:
            if entry.get('op', '').lower() == 'read':
                read_bytes += entry.get('value', 0)
            elif entry.get('op', '').lower() == 'write':
                write_bytes += entry.get('value', 0)
        
        return {
            'timestamp': stats.get('timestamp'),
            'cpu': {
                'usage': cpu_stats.get('cpu_usage', {}).get('total_usage', 0),
                'percent': cpu_percent,
                'online_cpus': cpu_stats.get('online_cpus', 0),
                'percpu_usage': cpu_stats.get('cpu_usage', {}).get('percpu_usage', []),
            },
            'memory': {
                'usage': memory_usage,
                'limit': memory_limit,
                'percent': memory_percent,
                'working_set': memory_stats.get('stats', {}).get('working_set', 0),
                'failcnt': memory_stats.get('failcnt', 0),
            },
            'network': {
                'rx_bytes': network_rx,
                'tx_bytes': network_tx,
                'rx_packets': sum(n.get('rx_packets', 0) for n in networks.values()),
                'tx_packets': sum(n.get('tx_packets', 0) for n in networks.values()),
                'rx_errors': sum(n.get('rx_errors', 0) for n in networks.values()),
                'tx_errors': sum(n.get('tx_errors', 0) for n in networks.values()),
            },
            'block_io': {
                'read_bytes': read_bytes,
                'write_bytes': write_bytes,
                'service_bytes_recursive': io_service_bytes,
            },
            'pids_stats': stats.get('pids_stats', {}),
        }
    
    def get_container_logs(
        self,
        container_id: str,
        stdout: bool = True,
        stderr: bool = True,
        tail: int = 100,
        since: Optional[str] = None
    ) -> str:
        """
        获取容器日志
        
        Args:
            container_id: 容器ID或名称
            stdout: 是否包含stdout
            stderr: 是否包含stderr
            tail: 返回最近N行
            since: 从指定时间戳获取日志
            
        Returns:
            日志内容
        """
        if not self._connected:
            return ''
        
        try:
            logs = self._client.logs(
                container_id,
                stdout=stdout,
                stderr=stderr,
                tail=tail,
                since=since,
                timestamps=True,
                stream=False,
            )
            
            return logs.decode('utf-8', errors='ignore') if isinstance(logs, bytes) else str(logs)
        except Exception as e:
            logger.error(f"获取容器日志失败: {container_id} - {e}")
            return ''
    
    def get_images(self, all: bool = False) -> List[Dict[str, Any]]:
        """
        获取镜像列表
        
        Args:
            all: 是否显示所有镜像（包括中间层）
            
        Returns:
            镜像列表
        """
        if not self._connected:
            return []
        
        try:
            images = self._client.images(all=all)
            
            return [{
                'id': img.get('Id', '')[:12],
                'full_id': img.get('Id', ''),
                'repo_tags': img.get('RepoTags', []),
                'repo_digests': img.get('RepoDigests', []),
                'created': img.get('Created', 0),
                'size': img.get('Size', 0),
                'virtual_size': img.get('VirtualSize', 0),
                'labels': img.get('Labels', {}),
            } for img in images]
        except Exception as e:
            logger.error(f"获取镜像列表失败: {e}")
            return []
    
    def get_networks(self) -> List[Dict[str, Any]]:
        """
        获取网络列表
        
        Returns:
            网络列表
        """
        if not self._connected:
            return []
        
        try:
            networks = self._client.networks()
            
            return [{
                'id': net.get('Id', '')[:12],
                'name': net.get('Name', ''),
                'driver': net.get('Driver', ''),
                'scope': net.get('Scope', ''),
                'internal': net.get('Internal', False),
                'attachable': net.get('Attachable', False),
                'labels': net.get('Labels', {}),
                'ipam': net.get('IPAM', {}),
                'containers': list(net.get('Containers', {}).keys()),
            } for net in networks]
        except Exception as e:
            logger.error(f"获取网络列表失败: {e}")
            return []
    
    def get_volumes(self) -> List[Dict[str, Any]]:
        """
        获取卷列表
        
        Returns:
            卷列表
        """
        if not self._connected:
            return []
        
        try:
            volumes = self._client.volumes()
            
            return [{
                'name': vol.get('Name', ''),
                'driver': vol.get('Driver', ''),
                'mountpoint': vol.get('Mountpoint', ''),
                'labels': vol.get('Labels', {}),
                'scope': vol.get('Scope', ''),
                'created': vol.get('CreatedAt', ''),
            } for vol in volumes.get('Volumes', [])]
        except Exception as e:
            logger.error(f"获取卷列表失败: {e}")
            return []
    
    def get_events(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        获取Docker事件
        
        Args:
            since: 起始时间
            until: 结束时间
            filters: 过滤条件
            
        Returns:
            事件列表
        """
        if not self._connected:
            return []
        
        try:
            events = self._client.events(
                since=since,
                until=until,
                filters=filters,
                decode=True,
            )
            
            return list(events)
        except Exception as e:
            logger.error(f"获取Docker事件失败: {e}")
            return []
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        采集所有Docker指标
        
        Returns:
            Docker指标数据
        """
        metrics = {
            'timestamp': None,
        }
        
        # 系统信息
        metrics['info'] = self.get_info()
        metrics['version'] = self.get_version()
        
        # 容器统计
        containers = self.get_containers(all=True)
        metrics['containers'] = {
            'total': len(containers),
            'running': len([c for c in containers if c.get('state') == 'running']),
            'paused': len([c for c in containers if c.get('state') == 'paused']),
            'stopped': len([c for c in containers if c.get('state') == 'exited']),
        }
        
        # 镜像统计
        images = self.get_images()
        metrics['images'] = {
            'total': len(images),
            'total_size': sum(img.get('size', 0) for img in images),
        }
        
        # 网络统计
        networks = self.get_networks()
        metrics['networks'] = {
            'total': len(networks),
            'by_driver': {},
        }
        for net in networks:
            driver = net.get('driver', 'unknown')
            metrics['networks']['by_driver'][driver] = metrics['networks']['by_driver'].get(driver, 0) + 1
        
        # 卷统计
        volumes = self.get_volumes()
        metrics['volumes'] = {
            'total': len(volumes),
        }
        
        # 容器资源使用
        metrics['container_stats'] = []
        for container in containers[:10]:  # 只采集前10个容器
            stats = self.get_container_stats(container['id'])
            if stats:
                metrics['container_stats'].append({
                    'name': container['names'][0] if container.get('names') else container['id'],
                    'id': container['id'],
                    'stats': stats,
                })
        
        return metrics
    
    def close(self) -> None:
        """关闭连接"""
        self._connected = False
        self._client = None
        logger.debug("Docker连接已关闭")


class DockerMetricsAggregator:
    """
    Docker指标聚合器
    
    聚合多个Docker主机的指标数据。
    """
    
    def __init__(self):
        self._clients: Dict[str, DockerClient] = {}
    
    def add_host(self, name: str, host: str, **kwargs) -> bool:
        """
        添加Docker主机
        
        Args:
            name: 主机名称
            host: 主机地址
            **kwargs: 其他参数
            
        Returns:
            是否成功
        """
        client = DockerClient(host=host, **kwargs)
        if client.connect():
            self._clients[name] = client
            return True
        return False
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有主机的指标
        
        Returns:
            聚合后的指标数据
        """
        aggregated = {
            'hosts': {},
            'totals': {
                'containers': 0,
                'running': 0,
                'images': 0,
                'networks': 0,
                'volumes': 0,
            }
        }
        
        for name, client in self._clients.items():
            try:
                metrics = client.collect_all_metrics()
                aggregated['hosts'][name] = metrics
                
                # 累加统计
                aggregated['totals']['containers'] += metrics.get('containers', {}).get('total', 0)
                aggregated['totals']['running'] += metrics.get('containers', {}).get('running', 0)
                aggregated['totals']['images'] += metrics.get('images', {}).get('total', 0)
                aggregated['totals']['networks'] += metrics.get('networks', {}).get('total', 0)
                aggregated['totals']['volumes'] += metrics.get('volumes', {}).get('total', 0)
            except Exception as e:
                logger.error(f"采集主机 {name} 指标失败: {e}")
        
        return aggregated
    
    def remove_host(self, name: str) -> None:
        """移除Docker主机"""
        if name in self._clients:
            self._clients[name].close()
            del self._clients[name]
    
    def close(self) -> None:
        """关闭所有连接"""
        for client in self._clients.values():
            client.close()
        self._clients.clear()
