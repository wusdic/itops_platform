"""初始化协议适配器数据库"""

import logging
from sqlalchemy import text

from modules.foundation.db_models.adapter import AdapterTemplate, DeviceProtocolConfig
from api.dependencies import get_db

logger = logging.getLogger(__name__)


# 20个协议的默认模板
DEFAULT_ADAPTERS = [
    {
        "protocol_type": "snmp",
        "name": "SNMP通用模板",
        "description": "适用于交换机、路由器、UPS等支持SNMP的设备",
        "default_config": {
            "port": 161,
            "version": "v2c",
            "community": "public",
            "timeout": 10,
        }
    },
    {
        "protocol_type": "ssh",
        "name": "SSH通用模板",
        "description": "适用于Linux/Unix服务器SSH命令行采集",
        "default_config": {
            "port": 22,
            "username": "root",
            "password": "",
            "key_file": None,
            "timeout": 30,
        }
    },
    {
        "protocol_type": "http",
        "name": "HTTP通用模板",
        "description": "适用于Web管理界面的REST API采集",
        "default_config": {
            "port": 80,
            "base_url": "",
            "username": "admin",
            "password": "",
            "ssl_verify": False,
            "timeout": 30,
        }
    },
    {
        "protocol_type": "winrm",
        "name": "WinRM模板",
        "description": "适用于Windows服务器远程管理",
        "default_config": {
            "port": 5985,
            "username": "Administrator",
            "password": "",
            "ssl": False,
            "timeout": 30,
        }
    },
    {
        "protocol_type": "ipmi",
        "name": "IPMI模板",
        "description": "适用于服务器BMC带外管理",
        "default_config": {
            "port": 623,
            "version": "v2.0",
            "username": "admin",
            "password": "",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "kubernetes",
        "name": "Kubernetes模板",
        "description": "适用于K8s集群API Server采集",
        "default_config": {
            "port": 6443,
            "api_server": "",
            "token": "",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "docker",
        "name": "Docker模板",
        "description": "适用于Docker Daemon API采集",
        "default_config": {
            "port": 2375,
            "host": "",
            "tls_verify": False,
            "timeout": 30,
        }
    },
    {
        "protocol_type": "zabbix",
        "name": "Zabbix模板",
        "description": "适用于Zabbix监控系统",
        "default_config": {
            "port": 80,
            "base_url": "",
            "username": "Admin",
            "password": "zabbix",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "prometheus",
        "name": "Prometheus模板",
        "description": "适用于Prometheus监控指标采集",
        "default_config": {
            "port": 9090,
            "base_url": "",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "browser",
        "name": "浏览器采集模板",
        "description": "适用于需要浏览器登录才能访问的Web系统",
        "default_config": {
            "port": 80,
            "protocol": "http",
            "login_url": "",
            "username": "admin",
            "password": "",
            "username_field": "input[name=\"username\"]",
            "password_field": "input[type=\"password\"]",
            "submit_button": "button[type=\"submit\"]",
            "dashboard_url": "",
            "wait_after_login": 3000,
            "verify_ssl": False,
            "headless": True,
        }
    },
    {
        "protocol_type": "redfish",
        "name": "Redfish模板",
        "description": "适用于支持Redfish标准接口的服务器",
        "default_config": {
            "port": 443,
            "username": "admin",
            "password": "",
            "timeout": 30,
            "ssl_verify": False,
        }
    },
    {
        "protocol_type": "syslog",
        "name": "Syslog模板",
        "description": "适用于日志服务器接收syslog",
        "default_config": {
            "port": 514,
            "protocol": "UDP",
            "timeout": 10,
        }
    },
    {
        "protocol_type": "telnet",
        "name": "Telnet模板",
        "description": "适用于老旧设备的Telnet采集",
        "default_config": {
            "port": 23,
            "username": "admin",
            "password": "",
            "timeout": 30,
            "terminal_type": "vt100",
        }
    },
    {
        "protocol_type": "mysql",
        "name": "MySQL模板",
        "description": "适用于MySQL数据库监控",
        "default_config": {
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "mysql",
            "connect_timeout": 30,
        }
    },
    {
        "protocol_type": "postgres",
        "name": "PostgreSQL模板",
        "description": "适用于PostgreSQL数据库监控",
        "default_config": {
            "port": 5432,
            "user": "postgres",
            "password": "",
            "database": "postgres",
            "connect_timeout": 30,
        }
    },
    {
        "protocol_type": "redis",
        "name": "Redis模板",
        "description": "适用于Redis缓存服务器监控",
        "default_config": {
            "port": 6379,
            "password": "",
            "db": 0,
            "socket_timeout": 10,
        }
    },
    {
        "protocol_type": "rabbitmq",
        "name": "RabbitMQ模板",
        "description": "适用于RabbitMQ消息队列监控",
        "default_config": {
            "port": 15672,
            "username": "guest",
            "password": "guest",
            "vhost": "/",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "kafka",
        "name": "Kafka模板",
        "description": "适用于Kafka消息队列监控",
        "default_config": {
            "port": 9092,
            "brokers": [],
            "consumer_group": "",
            "security_protocol": "PLAINTEXT",
            "sasl_mechanism": None,
            "username": None,
            "password": None,
        }
    },
    {
        "protocol_type": "elasticsearch",
        "name": "Elasticsearch模板",
        "description": "适用于ES集群监控",
        "default_config": {
            "port": 9200,
            "username": "elastic",
            "password": "",
            "index_pattern": "logstash-*",
            "timeout": 30,
        }
    },
    {
        "protocol_type": "vmware",
        "name": "VMware vSphere模板",
        "description": "适用于VMware虚拟化平台",
        "default_config": {
            "port": 443,
            "user": "administrator@vsphere.local",
            "password": "",
            "timeout": 30,
        }
    },
]


def run_migration(db):
    """执行数据库迁移"""
    # 创建表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS adapter_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_type VARCHAR(32) NOT NULL UNIQUE,
            name VARCHAR(128) NOT NULL,
            description VARCHAR(512),
            default_config JSON NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS device_protocol_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            protocol_type VARCHAR(32) NOT NULL,
            adapter_template_id INTEGER,
            overrides JSON NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
            FOREIGN KEY (adapter_template_id) REFERENCES adapter_templates(id) ON DELETE SET NULL
        )
    """))
    
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_device_protocol_configs_device_id 
        ON device_protocol_configs(device_id)
    """))
    
    db.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_device_protocol_configs_unique 
        ON device_protocol_configs(device_id, protocol_type)
    """))
    
    db.commit()
    logger.info("适配器表创建完成")
    
    # 插入默认模板
    for adapter in DEFAULT_ADAPTERS:
        existing = db.query(AdapterTemplate).filter(
            AdapterTemplate.protocol_type == adapter["protocol_type"]
        ).first()
        if not existing:
            tmpl = AdapterTemplate(
                protocol_type=adapter["protocol_type"],
                name=adapter["name"],
                description=adapter["description"],
                default_config=adapter["default_config"],
                enabled=True,
            )
            db.add(tmpl)
            logger.info(f"插入默认适配器: {adapter['name']}")
    
    db.commit()
    logger.info(f"默认适配器初始化完成，共 {len(DEFAULT_ADAPTERS)} 个")


if __name__ == "__main__":
    from api.dependencies import get_db
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    for db in get_db():
        run_migration(db)
        break
