"""
Kubernetes API客户端
支持Kubernetes集群监控，采集Pod、Service、Node等资源数据
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from kubernetes import client, config
    from kubernetes.client import ApiClient
    _kubernetes_available = True
except ImportError:
    _kubernetes_available = False
    client = None
    config = None


class K8sClient:
    """
    Kubernetes API客户端
    
    用于监控Kubernetes集群资源。
    
    支持:
    - Node监控
    - Pod监控
    - Service监控
    - Deployment监控
    - PersistentVolume监控
    - 资源配额监控
    - Events监控
    
    使用示例:
    >>> client = K8sClient()  # 使用本地kubeconfig
    >>> client.connect()
    >>> nodes = client.get_nodes()
    >>> pods = client.get_pods()
    >>> client.close()
    """
    
    def __init__(self, host: str = '', port: int = 6443, token: str = '', **kwargs):
        """
        初始化K8s客户端
        
        Args:
            host: API Server地址
            port: API Server端口
            token: Bearer Token认证
            **kwargs: 其他参数 (kubeconfig路径, context等)
        """
        self.host = host
        self.port = port
        self.token = token
        self._api_client: Optional[ApiClient] = None
        self._core_v1: Optional[Any] = None
        self._apps_v1: Optional[Any] = None
        self._connected = False
        self._kwargs = kwargs
    
    def connect(self) -> bool:
        """
        连接Kubernetes集群
        
        Returns:
            连接是否成功
        """
        if not _kubernetes_available:
            logger.error("kubernetes模块未安装，请执行: pip install kubernetes")
            return False
        
        try:
            if self.host:
                # 使用API Server地址连接
                configuration = client.Configuration()
                configuration.host = f"https://{self.host}:{self.port}"
                configuration.verify_ssl = self._kwargs.get('ssl_verify', True)
                
                if self.token:
                    configuration.api_key['authorization'] = f'Bearer {self.token}'
                elif self._kwargs.get('cert_file') and self._kwargs.get('key_file'):
                    configuration.cert_file = self._kwargs['cert_file']
                    configuration.key_file = self._kwargs['key_file']
                
                self._api_client = ApiClient(configuration)
            else:
                # 使用kubeconfig连接本地集群
                try:
                    config.load_kube_config(
                        config_file=self._kwargs.get('kubeconfig'),
                        context=self._kwargs.get('context')
                    )
                except:
                    # 尝试加载 incluster配置
                    config.load_incluster_config()
                
                self._api_client = client.ApiClient()
            
            self._core_v1 = client.CoreV1Api(self._api_client)
            self._apps_v1 = client.AppsV1Api(self._api_client)
            
            # 测试连接
            self._core_v1.get_api_resources()
            self._connected = True
            logger.info(f"K8s连接成功: {self.host or 'local'}")
            return True
            
        except Exception as e:
            logger.error(f"K8s连接失败: {e}")
            self._connected = False
            return False
    
    def get_nodes(self, label_selector: str = '') -> List[Dict[str, Any]]:
        """
        获取节点列表
        
        Args:
            label_selector: 标签选择器 (如 'node-role.kubernetes.io/master')
            
        Returns:
            节点列表
        """
        if not self._connected:
            return []
        
        try:
            nodes = self._core_v1.list_node(
                label_selector=label_selector,
                timeout_seconds=30
            )
            
            result = []
            for node in nodes.items:
                result.append(self._parse_node(node))
            
            return result
        except Exception as e:
            logger.error(f"获取节点失败: {e}")
            return []
    
    def _parse_node(self, node) -> Dict[str, Any]:
        """解析节点数据"""
        return {
            'name': node.metadata.name,
            'uid': node.metadata.uid,
            'labels': node.metadata.labels or {},
            'annotations': node.metadata.annotations or {},
            'creation_timestamp': str(node.metadata.creation_timestamp) if node.metadata.creation_timestamp else None,
            'status': {
                'capacity': self._parse_resource_list(node.status.capacity) if node.status and node.status.capacity else {},
                'allocatable': self._parse_resource_list(node.status.allocatable) if node.status and node.status.allocatable else {},
                'conditions': self._parse_conditions(node.status.conditions) if node.status and node.status.conditions else [],
                'node_info': {
                    'machine_id': node.status.node_info.machine_id if node.status and node.status.node_info else None,
                    'system_uuid': node.status.node_info.system_uuid if node.status and node.status.node_info else None,
                    'boot_id': node.status.node_info.boot_id if node.status and node.status.node_info else None,
                    'kernel_version': node.status.node_info.kernel_version if node.status and node.status.node_info else None,
                    'os_image': node.status.node_info.os_image if node.status and node.status.node_info else None,
                    'container_runtime_version': node.status.node_info.container_runtime_version if node.status and node.status.node_info else None,
                    'kubelet_version': node.status.node_info.kubelet_version if node.status and node.status.node_info else None,
                    'kube_proxy_version': node.status.node_info.kube_proxy_version if node.status and node.status.node_info else None,
                    'operating_system': node.status.node_info.operating_system if node.status and node.status.node_info else None,
                    'architecture': node.status.node_info.architecture if node.status and node.status.node_info else None,
                }
            }
        }
    
    def _parse_resource_list(self, resource_list) -> Dict[str, Any]:
        """解析资源列表"""
        result = {}
        if resource_list:
            for key, value in resource_list.items():
                result[key] = str(value)
        return result
    
    def _parse_conditions(self, conditions) -> List[Dict[str, Any]]:
        """解析节点状态"""
        result = []
        if conditions:
            for cond in conditions:
                result.append({
                    'type': cond.type,
                    'status': cond.status,
                    'reason': cond.reason,
                    'message': cond.message,
                    'last_transition_time': str(cond.last_transition_time) if cond.last_transition_time else None,
                })
        return result
    
    def get_pods(self, namespace: str = '', label_selector: str = '') -> List[Dict[str, Any]]:
        """
        获取Pod列表
        
        Args:
            namespace: 命名空间，为空表示所有命名空间
            label_selector: 标签选择器
            
        Returns:
            Pod列表
        """
        if not self._connected:
            return []
        
        try:
            if namespace:
                pods = self._core_v1.list_namespaced_pod(
                    namespace,
                    label_selector=label_selector,
                    timeout_seconds=30
                )
            else:
                pods = self._core_v1.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                    timeout_seconds=30
                )
            
            result = []
            for pod in pods.items:
                result.append(self._parse_pod(pod))
            
            return result
        except Exception as e:
            logger.error(f"获取Pod失败: {e}")
            return []
    
    def _parse_pod(self, pod) -> Dict[str, Any]:
        """解析Pod数据"""
        return {
            'name': pod.metadata.name,
            'namespace': pod.metadata.namespace,
            'uid': pod.metadata.uid,
            'labels': pod.metadata.labels or {},
            'annotations': pod.metadata.annotations or {},
            'creation_timestamp': str(pod.metadata.creation_timestamp) if pod.metadata.creation_timestamp else None,
            'status': {
                'phase': pod.status.phase if pod.status else None,
                'pod_ip': pod.status.pod_ip if pod.status else None,
                'host_ip': pod.status.host_ip if pod.status else None,
                'start_time': str(pod.status.start_time) if pod.status and pod.status.start_time else None,
                'reason': pod.status.reason if pod.status else None,
                'message': pod.status.message if pod.status else None,
                'conditions': self._parse_pod_conditions(pod.status.conditions) if pod.status and pod.status.conditions else [],
                'container_statuses': self._parse_container_statuses(pod.status.container_statuses) if pod.status and pod.status.container_statuses else [],
            },
            'spec': {
                'node_name': pod.spec.node_name if pod.spec else None,
                'host_network': pod.spec.host_network if pod.spec else None,
                'host_pid': pod.spec.host_pid if pod.spec else None,
                'host_ipc': pod.spec.host_ipc if pod.spec else None,
                'containers': [self._parse_container(c) for c in pod.spec.containers] if pod.spec and pod.spec.containers else [],
            }
        }
    
    def _parse_pod_conditions(self, conditions) -> List[Dict[str, Any]]:
        """解析Pod状态条件"""
        result = []
        if conditions:
            for cond in conditions:
                result.append({
                    'type': cond.type,
                    'status': cond.status,
                    'reason': cond.reason,
                    'message': cond.message,
                    'last_transition_time': str(cond.last_transition_time) if cond.last_transition_time else None,
                })
        return result
    
    def _parse_container_statuses(self, statuses) -> List[Dict[str, Any]]:
        """解析容器状态"""
        result = []
        if statuses:
            for status in statuses:
                result.append({
                    'name': status.name,
                    'state': {
                        'running': status.state.running.started_at.isoformat() if status.state and status.state.running else None,
                        'waiting': {
                            'reason': status.state.waiting.reason if status.state and status.state.waiting else None,
                            'message': status.state.waiting.message if status.state and status.state.waiting else None,
                        } if status.state and status.state.waiting else None,
                        'terminated': {
                            'exit_code': status.state.terminated.exit_code if status.state and status.state.terminated else None,
                            'reason': status.state.terminated.reason if status.state and status.state.terminated else None,
                            'started_at': status.state.terminated.started_at.isoformat() if status.state and status.state.terminated else None,
                            'finished_at': status.state.terminated.finished_at.isoformat() if status.state and status.state.terminated else None,
                        } if status.state and status.state.terminated else None,
                    },
                    'last_state': {
                        'terminated': {
                            'exit_code': status.last_state.terminated.exit_code if status.last_state and status.last_state.terminated else None,
                            'reason': status.last_state.terminated.reason if status.last_state and status.last_state.terminated else None,
                        } if status.last_state and status.last_state.terminated else None,
                    } if status.last_state else None,
                    'ready': status.ready,
                    'restart_count': status.restart_count,
                    'image': status.image,
                    'image_id': status.image_id,
                })
        return result
    
    def _parse_container(self, container) -> Dict[str, Any]:
        """解析容器规格"""
        return {
            'name': container.name,
            'image': container.image,
            'image_pull_policy': container.image_pull_policy,
            'command': container.command,
            'args': container.args,
            'ports': [{'container_port': p.container_port, 'protocol': p.protocol} for p in container.ports] if container.ports else [],
            'env': [{'name': e.name, 'value': e.value} for e in container.env] if container.env else [],
            'resources': {
                'limits': {k: str(v) for k, v in container.resources.limits.items()} if container.resources and container.resources.limits else {},
                'requests': {k: str(v) for k, v in container.resources.requests.items()} if container.resources and container.resources.requests else {},
            },
        }
    
    def get_services(self, namespace: str = '') -> List[Dict[str, Any]]:
        """
        获取Service列表
        
        Args:
            namespace: 命名空间
            
        Returns:
            Service列表
        """
        if not self._connected:
            return []
        
        try:
            if namespace:
                services = self._core_v1.list_namespaced_service(namespace, timeout_seconds=30)
            else:
                services = self._core_v1.list_service_for_all_namespaces(timeout_seconds=30)
            
            result = []
            for svc in services.items:
                result.append({
                    'name': svc.metadata.name,
                    'namespace': svc.metadata.namespace,
                    'uid': svc.metadata.uid,
                    'labels': svc.metadata.labels or {},
                    'type': svc.spec.type if svc.spec else None,
                    'cluster_ip': svc.spec.cluster_ip if svc.spec else None,
                    'external_ip': svc.spec.external_i_ps if svc.spec else None,
                    'ports': [{'port': p.port, 'target_port': str(p.target_port), 'protocol': p.protocol} for p in svc.spec.ports] if svc.spec and svc.spec.ports else [],
                    'selector': svc.spec.selector or {},
                    'creation_timestamp': str(svc.metadata.creation_timestamp) if svc.metadata.creation_timestamp else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取Service失败: {e}")
            return []
    
    def get_deployments(self, namespace: str = '') -> List[Dict[str, Any]]:
        """
        获取Deployment列表
        
        Args:
            namespace: 命名空间
            
        Returns:
            Deployment列表
        """
        if not self._connected:
            return []
        
        try:
            if namespace:
                deploys = self._apps_v1.list_namespaced_deployment(namespace, timeout_seconds=30)
            else:
                deploys = self._apps_v1.list_deployment_for_all_namespaces(timeout_seconds=30)
            
            result = []
            for deploy in deploys.items:
                result.append({
                    'name': deploy.metadata.name,
                    'namespace': deploy.metadata.namespace,
                    'uid': deploy.metadata.uid,
                    'labels': deploy.metadata.labels or {},
                    'replicas': {
                        'desired': deploy.spec.replicas if deploy.spec else 0,
                        'ready': deploy.status.ready_replicas if deploy.status else 0,
                        'available': deploy.status.available_replicas if deploy.status else 0,
                        'updated': deploy.status.updated_replicas if deploy.status else 0,
                    },
                    'conditions': [{
                        'type': c.type,
                        'status': c.status,
                        'reason': c.reason,
                        'message': c.message,
                    } for c in (deploy.status.conditions or [])],
                    'creation_timestamp': str(deploy.metadata.creation_timestamp) if deploy.metadata.creation_timestamp else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取Deployment失败: {e}")
            return []
    
    def get_namespaces(self) -> List[Dict[str, Any]]:
        """
        获取命名空间列表
        
        Returns:
            命名空间列表
        """
        if not self._connected:
            return []
        
        try:
            namespaces = self._core_v1.list_namespace(timeout_seconds=30)
            
            result = []
            for ns in namespaces.items:
                result.append({
                    'name': ns.metadata.name,
                    'uid': ns.metadata.uid,
                    'labels': ns.metadata.labels or {},
                    'status': ns.status.phase if ns.status else None,
                    'creation_timestamp': str(ns.metadata.creation_timestamp) if ns.metadata.creation_timestamp else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取命名空间失败: {e}")
            return []
    
    def get_events(self, namespace: str = '', **kwargs) -> List[Dict[str, Any]]:
        """
        获取事件列表
        
        Args:
            namespace: 命名空间
            **kwargs: 其他过滤参数
            
        Returns:
            事件列表
        """
        if not self._connected:
            return []
        
        try:
            if namespace:
                events = self._core_v1.list_namespaced_event(namespace, timeout_seconds=30)
            else:
                events = self._core_v1.list_event_for_all_namespaces(timeout_seconds=30)
            
            result = []
            for event in events.items:
                result.append({
                    'name': event.metadata.name,
                    'namespace': event.metadata.namespace,
                    'type': event.type,
                    'reason': event.reason,
                    'message': event.message,
                    'involved_object': {
                        'kind': event.involved_object.kind if event.involved_object else None,
                        'name': event.involved_object.name if event.involved_object else None,
                        'uid': event.involved_object.uid if event.involved_object else None,
                    },
                    'source': {
                        'component': event.source.component if event.source else None,
                        'host': event.source.host if event.source else None,
                    },
                    'first_timestamp': str(event.first_timestamp) if event.first_timestamp else None,
                    'last_timestamp': str(event.last_timestamp) if event.last_timestamp else None,
                    'count': event.count,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return []
    
    def get_persistent_volumes(self) -> List[Dict[str, Any]]:
        """
        获取PersistentVolume列表
        
        Returns:
            PV列表
        """
        if not self._connected:
            return []
        
        try:
            pvs = self._core_v1.list_persistent_volume(timeout_seconds=30)
            
            result = []
            for pv in pvs.items:
                result.append({
                    'name': pv.metadata.name,
                    'uid': pv.metadata.uid,
                    'labels': pv.metadata.labels or {},
                    'status': pv.status.phase if pv.status else None,
                    'capacity': {k: str(v) for k, v in (pv.spec.capacity or {}).items()},
                    'access_modes': pv.spec.access_modes or [],
                    'claim_ref': {
                        'namespace': pv.spec.claim_ref.namespace if pv.spec and pv.spec.claim_ref else None,
                        'name': pv.spec.claim_ref.name if pv.spec and pv.spec.claim_ref else None,
                    } if pv.spec and pv.spec.claim_ref else None,
                    'creation_timestamp': str(pv.metadata.creation_timestamp) if pv.metadata.creation_timestamp else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取PV失败: {e}")
            return []
    
    def get_resource_quota(self, namespace: str = '') -> List[Dict[str, Any]]:
        """
        获取资源配额
        
        Args:
            namespace: 命名空间
            
        Returns:
            资源配额列表
        """
        if not self._connected:
            return []
        
        try:
            if namespace:
                quotas = self._core_v1.list_namespaced_resource_quota(namespace, timeout_seconds=30)
            else:
                quotas = self._core_v1.list_resource_quota_for_all_namespaces(timeout_seconds=30)
            
            result = []
            for quota in quotas.items:
                result.append({
                    'name': quota.metadata.name,
                    'namespace': quota.metadata.namespace,
                    'labels': quota.metadata.labels or {},
                    'status': {
                        'hard': {k: str(v) for k, v in (quota.status.hard or {}).items()},
                        'used': {k: str(v) for k, v in (quota.status.used or {}).items()},
                    },
                    'creation_timestamp': str(quota.metadata.creation_timestamp) if quota.metadata.creation_timestamp else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"获取资源配额失败: {e}")
            return []
    
    def get_cluster_metrics(self) -> Dict[str, Any]:
        """
        获取集群指标
        
        Returns:
            集群指标
        """
        metrics = {
            'timestamp': None,
        }
        
        # 节点统计
        nodes = self.get_nodes()
        metrics['nodes'] = {
            'total': len(nodes),
            'master': len([n for n in nodes if 'node-role.kubernetes.io/master' in n.get('labels', {})]),
            'worker': len([n for n in nodes if 'node-role.kubernetes.io/worker' in n.get('labels', {})]),
        }
        
        # Pod统计
        pods = self.get_pods()
        metrics['pods'] = {
            'total': len(pods),
            'running': len([p for p in pods if p.get('status', {}).get('phase') == 'Running']),
            'pending': len([p for p in pods if p.get('status', {}).get('phase') == 'Pending']),
            'failed': len([p for p in pods if p.get('status', {}).get('phase') == 'Failed']),
        }
        
        # 命名空间统计
        namespaces = self.get_namespaces()
        metrics['namespaces'] = {
            'total': len(namespaces),
            'active': len([ns for ns in namespaces if ns.get('status') == 'Active']),
        }
        
        return metrics
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        采集所有K8s指标
        
        Returns:
            K8s指标数据
        """
        metrics = {
            'cluster': self.get_cluster_metrics(),
            'nodes': self.get_nodes(),
            'namespaces': self.get_namespaces(),
            'pods': self.get_pods(),
            'services': self.get_services(),
            'deployments': self.get_deployments(),
            'events': self.get_events()[:50],  # 只取最近50条事件
        }
        
        return metrics
    
    def close(self) -> None:
        """关闭连接"""
        self._connected = False
        self._api_client = None
        self._core_v1 = None
        self._apps_v1 = None
        logger.debug("K8s连接已关闭")


class K8sMetricsCollector:
    """
    Kubernetes指标采集器
    
    专门用于采集Prometheus格式的K8s指标。
    需要kube-state-metrics组件支持。
    """
    
    def __init__(self, k8s_client: K8sClient, metrics_endpoint: str = ''):
        """
        初始化K8s指标采集器
        
        Args:
            k8s_client: K8sClient实例
            metrics_endpoint: kube-state-metrics服务地址
        """
        self._client = k8s_client
        self._metrics_endpoint = metrics_endpoint or 'http://kube-state-metrics:8080/metrics'
    
    def collect(self) -> Dict[str, Any]:
        """
        采集K8s指标
        
        Returns:
            K8s指标数据
        """
        # 基础资源数据
        resources = {
            'nodes': self._client.get_nodes(),
            'pods': self._client.get_pods(),
            'deployments': self._client.get_deployments(),
            'services': self._client.get_services(),
            'namespaces': self._client.get_namespaces(),
        }
        
        # 计算聚合指标
        metrics = {
            'resources': resources,
            'aggregations': self._aggregate_metrics(resources),
        }
        
        return metrics
    
    def _aggregate_metrics(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """聚合指标计算"""
        aggregations = {
            'node_summary': self._summarize_nodes(resources.get('nodes', [])),
            'pod_summary': self._summarize_pods(resources.get('pods', [])),
            'workload_summary': self._summarize_workloads(resources.get('deployments', [])),
        }
        return aggregations
    
    def _summarize_nodes(self, nodes: List[Dict]) -> Dict[str, Any]:
        """节点汇总"""
        return {
            'total': len(nodes),
            'by_role': self._count_by_label(nodes, 'node-role.kubernetes.io/master'),
        }
    
    def _summarize_pods(self, pods: List[Dict]) -> Dict[str, Any]:
        """Pod汇总"""
        phases = {}
        for pod in pods:
            phase = pod.get('status', {}).get('phase', 'Unknown')
            phases[phase] = phases.get(phase, 0) + 1
        
        return {
            'total': len(pods),
            'by_phase': phases,
        }
    
    def _summarize_workloads(self, deployments: List[Dict]) -> Dict[str, Any]:
        """工作负载汇总"""
        return {
            'total': len(deployments),
            'ready_replicas': sum(d.get('replicas', {}).get('ready', 0) for d in deployments),
            'desired_replicas': sum(d.get('replicas', {}).get('desired', 0) for d in deployments),
        }
    
    def _count_by_label(self, items: List[Dict], label: str) -> Dict[str, int]:
        """按标签计数"""
        counts = {}
        for item in items:
            labels = item.get('labels', {})
            if label in labels:
                value = labels[label]
                counts[value] = counts.get(value, 0) + 1
        return counts
