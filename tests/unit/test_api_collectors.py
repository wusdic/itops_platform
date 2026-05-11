"""
API采集器综合测试
测试 Zabbix、Prometheus、Kubernetes API客户端的完整功能
"""

import unittest
import json
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestZabbixClientComplete(unittest.TestCase):
    """Zabbix客户端完整测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        client = ZabbixClient(
            url='http://test/zabbix/api_jsonrpc.php',
            user='admin',
            password='password',
            timeout=60
        )
        
        self.assertEqual(client.url, 'http://test/zabbix/api_jsonrpc.php')
        self.assertEqual(client.user, 'admin')
        self.assertEqual(client.timeout, 60)
        self.assertIsNone(client.auth_token)
    
    @patch('urllib.request.urlopen')
    def test_login_success(self, mock_urlopen):
        """测试登录成功"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': 'test-auth-token-12345',
            'id': 1
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        result = client.login()
        
        self.assertTrue(result)
        self.assertEqual(client.auth_token, 'test-auth-token-12345')
    
    @patch('urllib.request.urlopen')
    def test_login_failure(self, mock_urlopen):
        """测试登录失败"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'error': {'code': -32602, 'message': 'Invalid params', 'data': 'Login failed'},
            'id': 1
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        result = client.login()
        
        self.assertFalse(result)
        self.assertIsNone(client.auth_token)
    
    @patch('urllib.request.urlopen')
    def test_get_hosts(self, mock_urlopen):
        """测试获取主机列表"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': [
                {'hostid': '1', 'host': 'server1', 'name': 'Server 1', 'status': '0'},
                {'hostid': '2', 'host': 'server2', 'name': 'Server 2', 'status': '0'}
            ],
            'id': 2
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        hosts = client.host_get(output=['hostid', 'host', 'name'])
        
        self.assertEqual(len(hosts), 2)
        self.assertEqual(hosts[0]['host'], 'server1')
        self.assertEqual(hosts[1]['host'], 'server2')
    
    @patch('urllib.request.urlopen')
    def test_get_items(self, mock_urlopen):
        """测试获取监控项"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': [
                {'itemid': '1', 'name': 'CPU Usage', 'key_': 'system.cpu.util', 'lastvalue': '45.5'},
                {'itemid': '2', 'name': 'Memory Usage', 'key_': 'vm.memory.size', 'lastvalue': '2048'}
            ],
            'id': 3
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        items = client.item_get(hostids=['1'])
        
        self.assertEqual(len(items), 2)
    
    @patch('urllib.request.urlopen')
    def test_get_triggers(self, mock_urlopen):
        """测试获取触发器"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': [
                {
                    'triggerid': '1',
                    'description': 'High CPU',
                    'priority': '3',
                    'status': '0',
                    'value': '1'
                }
            ],
            'id': 4
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        triggers = client.trigger_get(only_true=True)
        
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]['description'], 'High CPU')
    
    @patch('urllib.request.urlopen')
    def test_history_get(self, mock_urlopen):
        """测试获取历史数据"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': [
                {'itemid': '1', 'clock': '1704067200', 'value': '45.5'},
                {'itemid': '1', 'clock': '1704067260', 'value': '46.0'}
            ],
            'id': 5
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        start_time = datetime.now() - timedelta(hours=1)
        history = client.history_get(
            itemids=['1'],
            history=0,
            start_time=start_time,
            limit=100
        )
        
        self.assertEqual(len(history), 2)
    
    @patch('urllib.request.urlopen')
    def test_host_create(self, mock_urlopen):
        """测试创建主机"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': {'hostids': ['100']},
            'id': 6
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        result = client.host_create(
            host='new-server',
            groups=[{'groupid': '1'}]
        )
        
        self.assertIn('hostids', result)
    
    @patch('urllib.request.urlopen')
    def test_logout(self, mock_urlopen):
        """测试登出"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': True,
            'id': 7
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        result = client.logout()
        
        self.assertTrue(result)
        self.assertIsNone(client.auth_token)
    
    def test_context_manager(self):
        """测试上下文管理器"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock login response
            mock_login = Mock()
            mock_login.read.return_value = json.dumps({
                'result': 'context-token'
            }).encode()
            mock_login.__enter__ = Mock(return_value=mock_login)
            mock_login.__exit__ = Mock(return_value=False)
            
            # Mock hosts response
            mock_hosts = Mock()
            mock_hosts.read.return_value = json.dumps({
                'result': [{'hostid': '1', 'host': 'server1'}]
            }).encode()
            mock_hosts.__enter__ = Mock(return_value=mock_hosts)
            mock_hosts.__exit__ = Mock(return_value=False)
            
            # Mock logout response
            mock_logout = Mock()
            mock_logout.read.return_value = json.dumps({
                'result': True
            }).encode()
            mock_logout.__enter__ = Mock(return_value=mock_logout)
            mock_logout.__exit__ = Mock(return_value=False)
            
            mock_urlopen.side_effect = [mock_login, mock_hosts, mock_logout]
            
            with ZabbixClient() as client:
                hosts = client.host_get(output=['hostid', 'host'])
                self.assertEqual(len(hosts), 1)
            
            self.assertIsNone(client.auth_token)


class TestPrometheusClientComplete(unittest.TestCase):
    """Prometheus客户端完整测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        client = PrometheusClient(
            url='http://test:9090',
            timeout=60
        )
        
        self.assertEqual(client.url, 'http://test:9090')
        self.assertEqual(client.timeout, 60)
        self.assertEqual(client._api_url, 'http://test:9090/api/v1')
    
    @patch('urllib.request.urlopen')
    def test_query_instant(self, mock_urlopen):
        """测试即时查询"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'job': 'test', 'instance': 'localhost:9100'},
                        'value': [1234567890.123, '1.0']
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.query('up{job="test"}')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['result']), 1)
    
    @patch('urllib.request.urlopen')
    def test_query_range(self, mock_urlopen):
        """测试范围查询"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'matrix',
                'result': [
                    {
                        'metric': {'job': 'test'},
                        'values': [
                            [1234567890.0, '100'],
                            [1234567900.0, '95']
                        ]
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        end = datetime.now()
        start = end - timedelta(hours=1)
        
        result = client.query_range(
            'up',
            start=start,
            end=end,
            step='1m'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['resultType'], 'matrix')
    
    @patch('urllib.request.urlopen')
    def test_get_all_metrics(self, mock_urlopen):
        """测试获取所有指标"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': ['up', 'process_cpu_seconds_total', 'node_memory_MemTotal_bytes']
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        metrics = client.get_all_metrics()
        
        self.assertEqual(len(metrics), 3)
        self.assertIn('up', metrics)
    
    @patch('urllib.request.urlopen')
    def test_targets(self, mock_urlopen):
        """测试获取Targets"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'activeTargets': [
                    {'job': 'node', 'instance': 'localhost:9100', 'health': 'up'}
                ],
                'droppedTargets': []
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.targets()
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['activeTargets']), 1)
    
    @patch('urllib.request.urlopen')
    def test_label_values(self, mock_urlopen):
        """测试获取标签值"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': ['prometheus', 'node', 'alertmanager']
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        values = client.label_values('job')
        
        self.assertEqual(len(values), 3)
        self.assertIn('prometheus', values)
    
    @patch('urllib.request.urlopen')
    def test_alerts(self, mock_urlopen):
        """测试获取告警"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'alerts': [
                    {'name': 'HighMemory', 'state': 'firing'},
                    {'name': 'HighCPU', 'state': 'pending'}
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        alerts = client.alerts()
        
        self.assertEqual(len(alerts), 2)
    
    @patch('urllib.request.urlopen')
    def test_rules(self, mock_urlopen):
        """测试获取规则"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'groups': [
                    {
                        'name': 'node_rules',
                        'file': 'rules.yml',
                        'rules': [{'name': 'HighMemory', 'type': 'alerting'}]
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.rules()
        
        self.assertEqual(result['status'], 'success')
    
    @patch('urllib.request.urlopen')
    def test_series(self, mock_urlopen):
        """测试查询序列"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': [
                {'__name__': 'up', 'job': 'node', 'instance': 'localhost:9100'}
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.series(['up{job="node"}'])
        
        self.assertEqual(len(result), 1)
    
    @patch('urllib.request.urlopen')
    def test_status_runtimeinfo(self, mock_urlopen):
        """测试获取运行时信息"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'version': '2.45.0',
                'revision': '8b4fc4f',
                'goVersion': 'go1.20'
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.status_runtimeinfo()
        
        self.assertEqual(result['status'], 'success')
    
    @patch('urllib.request.urlopen')
    def test_delete_series(self, mock_urlopen):
        """测试删除时间序列"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success'
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.delete_series(['up{job="test"}'])
        
        self.assertEqual(result['status'], 'success')
    
    def test_parse_instant_result(self):
        """测试即时结果解析"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        client = PrometheusClient()
        
        result = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {'metric': {'job': 'test'}, 'value': [1234567890.0, '100']}
                ]
            }
        }
        
        parsed = client._parse_instant_result(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['metric']['job'], 'test')
    
    def test_parse_range_result(self):
        """测试范围结果解析"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        client = PrometheusClient()
        
        result = {
            'status': 'success',
            'data': {
                'resultType': 'matrix',
                'result': [
                    {'metric': {'job': 'test'}, 'values': [[1234567890.0, '100']]}
                ]
            }
        }
        
        parsed = client._parse_range_result(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(len(parsed[0]['values']), 1)
    
    @patch('urllib.request.urlopen')
    def test_get_cpu_usage(self, mock_urlopen):
        """测试获取CPU使用率"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {'metric': {'instance': 'localhost:9100'}, 'value': [1234567890.0, '45.5']}
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.get_cpu_usage(instance='localhost:9100')
        
        self.assertEqual(len(result), 1)
    
    @patch('urllib.request.urlopen')
    def test_health_check(self, mock_urlopen):
        """测试健康检查"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success'
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        result = client.health_check()
        
        self.assertTrue(result)


class TestKubernetesClientComplete(unittest.TestCase):
    """Kubernetes客户端完整测试"""
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_client_initialization(self, mock_client, mock_config):
        """测试客户端初始化"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        k8s_client = K8sClient(
            host='192.168.1.100',
            port=6443,
            token='test-token'
        )
        
        self.assertEqual(k8s_client.host, '192.168.1.100')
        self.assertEqual(k8s_client.port, 6443)
        self.assertEqual(k8s_client.token, 'test-token')
        self.assertFalse(k8s_client._connected)
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_connect_with_token(self, mock_client, mock_config):
        """测试使用Token连接"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        mock_configuration = Mock()
        mock_client.Configuration.return_value = mock_configuration
        
        mock_api_client = Mock()
        mock_client.ApiClient.return_value = mock_api_client
        
        mock_core_v1 = Mock()
        mock_apps_v1 = Mock()
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.AppsV1Api.return_value = mock_apps_v1
        
        mock_core_v1.get_api_resources.return_value = Mock()
        
        k8s_client = K8sClient(
            host='192.168.1.100',
            port=6443,
            token='test-token'
        )
        
        result = k8s_client.connect()
        
        self.assertTrue(result)
        self.assertTrue(k8s_client._connected)
        self.assertIsNotNone(k8s_client._core_v1)
        self.assertIsNotNone(k8s_client._apps_v1)
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_get_nodes(self, mock_client, mock_config):
        """测试获取节点列表"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        mock_node = Mock()
        mock_node.metadata.name = 'node1'
        mock_node.metadata.uid = 'uid-123'
        mock_node.metadata.labels = {'node-role.kubernetes.io/master': 'true'}
        mock_node.metadata.annotations = {}
        mock_node.metadata.creation_timestamp = Mock()
        mock_node.status.capacity = {'cpu': '4', 'memory': '8Gi'}
        mock_node.status.allocatable = {'cpu': '4', 'memory': '8Gi'}
        mock_node.status.conditions = []
        mock_node.status.node_info = Mock()
        mock_node.status.node_info.machine_id = 'machine-123'
        
        mock_node_list = Mock()
        mock_node_list.items = [mock_node]
        
        mock_core_v1 = Mock()
        mock_core_v1.list_node.return_value = mock_node_list
        mock_client.CoreV1Api.return_value = mock_core_v1
        
        mock_client.ApiClient.return_value = Mock()
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._core_v1 = mock_core_v1
        
        nodes = k8s_client.get_nodes()
        
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'node1')
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_get_pods(self, mock_client, mock_config):
        """测试获取Pod列表"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        mock_pod = Mock()
        mock_pod.metadata.name = 'pod1'
        mock_pod.metadata.namespace = 'default'
        mock_pod.metadata.uid = 'pod-uid-123'
        mock_pod.metadata.labels = {'app': 'test'}
        mock_pod.metadata.annotations = {}
        mock_pod.metadata.creation_timestamp = Mock()
        mock_pod.status.phase = 'Running'
        mock_pod.status.pod_ip = '10.0.0.1'
        mock_pod.status.host_ip = '192.168.1.10'
        mock_pod.status.start_time = Mock()
        mock_pod.status.reason = None
        mock_pod.status.message = None
        mock_pod.status.conditions = []
        mock_pod.status.container_statuses = []
        mock_pod.spec.node_name = 'node1'
        mock_pod.spec.host_network = False
        mock_pod.spec.host_pid = False
        mock_pod.spec.host_ipc = False
        mock_pod.spec.containers = []
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        
        mock_core_v1 = Mock()
        mock_core_v1.list_pod_for_all_namespaces.return_value = mock_pod_list
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.ApiClient.return_value = Mock()
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._core_v1 = mock_core_v1
        
        pods = k8s_client.get_pods()
        
        self.assertEqual(len(pods), 1)
        self.assertEqual(pods[0]['name'], 'pod1')
        self.assertEqual(pods[0]['namespace'], 'default')
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_get_services(self, mock_client, mock_config):
        """测试获取Service列表"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        mock_svc = Mock()
        mock_svc.metadata.name = 'svc1'
        mock_svc.metadata.namespace = 'default'
        mock_svc.metadata.uid = 'svc-uid-123'
        mock_svc.metadata.labels = {'app': 'test'}
        mock_svc.spec.type = 'ClusterIP'
        mock_svc.spec.cluster_ip = '10.0.0.1'
        mock_svc.spec.external_i_ps = []
        mock_svc.spec.ports = []
        mock_svc.spec.selector = {'app': 'test'}
        mock_svc.metadata.creation_timestamp = Mock()
        
        mock_svc_list = Mock()
        mock_svc_list.items = [mock_svc]
        
        mock_core_v1 = Mock()
        mock_core_v1.list_service_for_all_namespaces.return_value = mock_svc_list
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.ApiClient.return_value = Mock()
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._core_v1 = mock_core_v1
        
        services = k8s_client.get_services()
        
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['name'], 'svc1')
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_get_namespaces(self, mock_client, mock_config):
        """测试获取命名空间"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        mock_ns = Mock()
        mock_ns.metadata.name = 'default'
        mock_ns.metadata.uid = 'ns-uid-123'
        mock_ns.metadata.labels = {}
        mock_ns.status.phase = 'Active'
        mock_ns.metadata.creation_timestamp = Mock()
        
        mock_ns_list = Mock()
        mock_ns_list.items = [mock_ns]
        
        mock_core_v1 = Mock()
        mock_core_v1.list_namespace.return_value = mock_ns_list
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.ApiClient.return_value = Mock()
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._core_v1 = mock_core_v1
        
        namespaces = k8s_client.get_namespaces()
        
        self.assertEqual(len(namespaces), 1)
        self.assertEqual(namespaces[0]['name'], 'default')
    
    @patch('modules.collection.api_collector.kubernetes_client.config')
    @patch('modules.collection.api_collector.kubernetes_client.client')
    def test_get_cluster_metrics(self, mock_client, mock_config):
        """测试获取集群指标"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        # Mock nodes
        mock_node = Mock()
        mock_node.metadata.name = 'node1'
        mock_node.metadata.labels = {'node-role.kubernetes.io/master': 'true'}
        mock_node.metadata.annotations = {}
        mock_node.metadata.creation_timestamp = None
        mock_node.status.capacity = {}
        mock_node.status.allocatable = {}
        mock_node.status.conditions = []
        mock_node.status.node_info = None
        
        # Mock pods
        mock_pod = Mock()
        mock_pod.metadata.name = 'pod1'
        mock_pod.metadata.namespace = 'default'
        mock_pod.metadata.uid = 'uid-1'
        mock_pod.metadata.labels = {}
        mock_pod.metadata.annotations = {}
        mock_pod.metadata.creation_timestamp = None
        mock_pod.status.phase = 'Running'
        mock_pod.status.pod_ip = '10.0.0.1'
        mock_pod.status.host_ip = '192.168.1.1'
        mock_pod.status.start_time = None
        mock_pod.status.reason = None
        mock_pod.status.message = None
        mock_pod.status.conditions = []
        mock_pod.status.container_statuses = []
        mock_pod.spec.node_name = 'node1'
        mock_pod.spec.host_network = False
        mock_pod.spec.host_pid = False
        mock_pod.spec.host_ipc = False
        mock_pod.spec.containers = []
        
        # Mock namespaces
        mock_ns = Mock()
        mock_ns.metadata.name = 'default'
        mock_ns.metadata.uid = 'ns-uid'
        mock_ns.metadata.labels = {}
        mock_ns.status.phase = 'Active'
        mock_ns.metadata.creation_timestamp = None
        
        mock_node_list = Mock()
        mock_node_list.items = [mock_node]
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        
        mock_ns_list = Mock()
        mock_ns_list.items = [mock_ns]
        
        mock_core_v1 = Mock()
        mock_core_v1.list_node.return_value = mock_node_list
        mock_core_v1.list_pod_for_all_namespaces.return_value = mock_pod_list
        mock_core_v1.list_namespace.return_value = mock_ns_list
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.ApiClient.return_value = Mock()
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._core_v1 = mock_core_v1
        
        metrics = k8s_client.get_cluster_metrics()
        
        self.assertIn('nodes', metrics)
        self.assertIn('pods', metrics)
        self.assertIn('namespaces', metrics)
        self.assertEqual(metrics['nodes']['total'], 1)
        self.assertEqual(metrics['pods']['total'], 1)
    
    def test_close(self):
        """测试关闭连接"""
        from modules.collection.api_collector.kubernetes_client import K8sClient
        
        k8s_client = K8sClient(host='192.168.1.100', token='test-token')
        k8s_client._connected = True
        k8s_client._api_client = Mock()
        k8s_client._core_v1 = Mock()
        k8s_client._apps_v1 = Mock()
        
        k8s_client.close()
        
        self.assertFalse(k8s_client._connected)
        self.assertIsNone(k8s_client._api_client)
        self.assertIsNone(k8s_client._core_v1)
        self.assertIsNone(k8s_client._apps_v1)


class TestDeviceMetricConfigModel(unittest.TestCase):
    """设备采集项配置模型测试"""
    
    def test_model_initialization(self):
        """测试模型初始化"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True,
            collect_interval=60,
            alert_thresholds='{"max": 90}',
            remark='Test config'
        )
        
        self.assertEqual(config.device_id, 1)
        self.assertEqual(config.device_name, 'test-server')
        self.assertEqual(config.metric_category, 'cpu')
        self.assertEqual(config.metric_name, 'cpu_usage')
        self.assertTrue(config.enabled)
        self.assertEqual(config.collect_interval, 60)
    
    def test_to_dict(self):
        """测试转换为字典"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from datetime import datetime
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True,
            collect_interval=60,
            alert_thresholds='{"max": 90}',
            remark='Test'
        )
        config.created_at = datetime(2024, 1, 1, 12, 0, 0)
        config.updated_at = datetime(2024, 1, 1, 12, 0, 0)
        
        result = config.to_dict()
        
        self.assertEqual(result['device_id'], 1)
        self.assertEqual(result['device_name'], 'test-server')
        self.assertEqual(result['metric_category'], 'cpu')
        self.assertEqual(result['metric_name'], 'cpu_usage')
        self.assertTrue(result['enabled'])
        self.assertEqual(result['collect_interval'], 60)
    
    def test_repr(self):
        """测试字符串表示"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True
        )
        
        repr_str = repr(config)
        self.assertIn('test-server', repr_str)
        self.assertIn('cpu_usage', repr_str)
        self.assertIn('enabled', repr_str)


if __name__ == '__main__':
    unittest.main()
