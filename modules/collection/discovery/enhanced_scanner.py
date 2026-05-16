# -*- coding: utf-8 -*-
"""
增强型设备发现扫描器

在原有 IP 扫描基础上，集成：
1. 设备指纹识别（厂商、型号、类型）
2. 自动认证探测（默认凭据尝试）
3. 自动选择采集协议
"""

import asyncio
import logging
import socket
import ipaddress
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .scanner import IPScanner, DiscoveredHost
from ..device_fingerprint import get_fingerprinter, DeviceCategory
from ..device_auth_prober import get_auth_prober

logger = logging.getLogger(__name__)


@dataclass
class EnhancedHost:
    """增强版发现主机"""
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    os_type: str = "unknown"
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    category: str = "other"
    ports: List[int] = field(default_factory=list)
    services: Dict[str, str] = field(default_factory=dict)
    status: str = "unknown"
    response_time: Optional[float] = None
    ttl: Optional[int] = None
    timestamp: str = ""
    
    # 指纹识别结果
    fingerprint: Dict[str, Any] = field(default_factory=dict)
    
    # 认证探测结果
    auth_result: Dict[str, Any] = field(default_factory=dict)
    
    # 建议的采集配置
    suggested_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "mac": self.mac,
            "os_type": self.os_type,
            "os_version": self.os_version,
            "vendor": self.vendor,
            "model": self.model,
            "category": self.category,
            "ports": self.ports,
            "services": self.services,
            "status": self.status,
            "response_time": self.response_time,
            "ttl": self.ttl,
            "timestamp": self.timestamp,
            "fingerprint": self.fingerprint,
            "auth_result": self.auth_result,
            "suggested_config": self.suggested_config,
        }


class EnhancedScanner:
    """
    增强型设备发现扫描器
    
    在标准IP扫描基础上，增加：
    - 设备指纹识别（厂商/型号）
    - 自动认证探测
    - 智能采集协议推荐
    """

    # 常见HTTP/HTTPS服务端口
    WEB_PORTS = [80, 443, 8080, 8443, 10443, 8000, 8888]

    def __init__(
        self,
        timeout: float = 2.0,
        ping_timeout: float = 1.0,
        ping_count: int = 2,
        max_workers: int = 50,
        enable_auth_probe: bool = True,
        auth_probe_timeout: float = 5.0,
    ):
        self.timeout = timeout
        self.ping_timeout = ping_timeout
        self.ping_count = ping_count
        self.max_workers = max_workers
        self.enable_auth_probe = enable_auth_probe
        self.auth_probe_timeout = auth_probe_timeout

        self._scanner = IPScanner(
            timeout=timeout,
            ping_timeout=ping_timeout,
            ping_count=ping_count,
            max_workers=max_workers,
        )
        self._fingerprinter = get_fingerprinter()
        self._auth_prober = get_auth_prober()

    async def scan_and_identify(
        self,
        cidr: str,
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> List[EnhancedHost]:
        """
        扫描并识别整个IP段
        
        流程：
        1. 并行ping扫描 + 端口扫描 + banner抓取
        2. 对每个在线主机进行指纹识别
        3. 自动尝试默认凭据认证（可选）
        4. 生成采集配置建议
        """
        logger.info(f"开始增强扫描: {cidr}")

        # 阶段1：快速主机发现
        hosts = await self._scanner.scan_ip_range(cidr, progress_callback)

        if not hosts:
            logger.info(f"扫描完成，未发现在线主机: {cidr}")
            return []

        logger.info(f"发现 {len(hosts)} 台在线主机，开始指纹识别...")

        # 阶段2：指纹识别 + 认证探测
        enhanced_hosts = await self._identify_hosts(hosts)

        logger.info(f"指纹识别完成，{len(enhanced_hosts)} 台设备已分析")
        return enhanced_hosts

    async def scan_single_and_identify(
        self,
        ip: str,
        ports: List[int] = None,
        banners: Dict[str, str] = None,
        mac: str = None,
        ttl: int = None,
        hostname: str = None,
    ) -> EnhancedHost:
        """
        对单个IP进行完整扫描和识别
        """
        host = EnhancedHost(ip=ip)
        host.status = "up"
        host.timestamp = datetime.now().isoformat()

        if ports:
            host.ports = ports
        if banners:
            host.services = banners
        if mac:
            host.mac = mac
        if ttl:
            host.ttl = ttl
        if hostname:
            host.hostname = hostname

        # 指纹识别
        host.fingerprint = self._fingerprinter.identify(
            banners=banners or {},
            ports=ports or [],
            mac=mac,
            ttl=ttl,
            hostname=hostname,
        )

        self._apply_fingerprint(host)

        # 认证探测
        if self.enable_auth_probe and host.fingerprint.get("vendor"):
            host.auth_result = await self._auth_prober.probe_device(
                ip=ip,
                ports=ports or [],
                banners=banners or {},
                suggested_creds=host.fingerprint.get("possible_creds", []),
                suggested_protocols=host.fingerprint.get("suggested_protocols", []),
            )

        # 生成采集配置建议
        host.suggested_config = self._generate_suggested_config(host)

        return host

    async def _identify_hosts(
        self,
        hosts: List[DiscoveredHost],
    ) -> List[EnhancedHost]:
        """对发现的主机列表进行指纹识别"""
        semaphore = asyncio.Semaphore(self.max_workers)

        async def identify_host(h: DiscoveredHost) -> Optional[EnhancedHost]:
            async with semaphore:
                try:
                    # 构建banner字典 {port: banner}
                    banners = {}
                    for port, banner in h.services.items():
                        if banner:
                            banners[str(port)] = banner

                    return await self.scan_single_and_identify(
                        ip=h.ip,
                        ports=h.ports,
                        banners=banners,
                        mac=h.mac,
                        ttl=h.ttl,
                        hostname=h.hostname,
                    )
                except Exception as e:
                    logger.debug(f"识别主机 {h.ip} 失败: {e}")
                    return None

        tasks = [identify_host(h) for h in hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enhanced = []
        for r in results:
            if isinstance(r, EnhancedHost):
                enhanced.append(r)

        logger.info(f"指纹识别完成，{len(enhanced)} 台设备已分析")
        return enhanced

    def _apply_fingerprint(self, host: EnhancedHost) -> None:
        """将指纹结果应用到主机对象"""
        fp = host.fingerprint

        host.vendor = fp.get("vendor")
        host.model = fp.get("model")
        host.os_type = fp.get("category", "other")
        host.category = fp.get("category", "other")
        host.os_version = fp.get("model") or fp.get("os_version")

        # 从matched_by推断OS类型
        matched_by = fp.get("matched_by", [])
        for match in matched_by:
            if "banner" in match:
                host.os_type = self._banner_to_os_type(matched_by)

    def _banner_to_os_type(self, matched_by: List[str]) -> str:
        """根据匹配依据推断OS类型"""
        combined = " ".join(matched_by).lower()

        if any(p in combined for p in ["windows", "microsoft"]):
            return "windows"
        elif any(p in combined for p in ["linux", "ubuntu", "centos", "debian", "red hat"]):
            return "linux"
        elif any(p in combined for p in ["cisco", "huawei", "juniper", "h3c", "arista"]):
            return "network"
        elif any(p in combined for p in ["vmware", "esxi"]):
            return "vmware"
        elif any(p in combined for p in ["hikvision", "dahua", "camera"]):
            return "camera"

        return "unknown"

    def _generate_suggested_config(self, host: EnhancedHost) -> Dict[str, Any]:
        """生成建议的采集配置"""
        config = {
            "name": f"auto-{host.ip.replace('.', '-')}",
            "ip": host.ip,
            "type": self._category_to_device_type(host.category),
            "vendor": host.vendor or "unknown",
            "os": host.os_type,
            "os_version": host.os_version,
            "model": host.model,
            "protocols": {},
            "collect": {
                "enabled": True,
                "interval": 60,
            },
            "tags": {
                "source": "enhanced_scan",
                "scanned_at": datetime.now().isoformat(),
            },
        }

        # 根据指纹结果填充协议
        suggested_protocols = host.fingerprint.get("suggested_protocols", [])
        auth_result = host.auth_result

        if auth_result.get("accessible"):
            method = auth_result.get("method", "")
            creds = auth_result.get("credentials", {})

            if method in ("ssh",):
                config["protocols"]["ssh"] = {
                    "enabled": True,
                    "port": 22,
                    "username": creds.get("username", ""),
                    "password": creds.get("password", ""),
                }
                config["protocols"]["snmp"] = {"enabled": False}

            elif method in ("http", "https"):
                port = 443 if method == "https" else 80
                config["protocols"]["http"] = {
                    "enabled": True,
                    "port": port,
                    "use_ssl": method == "https",
                    "username": creds.get("username", ""),
                    "password": creds.get("password", ""),
                }

            elif method == "snmp":
                config["protocols"]["snmp"] = {
                    "enabled": True,
                    "port": 161,
                    "community": "public",
                }

        else:
            # 没有认证成功，按建议协议配置空凭据
            if "snmp" in suggested_protocols:
                config["protocols"]["snmp"] = {"enabled": True, "port": 161, "community": "public"}

            if "ssh" in suggested_protocols:
                config["protocols"]["ssh"] = {"enabled": True, "port": 22}

        return config

    def _category_to_device_type(self, category: str) -> str:
        """将Category转换为设备类型"""
        mapping = {
            "server": "server",
            "switch": "network",
            "router": "network",
            "firewall": "security",
            "wireless": "network",
            "storage": "storage",
            "camera": "security",
            "loadbalancer": "network",
            "ids_ips": "security",
            "ups": "power",
            "other": "server",
        }
        return mapping.get(category, "server")


# 全局单例
_enhanced_scanner: Optional[EnhancedScanner] = None


def get_enhanced_scanner() -> EnhancedScanner:
    """获取增强扫描器单例"""
    global _enhanced_scanner
    if _enhanced_scanner is None:
        _enhanced_scanner = EnhancedScanner()
    return _enhanced_scanner
