# -*- coding: utf-8 -*-
"""
SNMP Scanner for Device Auto-Discovery

Provides SNMP-based device discovery and information retrieval.
Supports SNMP v1/v2c/v3 and multiple network discovery techniques.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import ipaddress
import concurrent.futures

logger = logging.getLogger(__name__)


class SNMPDeviceType(str, Enum):
    """SNMP设备类型"""
    ROUTER = "router"
    SWITCH = "switch"
    SERVER = "server"
    WORKSTATION = "workstation"
    PRINTER = "printer"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    STORAGE = "storage"
    UNKNOWN = "unknown"


@dataclass
class SNMPDiscoveredDevice:
    """SNMP发现的设备"""
    ip: str
    hostname: Optional[str] = None
    sys_descr: Optional[str] = None
    sys_object_id: Optional[str] = None
    sys_uptime: Optional[int] = None
    vendor: Optional[str] = None
    device_type: SNMPDeviceType = SNMPDeviceType.UNKNOWN
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    location: Optional[str] = None
    contact: Optional[str] = None
    mac_address: Optional[str] = None
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "unknown"
    response_time: Optional[float] = None
    community: str = "public"
    snmp_version: str = "v2c"
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "sys_descr": self.sys_descr,
            "sys_object_id": self.sys_object_id,
            "sys_uptime": self.sys_uptime,
            "vendor": self.vendor,
            "device_type": self.device_type.value if isinstance(self.device_type, SNMPDeviceType) else self.device_type,
            "os_type": self.os_type,
            "os_version": self.os_version,
            "location": self.location,
            "contact": self.contact,
            "mac_address": self.mac_address,
            "interfaces": self.interfaces,
            "status": self.status,
            "response_time": self.response_time,
            "community": self.community,
            "snmp_version": self.snmp_version,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class SNMPScanner:
    """
    SNMP Network Scanner
    
    Features:
    - SNMP device discovery via walk
    - System information retrieval
    - Interface enumeration
    - Vendor auto-detection
    - Multi-version support (v1/v2c/v3)
    """
    
    # SNMP OIDs for discovery
    OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"  # sysDescr
    OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"  # sysObjectID
    OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"  # sysUpTime
    OID_SYS_CONTACT = "1.3.6.1.2.1.1.4.0"  # sysContact
    OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"  # sysName
    OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"  # sysLocation
    
    # Interface OIDs
    OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"  # ifDescr
    OID_IF_TYPE = "1.3.6.1.2.1.2.2.1.3"  # ifType
    OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"  # ifSpeed
    OID_IF_MAC = "1.3.6.1.2.1.2.2.1.6"  # ifPhysAddress
    OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"  # ifAdminStatus
    OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"  # ifOperStatus
    
    # Vendor OIDs (sysObjectID prefixes)
    VENDOR_OIDS = {
        'cisco': '1.3.6.1.4.1.9',
        'juniper': '1.3.6.1.4.1.2636',
        'huawei': '1.3.6.1.4.1.2011',
        'h3c': '1.3.6.1.4.1.25506',
        'arista': '1.3.6.1.4.1.30065',
        'dell': '1.3.6.1.4.1.674',
        'hp': '1.3.6.1.4.1.11',
        'lenovo': '1.3.6.1.4.1.2',
        'inspur': '1.3.6.1.4.1.111',
        'neokylin': '1.3.6.1.4.1.489',
        'topsec': '1.3.6.1.4.1.629',
        'nsfocus': '1.3.6.1.4.1.8013',
        'venustech': '1.3.6.1.4.1.25582',
        'sangfor': '1.3.6.1.4.1.20992',
        'fortinet': '1.3.6.1.4.1.12356',
        'checkpoint': '1.3.6.1.4.1.262',
        'ubiquiti': '1.3.6.1.4.1.41112',
        'mikrotik': '1.3.6.1.4.1.14988',
        'aruba': '1.3.6.1.4.1.14823',
        'raspberry': '1.3.6.1.4.1.8072',
        'vmware': '1.3.6.1.4.1.6876',
        'microsoft': '1.3.6.1.4.1.311',
        'linux': '1.3.6.1.4.1.8072',
        'windows': '1.3.6.1.4.1.311',
    }
    
    # Device type detection based on sysDescr or sysObjectID
    DEVICE_TYPE_PATTERNS = {
        SNMPDeviceType.ROUTER: ['router', 'ios-xe', 'nx-os', 'junos', 'vrp', 'comware'],
        SNMPDeviceType.SWITCH: ['switch', 'catalyst', 'procurve', 'powerconnect'],
        SNMPDeviceType.FIREWALL: ['firewall', 'fortigate', 'ASA', 'pix', 'checkpoint', 'sangfor'],
        SNMPDeviceType.LOAD_BALANCER: ['load balancer', 'f5', 'big-ip', 'ace'],
        SNMPDeviceType.SERVER: ['server', 'windows server', 'linux', 'vmware esxi'],
        SNMPDeviceType.PRINTER: ['printer', 'laserjet', 'officejet', 'deskjet'],
        SNMPDeviceType.STORAGE: ['storage', 'san', 'nas', 'dell emc', 'netapp'],
    }
    
    def __init__(
        self,
        timeout: float = 5.0,
        retries: int = 3,
        max_workers: int = 20,
        communities: List[str] = None,
    ):
        """
        Initialize SNMP Scanner
        
        Args:
            timeout: SNMP request timeout
            retries: Number of retries
            max_workers: Maximum parallel workers
            communities: List of SNMP communities to try (for v1/v2c)
        """
        self.timeout = timeout
        self.retries = retries
        self.max_workers = max_workers
        self.communities = communities or ["public", "private", "community"]
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._snmp_client = None
    
    def _get_snmp_client(self):
        """Get or create SNMP client"""
        if self._snmp_client is None:
            # Import here to handle optional dependency
            try:
                from modules.collection.snmp_collector.snmp_client import SNMPClient, SNMPConfig, SNMPVersion
                self._snmp_client = {
                    'class': SNMPClient,
                    'config': SNMPConfig,
                    'version': SNMPVersion,
                }
            except ImportError:
                logger.warning("pysnmp not available, SNMP scanning will use simulated responses")
                self._snmp_client = {'class': None, 'config': None, 'version': None}
        return self._snmp_client
    
    async def scan_network(
        self,
        target: str,
        community: str = "public",
        snmp_version: str = "v2c",
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> List[SNMPDiscoveredDevice]:
        """
        Scan a single target or IP range for SNMP devices
        
        Args:
            target: IP address, CIDR range, or hostname
            community: SNMP community string
            snmp_version: SNMP version (v1, v2c, v3)
            progress_callback: Optional callback(complete, total, current_ip)
            
        Returns:
            List of discovered SNMP devices
        """
        # Determine targets
        targets = self._parse_target(target)
        total = len(targets)
        
        logger.info(f"SNMP scan: {len(targets)} targets, community={community}, version={snmp_version}")
        
        discovered = []
        completed = 0
        
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def scan_target(ip):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._scan_single_target(ip, community, snmp_version)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, ip)
                    return result
                except Exception as e:
                    logger.debug(f"SNMP scan error for {ip}: {e}")
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, ip)
                    return None
        
        tasks = [scan_target(ip) for ip in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, SNMPDiscoveredDevice):
                discovered.append(result)
        
        logger.info(f"SNMP scan complete: {len(discovered)} devices responding out of {total} targets")
        return discovered
    
    async def discover_snmp_devices(
        self,
        cidr: str,
        communities: List[str] = None,
        snmp_version: str = "v2c",
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> List[SNMPDiscoveredDevice]:
        """
        Discover SNMP devices in a network range
        
        Args:
            cidr: CIDR notation (e.g., "192.168.1.0/24")
            communities: List of communities to try
            snmp_version: SNMP version
            progress_callback: Optional callback
            
        Returns:
            List of discovered SNMP devices
        """
        communities = communities or self.communities
        targets = self._parse_target(cidr)
        total = len(targets) * len(communities)
        
        logger.info(f"SNMP discovery: {len(targets)} targets x {len(communities)} communities")
        
        discovered = []
        completed = 0
        seen_ips = set()  # Avoid duplicates
        
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def scan_target_community(ip, community):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._scan_single_target(ip, community, snmp_version)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, f"{ip}/{community}")
                    
                    if result and result.ip not in seen_ips:
                        seen_ips.add(result.ip)
                        return result
                    return None
                except Exception as e:
                    logger.debug(f"SNMP discovery error for {ip}/{community}: {e}")
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, f"{ip}/{community}")
                    return None
        
        # Create tasks for all target/community combinations
        tasks = []
        for ip in targets:
            for community in communities:
                tasks.append(scan_target_community(ip, community))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, SNMPDiscoveredDevice):
                discovered.append(result)
        
        logger.info(f"SNMP discovery complete: {len(discovered)} unique devices")
        return discovered
    
    async def _scan_single_target(
        self,
        ip: str,
        community: str,
        snmp_version: str,
    ) -> Optional[SNMPDiscoveredDevice]:
        """Scan a single target via SNMP"""
        import time
        start_time = time.time()
        
        snmp_info = self._get_snmp_client()
        
        if snmp_info['class'] is None:
            # Simulated response when pysnmp is not available
            return await self._simulated_snmp_scan(ip, community, snmp_version)
        
        try:
            config = snmp_info['config'](
                host=ip,
                community=community,
                version=snmp_info['version'][snmp_version] if isinstance(snmp_version, str) else snmp_version,
                timeout=self.timeout,
                retries=self.retries,
            )
            
            client = snmp_info['class'](config)
            client.connect()
            
            # Get system info
            sys_descr = client.get(self.OID_SYS_DESCR)
            sys_object_id = client.get(self.OID_SYS_OBJECT_ID)
            sys_uptime = client.get(self.OID_SYS_UPTIME)
            sys_contact = client.get(self.OID_SYS_CONTACT)
            sys_name = client.get(self.OID_SYS_NAME)
            sys_location = client.get(self.OID_SYS_LOCATION)
            
            client.close()
            
            # If no response, device doesn't support SNMP
            if not sys_descr and not sys_object_id:
                return None
            
            response_time = (time.time() - start_time) * 1000
            
            device = SNMPDiscoveredDevice(
                ip=ip,
                hostname=sys_name,
                sys_descr=sys_descr,
                sys_object_id=sys_object_id,
                sys_uptime=sys_uptime,
                contact=sys_contact,
                location=sys_location,
                vendor=self._detect_vendor(sys_object_id, sys_descr),
                device_type=self._detect_device_type(sys_descr, sys_object_id),
                os_type=self._detect_os_type(sys_descr),
                os_version=self._detect_os_version(sys_descr),
                status="responding",
                response_time=response_time,
                community=community,
                snmp_version=snmp_version,
            )
            
            # Get interfaces
            device.interfaces = await self._get_interfaces(client, config)
            
            return device
            
        except Exception as e:
            logger.debug(f"SNMP target {ip} error: {e}")
            return None
    
    async def _simulated_snmp_scan(
        self,
        ip: str,
        community: str,
        snmp_version: str,
    ) -> Optional[SNMPDiscoveredDevice]:
        """Simulated SNMP scan for testing when pysnmp is not available"""
        import random
        import time
        
        # Simulate response for specific IPs or random chance
        if ip.endswith('.1') or ip.endswith('.254') or random.random() < 0.1:
            await asyncio.sleep(0.05)  # Simulate network delay
            
            return SNMPDiscoveredDevice(
                ip=ip,
                hostname=f"snmp-device-{ip.split('.')[-1]}",
                sys_descr=f"Simulated device at {ip}",
                sys_object_id="1.3.6.1.4.1.1",
                sys_uptime=random.randint(100000, 10000000),
                vendor="Simulated",
                device_type=SNMPDeviceType.SERVER,
                os_type="Linux",
                os_version="2.6.x",
                status="responding",
                response_time=random.uniform(1.0, 50.0),
                community=community,
                snmp_version=snmp_version,
            )
        return None
    
    async def _get_interfaces(self, client, config) -> List[Dict[str, Any]]:
        """Get network interfaces via SNMP"""
        interfaces = []
        
        try:
            # Walk interface table
            if_descrs = client.walk(self.OID_IF_DESCR)
            
            for if_entry in if_descrs:
                oid = if_entry.get('oid', '')
                descr = if_entry.get('value', '')
                
                # Extract interface index from OID
                if_index = oid.split('.')[-1] if '.' in oid else None
                
                interfaces.append({
                    'index': if_index,
                    'description': descr,
                    'type': 'unknown',  # Would need additional queries
                    'speed': 0,
                    'mac': None,
                    'admin_status': 'up',
                    'oper_status': 'up',
                })
        except Exception as e:
            logger.debug(f"Interface enumeration error: {e}")
        
        return interfaces[:10]  # Limit to 10 interfaces
    
    def _parse_target(self, target: str) -> List[str]:
        """Parse target string into list of IP addresses"""
        targets = []
        
        try:
            # Check if it's a CIDR range
            if '/' in target:
                network = ipaddress.ip_network(target, strict=False)
                for ip in network.hosts():
                    targets.append(str(ip))
            else:
                # Single IP or hostname
                targets.append(target)
        except ValueError as e:
            logger.error(f"Invalid target format: {target} - {e}")
            raise ValueError(f"Invalid target format: {target}") from e
        
        return targets
    
    def _detect_vendor(self, sys_object_id: Optional[str], sys_descr: Optional[str]) -> Optional[str]:
        """Detect vendor from sysObjectID and sysDescr"""
        if sys_object_id:
            sys_object_id_lower = sys_object_id.lower()
            for vendor, prefix in self.VENDOR_OIDS.items():
                if prefix in sys_object_id_lower or prefix in sys_object_id:
                    return vendor.capitalize()
        
        if sys_descr:
            sys_descr_lower = sys_descr.lower()
            vendor_keywords = {
                'Cisco': ['cisco', 'ios-xe', 'nx-os', 'ios'],
                'Juniper': ['juniper', 'junos'],
                'Huawei': ['huawei', 'vrp'],
                'H3C': ['h3c', 'comware'],
                'Arista': ['arista', 'eos'],
                'Dell': ['dell', 'powerconnect'],
                'HP': ['hp ', 'hewlett', 'procurve'],
                'VMware': ['vmware', 'esxi', 'esx'],
                'Microsoft': ['windows', 'microsoft'],
                'Linux': ['linux'],
            }
            
            for vendor, keywords in vendor_keywords.items():
                for keyword in keywords:
                    if keyword in sys_descr_lower:
                        return vendor
        
        return None
    
    def _detect_device_type(self, sys_descr: Optional[str], sys_object_id: Optional[str]) -> SNMPDeviceType:
        """Detect device type from sysDescr and sysObjectID"""
        text = ""
        if sys_descr:
            text += sys_descr.lower()
        if sys_object_id:
            text += sys_object_id.lower()
        
        for device_type, patterns in self.DEVICE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    return device_type
        
        return SNMPDeviceType.UNKNOWN
    
    def _detect_os_type(self, sys_descr: Optional[str]) -> Optional[str]:
        """Detect OS type from sysDescr"""
        if not sys_descr:
            return None
        
        sys_descr_lower = sys_descr.lower()
        
        os_patterns = {
            'Cisco IOS': ['cisco ios', 'ios-xe', 'nx-os'],
            'Juniper JunOS': ['junos', 'juniper'],
            'Huawei VRP': ['vrp', 'huawei'],
            'H3C Comware': ['comware', 'h3c'],
            'Arista EOS': ['eos', 'arista'],
            'Windows': ['windows'],
            'Linux': ['linux'],
            'VMware ESXi': ['esxi', 'vmware'],
            'Mac OS': ['macos', 'darwin'],
        }
        
        for os_name, patterns in os_patterns.items():
            for pattern in patterns:
                if pattern in sys_descr_lower:
                    return os_name
        
        return None
    
    def _detect_os_version(self, sys_descr: Optional[str]) -> Optional[str]:
        """Detect OS version from sysDescr"""
        if not sys_descr:
            return None
        
        import re
        
        # Try to find version patterns
        patterns = [
            r'(\d+\.\d+(?:\.\d+)?[A-Za-z]*)',  # e.g., 2.6.32, 15.2, 4.19.0, 15.2.4M
            r'Version\s+(\S+)',
            r'Vers\.\s*(\S+)',
            r'Release\s+(\S+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sys_descr, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def snmp_walk_network(
        self,
        target: str,
        community: str = "public",
        oid: str = "1.3.6.1",
    ) -> List[Dict[str, Any]]:
        """
        Perform SNMP walk on a target
        
        Args:
            target: IP address
            community: SNMP community
            oid: OID to start walk from
            
        Returns:
            List of {oid, value} dicts
        """
        snmp_info = self._get_snmp_client()
        
        if snmp_info['class'] is None:
            logger.warning("pysnmp not available for SNMP walk")
            return []
        
        try:
            config = snmp_info['config'](
                host=target,
                community=community,
                timeout=self.timeout,
                retries=self.retries,
            )
            
            client = snmp_info['class'](config)
            client.connect()
            
            results = client.walk(oid)
            
            client.close()
            
            return [{'oid': r.get('oid'), 'value': r.get('value')} for r in results]
            
        except Exception as e:
            logger.error(f"SNMP walk failed for {target}: {e}")
            return []
    
    def close(self):
        """Close scanner and cleanup resources"""
        self._executor.shutdown(wait=False)


# Global scanner instance
_snmp_scanner: Optional[SNMPScanner] = None


def get_snmp_scanner() -> SNMPScanner:
    """Get or create global SNMP scanner instance"""
    global _snmp_scanner
    if _snmp_scanner is None:
        _snmp_scanner = SNMPScanner()
    return _snmp_scanner
