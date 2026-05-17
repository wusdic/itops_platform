# -*- coding: utf-8 -*-
"""
采集适配器工厂

统一管理多种采集协议和厂商设备，提供统一的采集接口
设备配置从 config/devices/*.yaml 加载，不硬编码敏感信息
"""

import logging
from typing import Any, Dict, List, Optional

from core.protocols import ProtocolType
from .api_collector.http_client import HTTPClient, VendorAPIClient, AuthType

logger = logging.getLogger(__name__)


class CollectorFactory:
    """
    采集适配器工厂
    
    根据设备配置自动选择合适的采集协议和客户端。
    设备配置从配置文件加载，支持热更新。
    
    使用示例:
    >>> factory = CollectorFactory()
    >>> # 创建设备采集器
    >>> collector = factory.create_collector(device_config)
    >>> # 执行采集
    >>> data = collector.collect()
    """
    
    def __init__(self):
        self._collectors: Dict[str, Any] = {}
    
    def create_collector(self, device_config: Dict[str, Any]):
        """
        根据设备配置创建采集器
        
        Args:
            device_config: 设备配置字典
            
        Returns:
            采集器实例
        """
        device_type = device_config.get('type', 'unknown')
        protocol = device_config.get('protocols', {}).get('primary', 'snmp')
        
        protocol_lower = protocol.lower()
        
        # 根据协议类型创建采集器
        if protocol_lower == 'snmp':
            return self._create_snmp_collector(device_config)
        elif protocol_lower == 'ssh':
            return self._create_ssh_collector(device_config)
        elif protocol_lower == 'winrm':
            return self._create_winrm_collector(device_config)
        elif protocol_lower == 'ipmi':
            return self._create_ipmi_collector(device_config)
        elif protocol_lower == 'http':
            return self._create_http_collector(device_config)
        elif protocol_lower == 'kubernetes':
            return self._create_kubernetes_collector(device_config)
        elif protocol_lower == 'docker':
            return self._create_docker_collector(device_config)
        elif protocol_lower == 'zabbix':
            return self._create_zabbix_collector(device_config)
        elif protocol_lower == 'prometheus':
            return self._create_prometheus_collector(device_config)
        elif protocol_lower == 'browser':
            return self._create_browser_collector(device_config)
        elif protocol_lower == 'redfish':
            return self._create_redfish_collector(device_config)
        elif protocol_lower == 'syslog':
            return self._create_syslog_collector(device_config)
        elif protocol_lower == 'telnet':
            return self._create_telnet_collector(device_config)
        elif protocol_lower == 'mysql':
            return self._create_mysql_collector(device_config)
        elif protocol_lower == 'postgres' or protocol_lower == 'postgresql':
            return self._create_postgres_collector(device_config)
        elif protocol_lower == 'redis':
            return self._create_redis_collector(device_config)
        elif protocol_lower == 'rabbitmq':
            return self._create_rabbitmq_collector(device_config)
        elif protocol_lower == 'kafka':
            return self._create_kafka_collector(device_config)
        elif protocol_lower == 'elasticsearch' or protocol_lower == 'es':
            return self._create_elasticsearch_collector(device_config)
        elif protocol_lower == 'vmware' or protocol_lower == 'vsphere':
            return self._create_vmware_collector(device_config)
        else:
            raise ValueError(f"不支持的协议: {protocol}")
    
    def _create_snmp_collector(self, device_config: Dict[str, Any]):
        """创建SNMP采集器"""
        from .snmp_collector.snmp_client import SNMPDevice, SNMPConfig, SNMPVersion
        
        credentials = device_config.get('credentials', {}).get('snmp', {})
        ip = device_config.get('ip', '')
        port = device_config.get('port', 161)
        
        version_str = credentials.get('version', 'v2c')
        version = SNMPVersion(version_str) if version_str else SNMPVersion.V2C
        
        config = SNMPConfig(
            host=ip,
            port=credentials.get('port', port),
            version=version,
            community=credentials.get('community', 'public'),
            timeout=credentials.get('timeout', 10),
        )
        
        return SNMPDevice(config)
    
    def _create_ssh_collector(self, device_config: Dict[str, Any]):
        """创建SSH采集器"""
        from .ssh_collector.ssh_client import SSHClient, SSHConfig
        
        credentials = device_config.get('credentials', {}).get('ssh', {})
        ip = device_config.get('ip', '')
        
        config = SSHConfig(
            host=ip,
            port=credentials.get('port', 22),
            username=credentials.get('username', 'root'),
            password=credentials.get('password', ''),
            key_file=credentials.get('key_file'),
            timeout=credentials.get('timeout', 30),
        )
        
        return SSHClient(config)
    
    def _create_winrm_collector(self, device_config: Dict[str, Any]):
        """创建WinRM采集器"""
        from .ssh_collector.winrm_client import WinRMClient, WinRMConfig
        
        credentials = device_config.get('credentials', {}).get('winrm', {})
        ip = device_config.get('ip', '')
        
        config = WinRMConfig(
            host=ip,
            port=credentials.get('port', 5985),
            username=credentials.get('username', 'Administrator'),
            password=credentials.get('password', ''),
            ssl=credentials.get('ssl', False),
        )
        
        return WinRMClient(config)
    
    def _create_ipmi_collector(self, device_config: Dict[str, Any]):
        """创建IPMI采集器"""
        from .ipmi_collector.ipmi_client import IPMIClient, IPMIConfig, IPMIVersion
        
        credentials = device_config.get('credentials', {}).get('ipmi', {})
        ip = device_config.get('ipmi_ip', device_config.get('ip', ''))
        
        cred_version = credentials.get('version', '2.0')
        # 规范化版本字符串: '2.0' -> 'v2.0', '1.5' -> 'v1.5'
        if not cred_version.startswith('v'):
            cred_version = 'v' + cred_version
        ipmi_version = IPMIVersion(cred_version) if cred_version else IPMIVersion.V2_0
        
        config = IPMIConfig(
            host=ip,
            port=credentials.get('port', 623),
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            version=ipmi_version,
        )
        
        return IPMIClient(config)
    
    def _create_http_collector(self, device_config: Dict[str, Any]):
        """创建HTTP API采集器"""
        from .api_collector.http_client import HTTPClient, VendorAPIClient
        from .api_collector.http_client import AuthType
        
        api_config = device_config.get('api', {})
        vendor = device_config.get('vendor', '')
        
        if vendor in ['zabbix', 'prometheus', 'topsec', 'nsfocus', 'sangfor', 'venustech', 'fortinet']:
            adapter = VendorAPIClient(
                vendor=vendor,
                host=device_config.get('ip', ''),
                port=api_config.get('port', 80),
                username=api_config.get('username'),
                password=api_config.get('password'),
                api_key=api_config.get('api_key'),
            )
            return adapter
        else:
            base_url = api_config.get('base_url', f"http://{device_config.get('ip')}")
            client = HTTPClient(base_url=base_url)
            
            if api_config.get('username'):
                client.set_auth(AuthType.BASIC, username=api_config['username'], password=api_config.get('password', ''))
            
            return client
    
    def _create_kubernetes_collector(self, device_config: Dict[str, Any]):
        """创建Kubernetes采集器"""
        from .api_collector.kubernetes_client import K8sClient
        
        k8s_config = device_config.get('kubernetes', {})
        
        return K8sClient(
            host=k8s_config.get('api_server', device_config.get('ip')),
            port=k8s_config.get('port', 6443),
            token=k8s_config.get('token', ''),
        )
    
    def _create_docker_collector(self, device_config: Dict[str, Any]):
        """创建Docker采集器"""
        from .api_collector.docker_client import DockerClient, DockerConfig
        
        credentials = device_config.get('credentials', {}).get('docker', {})
        docker_host = credentials.get('host', '')
        
        # 如果host已经是完整URL(tcp://或unix://)，直接使用；否则拼接
        if not docker_host.startswith('tcp://') and not docker_host.startswith('unix://'):
            docker_host = f"tcp://{device_config.get('ip')}:2375"
        
        config = DockerConfig(host=docker_host)
        
        return DockerClient(config)
    
    def _create_zabbix_collector(self, device_config: Dict[str, Any]):
        """创建Zabbix采集器"""
        from .api_collector.zabbix_client import ZabbixClient
        
        api_config = device_config.get('api', {})
        
        client = ZabbixClient(
            url=api_config.get('base_url'),
            user=api_config.get('username', 'Admin'),
            password=api_config.get('password', 'zabbix'),
        )
        
        return client
    
    def _create_prometheus_collector(self, device_config: Dict[str, Any]):
        """创建Prometheus采集器"""
        from .api_collector.prometheus_client import PrometheusClient
        
        api_config = device_config.get('api', {})
        
        return PrometheusClient(
            url=api_config.get('base_url', f"http://{device_config.get('ip')}:9090"),
        )
    
    def _create_browser_collector(self, device_config: Dict[str, Any]):
        """创建浏览器登录采集器"""
        from .browser_collector.browser_client import BrowserCollector, BrowserCollectorConfig
        
        credentials = device_config.get('credentials', {}).get('browser', {})
        ip = device_config.get('ip', '')
        port = device_config.get('port', 80)
        protocols_cfg = device_config.get('protocols', {})
        browser_cfg = protocols_cfg.get('browser', {})
        
        # 构造登录 URL
        scheme = 'https' if port == 443 else 'http'
        login_url = browser_cfg.get('login_url', f"{scheme}://{ip}:{port}/login")
        dashboard_url = browser_cfg.get('dashboard_url', f"{scheme}://{ip}:{port}/monitor")
        
        config = BrowserCollectorConfig(
            host=ip,
            port=port,
            protocol='https' if port == 443 else 'http',
            login_url=login_url,
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            username_field=browser_cfg.get('username_field', 'input[name="username"]'),
            password_field=browser_cfg.get('password_field', 'input[type="password"]'),
            submit_button=browser_cfg.get('submit_button', 'button[type="submit"]'),
            dashboard_url=dashboard_url,
            data_selectors=browser_cfg.get('data_selectors', {}),
            wait_after_login=browser_cfg.get('wait_after_login', 3000),
            verify_ssl=browser_cfg.get('verify_ssl', False),
            headless=browser_cfg.get('headless', True),
        )
        
        return BrowserCollector(config)

    def _create_redfish_collector(self, device_config: Dict[str, Any]):
        """创建Redfish采集器"""
        from .redfish_collector.redfish_client import RedfishCollector, RedfishConfig

        credentials = device_config.get('credentials', {}).get('redfish', {})
        ip = device_config.get('ip', '')
        port = device_config.get('redfish_port', 443)

        config = RedfishConfig(
            host=ip,
            port=port,
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            timeout=credentials.get('timeout', 30),
            ssl_verify=credentials.get('ssl_verify', False),
        )
        return RedfishCollector(config)

    def _create_syslog_collector(self, device_config: Dict[str, Any]):
        """创建Syslog采集器"""
        from .syslog_collector.syslog_client import SyslogCollector, SyslogConfig

        credentials = device_config.get('credentials', {}).get('syslog', {})
        ip = device_config.get('ip', '')
        syslog_cfg = device_config.get('syslog', {})

        config = SyslogConfig(
            host=ip,
            port=credentials.get('port', 514),
            protocol=syslog_cfg.get('protocol', 'UDP').upper(),
            timeout=credentials.get('timeout', 10),
        )
        return SyslogCollector(config)

    def _create_telnet_collector(self, device_config: Dict[str, Any]):
        """创建Telnet采集器"""
        from .telnet_collector.telnet_client import TelnetCollector, TelnetConfig

        credentials = device_config.get('credentials', {}).get('telnet', {})
        ip = device_config.get('ip', '')

        config = TelnetConfig(
            host=ip,
            port=credentials.get('port', 23),
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            timeout=credentials.get('timeout', 30),
            terminal_type=credentials.get('terminal_type', 'vt100'),
        )
        return TelnetCollector(config)

    def _create_mysql_collector(self, device_config: Dict[str, Any]):
        """创建MySQL采集器"""
        from .db_collector.mysql_client import MySQLCollector, MySQLConfig

        credentials = device_config.get('credentials', {}).get('mysql', {})
        ip = device_config.get('ip', '')
        db_cfg = device_config.get('database', {})

        config = MySQLConfig(
            host=ip,
            port=credentials.get('port', 3306),
            user=credentials.get('username', 'root'),
            password=credentials.get('password', ''),
            database=db_cfg.get('name', 'mysql'),
            connect_timeout=credentials.get('timeout', 30),
        )
        return MySQLCollector(config)

    def _create_postgres_collector(self, device_config: Dict[str, Any]):
        """创建PostgreSQL采集器"""
        from .db_collector.postgres_client import PostgreSQLCollector, PostgreSQLConfig

        credentials = device_config.get('credentials', {}).get('postgres', {})
        ip = device_config.get('ip', '')
        db_cfg = device_config.get('database', {})

        config = PostgreSQLConfig(
            host=ip,
            port=credentials.get('port', 5432),
            user=credentials.get('username', 'postgres'),
            password=credentials.get('password', ''),
            database=db_cfg.get('name', 'postgres'),
            connect_timeout=credentials.get('timeout', 30),
        )
        return PostgreSQLCollector(config)

    def _create_redis_collector(self, device_config: Dict[str, Any]):
        """创建Redis采集器"""
        from .mq_collector.redis_client import RedisCollector, RedisConfig

        credentials = device_config.get('credentials', {}).get('redis', {})
        ip = device_config.get('ip', '')

        config = RedisConfig(
            host=ip,
            port=credentials.get('port', 6379),
            password=credentials.get('password', ''),
            db=credentials.get('db', 0),
            socket_timeout=credentials.get('timeout', 10),
        )
        return RedisCollector(config)

    def _create_rabbitmq_collector(self, device_config: Dict[str, Any]):
        """创建RabbitMQ采集器"""
        from .mq_collector.rabbitmq_client import RabbitMQCollector, RabbitMQConfig

        credentials = device_config.get('credentials', {}).get('rabbitmq', {})
        ip = device_config.get('ip', '')

        config = RabbitMQConfig(
            host=ip,
            port=credentials.get('port', 15672),
            username=credentials.get('username', 'guest'),
            password=credentials.get('password', 'guest'),
            virtual_host=credentials.get('vhost', '/'),
            timeout=credentials.get('timeout', 30),
        )
        return RabbitMQCollector(config)

    def _create_kafka_collector(self, device_config: Dict[str, Any]):
        """创建Kafka采集器"""
        from .mq_collector.kafka_client import KafkaCollector, KafkaConfig

        credentials = device_config.get('credentials', {}).get('kafka', {})
        kafka_cfg = device_config.get('kafka', {})
        brokers = kafka_cfg.get('brokers', [])
        bootstrap = brokers[0] if brokers else f"{device_config.get('ip', '')}:9092"

        config = KafkaConfig(
            bootstrap_servers=bootstrap,
            consumer_group=kafka_cfg.get('consumer_group', ''),
            security_protocol=credentials.get('security_protocol', 'PLAINTEXT'),
            sasl_mechanism=credentials.get('sasl_mechanism'),
            sasl_plain_username=credentials.get('username'),
            sasl_plain_password=credentials.get('password'),
            request_timeout_ms=30 * 1000,
        )
        return KafkaCollector(config)

    def _create_elasticsearch_collector(self, device_config: Dict[str, Any]):
        """创建Elasticsearch采集器"""
        from .elasticsearch_collector.elasticsearch_client import ElasticsearchCollector, ElasticsearchConfig

        credentials = device_config.get('credentials', {}).get('elasticsearch', {})
        ip = device_config.get('ip', '')
        es_cfg = device_config.get('elasticsearch', {})

        config = ElasticsearchConfig(
            hosts=[f"http://{ip}:{credentials.get('port', 9200)}"],
            username=credentials.get('username', 'elastic'),
            password=credentials.get('password', ''),
            index_pattern=es_cfg.get('index_pattern', 'logstash-*'),
            timeout=credentials.get('timeout', 30),
        )
        return ElasticsearchCollector(config)

    def _create_vmware_collector(self, device_config: Dict[str, Any]):
        """创建VMware vSphere采集器"""
        from .vmware_collector.vmware_client import VMwareCollector, VMwareConfig

        credentials = device_config.get('credentials', {}).get('vmware', {})
        ip = device_config.get('ip', '')

        config = VMwareConfig(
            host=ip,
            port=credentials.get('port', 443),
            user=credentials.get('username', 'administrator@vsphere.local'),
            password=credentials.get('password', ''),
        )
        return VMwareCollector(config)

    def register_collector(self, name: str, collector: Any) -> None:
        """注册采集器实例"""
        self._collectors[name] = collector
    
    def get_collector(self, name: str) -> Optional[Any]:
        """获取已注册的采集器"""
        return self._collectors.get(name)
    
    def remove_collector(self, name: str) -> None:
        """移除采集器"""
        if name in self._collectors:
            del self._collectors[name]


# 全局工厂实例
_factory: Optional[CollectorFactory] = None


def get_factory() -> CollectorFactory:
    """获取全局采集器工厂"""
    global _factory
    if _factory is None:
        _factory = CollectorFactory()
    return _factory
