"""
麒麟操作系统专用采集器
支持银河麒麟、麒麟软件等国产操作系统
"""

import logging
import re
from typing import Any, Dict, List, Optional

from ..ssh_client import SSHClient, SSHConfig

logger = logging.getLogger(__name__)


class KylinCollector:
    """
    麒麟操作系统采集器
    
    专门针对国产麒麟操作系统的特殊采集功能
    银河麒麟 (Kylin Linux) / 银河麒麟V10 / 麒麟软件等
    """
    
    def __init__(self, client: SSHClient):
        """
        初始化采集器
        
        Args:
            client: SSH客户端
        """
        self._client = client
        self._kylin_version: Optional[str] = None
    
    def detect_version(self) -> str:
        """
        检测麒麟版本
        
        Returns:
            麒麟版本信息
        """
        _, os_release, _ = self._client.execute('cat /etc/kylin-release 2>/dev/null || cat /etc/os-release')
        
        # 银河麒麟V10
        if 'V10' in os_release or 'v10' in os_release.lower():
            self._kylin_version = 'kylin_v10'
        # 银河麒麟V7
        elif 'V7' in os_release or 'v7' in os_release.lower():
            self._kylin_version = 'kylin_v7'
        # 麒麟软件
        elif 'Kylin' in os_release:
            self._kylin_version = 'kylin'
        # 麒麟信创版
        elif 'NeoKylin' in os_release:
            self._kylin_version = 'neokylin'
        # UOS
        elif 'UnionTech' in os_release or '统信' in os_release:
            self._kylin_version = 'uos'
        # 银河麒麟企业版
        elif 'Kylin-Server' in os_release:
            self._kylin_version = 'kylin_server'
        else:
            self._kylin_version = 'unknown'
        
        logger.info(f"检测到麒麟版本: {self._kylin_version}")
        return self._kylin_version
    
    def collect_sec_info(self) -> Dict[str, Any]:
        """
        采集安全信息系统 (银河麒麟特有)
        
        Returns:
            安全信息字典
        """
        info = {}
        
        # 安全基线检查状态
        _, sec_check, _ = self._client.execute('which sec_check 2>/dev/null || echo notfound')
        if 'notfound' not in sec_check:
            _, sec_output, _ = self._client.execute('sec_check -v 2>/dev/null || echo ""')
            info['sec_check_available'] = True
            info['sec_check_version'] = sec_output.strip()
        
        # 三权分立检查
        _, audit_status, _ = self._client.execute('systemctl status kylin-audit 2>/dev/null || echo inactive')
        info['audit_enabled'] = 'active' in audit_status.lower()
        
        # 安全审计日志
        _, audit_log, _ = self._client.execute('ls -la /var/log/kylin-audit/ 2>/dev/null | head -5 || echo ""')
        info['audit_log_exists'] = len(audit_log.strip()) > 0
        
        # 可信检查
        _, trusted_status, _ = self._client.execute('cat /etc/trusted-kylin.conf 2>/dev/null || echo ""')
        info['trusted_config_exists'] = len(trusted_status.strip()) > 0
        
        return info
    
    def collect_compliance_info(self) -> Dict[str, Any]:
        """
        采集合规信息
        
        Returns:
            合规信息字典
        """
        compliance = {}
        
        # 密码策略
        _, passwd_policy, _ = self._client.execute('grep "^PASS" /etc/login.defs 2>/dev/null || echo ""')
        compliance['password_policy'] = passwd_policy.strip()
        
        # 审计规则
        _, audit_rules, _ = self._client.execute('auditctl -l 2>/dev/null | head -10 || echo ""')
        compliance['audit_rules'] = audit_rules.strip().split('\n')
        
        # 防火墙状态
        _, firewall_status, _ = self._client.execute('systemctl status firewalld 2>/dev/null || systemctl status iptables 2>/dev/null || echo "unknown"')
        compliance['firewall_status'] = 'active' in firewall_status.lower()
        
        # SELinux/AppArmor状态
        _, selinux_status, _ = self._client.execute('getenforce 2>/dev/null || echo "disabled"')
        compliance['selinux_status'] = selinux_status.strip()
        
        return compliance
    
    def collect_network_config(self) -> Dict[str, Any]:
        """
        采集网络配置信息 (麒麟特有)
        
        Returns:
            网络配置字典
        """
        config = {}
        
        # 网卡配置
        _, net_interfaces, _ = self._client.execute(
            "ls -la /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | grep -v '.bak' | awk '{print $NF}'"
        )
        
        interfaces = []
        for iffile in net_interfaces.strip().split('\n'):
            if iffile and 'ifcfg-lo' not in iffile:
                _, ifconfig, _ = self._client.execute(f'cat {iffile} 2>/dev/null || echo ""')
                if ifconfig:
                    interfaces.append(ifconfig)
        
        config['interface_configs'] = interfaces
        
        # DNS配置
        _, dns_config, _ = self._client.execute('cat /etc/resolv.conf 2>/dev/null || echo ""')
        config['dns_config'] = dns_config.strip()
        
        # 主机名配置
        _, hostname_config, _ = self._client.execute('cat /etc/hostname 2>/dev/null || echo ""')
        config['hostname'] = hostname_config.strip()
        
        return config
    
    def collect_systemd_services(self) -> List[Dict[str, Any]]:
        """
        采集系统服务状态 (麒麟特有)
        
        Returns:
            服务列表
        """
        services = []
        
        # 麒麟特有服务
        kylin_services = [
            'kylin-audit',      # 安全审计服务
            'kylin-secure',      # 安全服务
            'kylin-smart',       # 智能监控
            'kylin-power',      # 电源管理
            'kylin-display',   # 显示管理
            'kwin'              # 窗口管理器
        ]
        
        for svc in kylin_services:
            _, status, _ = self._client.execute(f'systemctl status {svc} 2>/dev/null | head -1')
            if status:
                services.append({
                    'name': svc,
                    'status': status.strip() if status else 'unknown'
                })
        
        # 通用服务
        _, running_services, _ = self._client.execute(
            'systemctl list-units --type=service --state=running --no-pager --no-legend | head -30'
        )
        
        for line in running_services.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split()
            if parts:
                services.append({
                    'name': parts[0].replace('.service', ''),
                    'status': 'running'
                })
        
        return services
    
    def collect_package_updates(self) -> Dict[str, Any]:
        """
        采集可用包更新 (麒麟特有)
        
        Returns:
            包更新信息
        """
        updates = {}
        
        # 检查更新源
        _, update_source, _ = self._client.execute('cat /etc/apt/sources.list 2>/dev/null | head -5 || echo ""')
        updates['apt_sources'] = update_source
        
        _, update_source_yum, _ = self._client.execute('cat /etc/yum.repos.d/*.repo 2>/dev/null | head -10 || echo ""')
        updates['yum_sources'] = update_source_yum
        
        # 检查可用更新
        if update_source:  # apt系统
            _, check_update, _ = self._client.execute('apt list --upgradable 2>/dev/null | tail -n +2 || echo ""')
            updates['apt_updates'] = check_update.strip().split('\n')
        elif update_source_yum:  # yum系统
            _, check_update, _ = self._client.execute('yum check-update 2>/dev/null || echo ""')
            updates['yum_updates'] = check_update.strip()
        
        return updates
    
    def collect_selinux_status(self) -> Dict[str, Any]:
        """
        采集SELinux状态
        
        Returns:
            SELinux状态
        """
        status = {}
        
        _, selinux_mode, _ = self._client.execute('getenforce 2>/dev/null || echo "Not supported"')
        status['mode'] = selinux_mode.strip()
        
        _, selinux_policy, _ = self._client.execute('sestatus 2>/dev/null | head -10 || echo ""')
        status['details'] = selinux_policy.strip().split('\n')
        
        _, selinux_config, _ = self._client.execute('cat /etc/selinux/config 2>/dev/null || echo ""')
        status['config'] = selinux_config.strip()
        
        return status
    
    def collect_kylin_specific(self) -> Dict[str, Any]:
        """
        采集麒麟特有信息
        
        Returns:
            麒麟特有信息
        """
        specific = {}
        
        # 麒麟桌面环境
        _, kde_version, _ = self._client.execute('kwin --version 2>/dev/null || echo ""')
        specific['kde_version'] = kde_version.strip()
        
        # 麒麟字体
        _, kylin_fonts, _ = self._client.execute('fc-list :lang=zh 2>/dev/null | head -10 || echo ""')
        specific['chinese_fonts'] = kylin_fonts.strip().split('\n')
        
        # 麒麟输入法
        _, ibus_status, _ = self._client.execute('ibus version 2>/dev/null || echo ""')
        specific['ibus_version'] = ibus_status.strip()
        
        # 麒麟签名工具
        _, sign_tool, _ = self._client.execute('which kylinsign 2>/dev/null || echo ""')
        specific['signature_tool'] = 'available' if 'kylinsign' in sign_tool else 'not_found'
        
        return specific
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有系统信息
        
        Returns:
            完整的系统信息
        """
        # 检测麒麟版本
        if not self._kylin_version:
            self.detect_version()
        
        # 先调用Linux采集器获取基础信息
        from .linux_collector import LinuxCollector
        linux_collector = LinuxCollector(self._client)
        base_info = linux_collector.collect_all()
        
        # 合并麒麟特有信息
        data = base_info.copy()
        data.update({
            'kylin_version': self._kylin_version,
            'kylin_specific': self.collect_kylin_specific(),
            'security_info': self.collect_sec_info(),
            'compliance': self.collect_compliance_info(),
            'network_config': self.collect_network_config(),
            'systemd_services': self.collect_systemd_services(),
            'package_updates': self.collect_package_updates(),
            'selinux_status': self.collect_selinux_status()
        })
        
        return data
