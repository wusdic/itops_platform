# -*- coding: utf-8 -*-
"""
IP Range Scanner for Device Auto-Discovery

Provides parallel ping sweep, TCP banner grabbing, and OS fingerprinting
for discovering devices in IP ranges.
"""

import asyncio
import logging
import socket
import struct
import concurrent.futures
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import ipaddress
import re

logger = logging.getLogger(__name__)


class OSType(str, Enum):
    """操作系统类型"""
    WINDOWS = "windows"
    LINUX = "linux"
    UNIX = "unix"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredHost:
    """发现的Host"""
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    os_type: OSType = OSType.UNKNOWN
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    services: Dict[str, str] = field(default_factory=dict)
    status: str = "unknown"
    response_time: Optional[float] = None
    ttl: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "mac": self.mac,
            "os_type": self.os_type.value if isinstance(self.os_type, OSType) else self.os_type,
            "os_version": self.os_version,
            "vendor": self.vendor,
            "ports": self.ports,
            "services": self.services,
            "status": self.status,
            "response_time": self.response_time,
            "ttl": self.ttl,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class IPScanner:
    """
    IP Range Scanner
    
    Features:
    - Parallel ping sweep
    - TCP banner grabbing
    - OS fingerprinting based on TTL and banner
    - Common port scanning
    """
    
    # Common ports to scan
    COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
    
    # TCP ports for banner grabbing
    BANNER_PORTS = [21, 22, 23, 80, 443, 3306, 3389, 8080]
    
    # OS detection patterns
    WINDOWS_BANNER_PATTERNS = [b"windows", b"microsoft", b"iis", b"asp.net"]
    LINUX_BANNER_PATTERNS = [b"linux", b"ubuntu", b"centos", b"debian", b"red hat", b"fedora", b"ssh-", b"apache", b"nginx"]
    NETWORK_DEVICE_PATTERNS = [b"cisco", b"huawei", b"h3c", b"juniper", b"arista", b"dell", b"hp ", b"broadcom", b"router", b"switch"]
    
    def __init__(
        self,
        timeout: float = 2.0,
        ping_timeout: float = 1.0,
        ping_count: int = 2,
        max_workers: int = 50,
        ports: List[int] = None,
    ):
        """
        Initialize IP Scanner
        
        Args:
            timeout: TCP connection timeout
            ping_timeout: Ping timeout per host
            ping_count: Number of ping attempts
            max_workers: Maximum parallel workers
            ports: Custom port list (defaults to COMMON_PORTS)
        """
        self.timeout = timeout
        self.ping_timeout = ping_timeout
        self.ping_count = ping_count
        self.max_workers = max_workers
        self.ports = ports or self.COMMON_PORTS
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    async def scan_ip_range(
        self,
        cidr: str,
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> List[DiscoveredHost]:
        """
        Scan IP range (CIDR notation)
        
        Args:
            cidr: CIDR notation (e.g., "192.168.1.0/24")
            progress_callback: Optional callback(complete, total, current_ip)
            
        Returns:
            List of discovered hosts
        """
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            hosts = list(network.hosts())
            total = len(hosts)
            
            logger.info(f"Scanning {cidr}: {total} hosts to check")
            
            discovered = []
            completed = 0
            
            # Use semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def scan_host(host):
                async with semaphore:
                    nonlocal completed
                    try:
                        result = await self._scan_single_host(str(host))
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total, str(host))
                        return result
                    except Exception as e:
                        logger.debug(f"Error scanning {host}: {e}")
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total, str(host))
                        return None
            
            tasks = [scan_host(host) for host in hosts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, DiscoveredHost) and result.status == "up":
                    discovered.append(result)
            
            logger.info(f"Discovery complete: {len(discovered)} hosts up out of {total} scanned")
            return discovered
            
        except ValueError as e:
            logger.error(f"Invalid CIDR format: {cidr} - {e}")
            raise ValueError(f"Invalid CIDR format: {cidr}") from e
    
    async def scan_hosts(
        self,
        hosts: List[str],
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> List[DiscoveredHost]:
        """
        Scan specific hosts
        
        Args:
            hosts: List of IP addresses or hostnames
            progress_callback: Optional callback
            
        Returns:
            List of discovered hosts
        """
        total = len(hosts)
        discovered = []
        completed = 0
        
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def scan_host(ip):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._scan_single_host(ip)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, ip)
                    return result
                except Exception as e:
                    logger.debug(f"Error scanning {ip}: {e}")
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, ip)
                    return None
        
        tasks = [scan_host(ip) for ip in hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, DiscoveredHost) and result.status == "up":
                discovered.append(result)
        
        return discovered
    
    async def _scan_single_host(self, ip: str) -> Optional[DiscoveredHost]:
        """
        Scan a single host - ping first, then do port scan and banner grab
        """
        start_time = datetime.now()
        
        # Ping check first
        is_alive, ttl, response_time = await self._ping(ip)
        
        if not is_alive:
            # Try TCP check as fallback for hosts that block ICMP
            is_alive = await self._tcp_check(ip, [80, 443, 22])
            if not is_alive:
                return DiscoveredHost(ip=ip, status="down")
        
        host = DiscoveredHost(
            ip=ip,
            status="up",
            ttl=ttl,
            response_time=response_time,
        )
        
        # Try to resolve hostname
        try:
            hostname, _, _ = await asyncio.get_event_loop().run_in_executor(
                None, socket.gethostbyaddr, ip
            )
            host.hostname = hostname
        except (socket.herror, socket.gaierror, Exception):
            pass
        
        # Detect OS
        host.os_type, host.os_version = self._detect_os(ttl, b"")  # Will be refined after banner grab
        
        # Scan ports
        open_ports = await self._scan_ports(ip, self.ports)
        host.ports = open_ports
        
        # Grab banners
        banners = await self._grab_banners(ip, self.BANNER_PORTS)
        host.services = banners
        
        # Refine OS detection with banner info
        combined_banner = b" ".join(banners.values()) if banners else b""
        host.os_type, host.os_version = self._detect_os(ttl, combined_banner)
        
        # Detect vendor from banners
        host.vendor = self._detect_vendor(combined_banner)
        
        host.timestamp = datetime.now()
        return host
    
    async def _ping(self, ip: str) -> tuple:
        """
        Ping a host using asyncio
        
        Returns:
            (is_alive, ttl, response_time_ms)
        """
        try:
            # Try ICMP ping first (requires root on Linux)
            loop = asyncio.get_event_loop()
            
            # Create raw socket for ICMP
            # Note: This may fail without root privileges
            import os
            import struct
            import time
            
            if os.getuid() == 0:  # root
                return await self._icmp_ping(ip)
            else:
                # Fallback to TCP ping
                return await self._tcp_ping_fallback(ip)
                
        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {e}")
            return await self._tcp_ping_fallback(ip)
    
    async def _icmp_ping(self, ip: str) -> tuple:
        """ICMP ping (requires root)"""
        try:
            import os
            import struct
            import time
            import asyncio
            
            # Create raw ICMP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.setsockopt(socket.SOL_IP, socket.IP_TTL, 64)
            sock.settimeout(self.ping_timeout)
            
            # ICMP echo request
            packet_id = os.getpid() & 0xFFFF
            seq = 1
            
            header = struct.pack('!BBHHH', 8, 0, 0, packet_id, seq)
            data = b'ping'
            
            # Calculate checksum
            def checksum(data):
                s = 0
                for i in range(0, len(data), 2):
                    s += (data[i] << 8) + data[i + 1]
                while s >> 16:
                    s = (s & 0xFFFF) + (s >> 16)
                return ~s & 0xFFFF
            
            checksum_val = checksum(header + data)
            header = struct.pack('!BBHHH', 8, 0, checksum_val, packet_id, seq)
            packet = header + data
            
            start_time = time.time()
            sock.sendto(packet, (ip, 0))
            
            # Wait for reply
            recv_packet, addr = sock.recv(1024)
            end_time = time.time()
            
            sock.close()
            
            # Parse ICMP response
            icmp_header = recv_packet[20:28]
            _, _, _, seq = struct.unpack('!BBHHH', icmp_header)
            
            response_time = (end_time - start_time) * 1000  # ms
            ttl = 64  # Default TTL
            
            return True, ttl, response_time
            
        except Exception as e:
            logger.debug(f"ICMP ping failed for {ip}: {e}")
            return False, None, None
    
    async def _tcp_ping_fallback(self, ip: str) -> tuple:
        """TCP ping fallback - try to connect to common ports"""
        try:
            for port in [80, 443, 22, 445]:
                if await self._tcp_check(ip, [port]):
                    return True, 64, None  # Assume TTL of 64 for responsive hosts
            return False, None, None
        except Exception:
            return False, None, None
    
    async def _tcp_check(self, ip: str, ports: List[int]) -> bool:
        """Check if host is reachable via TCP"""
        loop = asyncio.get_event_loop()
        
        async def check_port(port):
            try:
                reader, writer = await asyncio.wait_for(
                    loop.create_connection(
                        lambda: asyncio.Protocol(),
                        ip,
                        port,
                    ),
                    timeout=self.timeout,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except Exception:
                return False
        
        results = await asyncio.gather(*[check_port(p) for p in ports], return_exceptions=True)
        return any(r is True for r in results)
    
    async def _scan_ports(self, ip: str, ports: List[int]) -> List[int]:
        """Scan ports on a host"""
        loop = asyncio.get_event_loop()
        
        async def check_port(port):
            try:
                reader, writer = await asyncio.wait_for(
                    loop.create_connection(
                        lambda: asyncio.Protocol(),
                        ip,
                        port,
                    ),
                    timeout=self.timeout,
                )
                writer.close()
                await writer.wait_closed()
                return port
            except Exception:
                return None
        
        results = await asyncio.gather(*[check_port(p) for p in ports], return_exceptions=True)
        return [r for r in results if r is not None]
    
    async def _grab_banners(self, ip: str, ports: List[int]) -> Dict[str, str]:
        """Grab service banners"""
        banners = {}
        loop = asyncio.get_event_loop()
        
        async def grab_banner(port):
            try:
                reader, writer = await asyncio.wait_for(
                    loop.create_connection(
                        lambda: asyncio.streams.FlowControlMixin,
                        ip,
                        port,
                    ),
                    timeout=self.timeout,
                )
                
                # Send HTTP request for web ports
                if port in [80, 443, 8080, 8443]:
                    writer.write(b"GET / HTTP/1.0\r\nHost: %s\r\n\r\n" % ip.encode())
                
                await writer.drain()
                
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=self.timeout)
                    if data:
                        banner = data.decode('utf-8', errors='ignore').strip()
                        if banner:
                            service_name = self._identify_service(port, banner)
                            banners[service_name] = banner[:200]
                except asyncio.TimeoutError:
                    pass
                
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        
        await asyncio.gather(*[grab_banner(p) for p in ports], return_exceptions=True)
        return banners
    
    def _identify_service(self, port: int, banner: str) -> str:
        """Identify service based on port and banner"""
        port_service_map = {
            21: "ftp",
            22: "ssh",
            23: "telnet",
            25: "smtp",
            53: "dns",
            80: "http",
            110: "pop3",
            143: "imap",
            443: "https",
            3306: "mysql",
            3389: "rdp",
            5900: "vnc",
            8080: "http-proxy",
            8443: "https-alt",
        }
        return port_service_map.get(port, f"port-{port}")
    
    def _detect_os(self, ttl: Optional[int], banner: bytes) -> tuple:
        """
        Detect OS type and version from TTL and banner
        
        Returns:
            (os_type, os_version)
        """
        banner_lower = banner.lower() if banner else b""
        
        # Check banner patterns first
        for pattern in self.WINDOWS_BANNER_PATTERNS:
            if pattern in banner_lower:
                return OSType.WINDOWS, self._extract_version(banner_lower, [b"windows", b"microsoft"])
        
        for pattern in self.LINUX_BANNER_PATTERNS:
            if pattern in banner_lower:
                return OSType.LINUX, self._extract_version(banner_lower, [b"linux", b"ubuntu", b"centos", b"debian"])
        
        for pattern in self.NETWORK_DEVICE_PATTERNS:
            if pattern in banner_lower:
                return OSType.NETWORK, self._extract_version(banner_lower, [b"cisco", b"huawei", b"juniper"])
        
        # TTL-based detection as fallback
        if ttl:
            if ttl <= 64:
                return OSType.LINUX, "linux/unix (TTL-based)"
            elif ttl <= 128:
                return OSType.WINDOWS, "windows (TTL-based)"
            elif ttl <= 255:
                return OSType.NETWORK, "network device (TTL-based)"
        
        return OSType.UNKNOWN, None
    
    def _extract_version(self, banner: bytes, keywords: List[bytes]) -> Optional[str]:
        """Extract version string from banner"""
        for keyword in keywords:
            if keyword in banner:
                # Try to find version pattern
                match = re.search(rb'(\d+\.\d+(?:\.\d+)?)', banner)
                if match:
                    return match.group(1).decode('utf-8', errors='ignore')
        return None
    
    def _detect_vendor(self, banner: bytes) -> Optional[str]:
        """Detect vendor from banner"""
        banner_lower = banner.lower() if banner else b""
        
        vendor_patterns = {
            "Cisco": [b"cisco", b"ios-xe", b"nx-os", b"ios"],
            "Huawei": [b"huawei", b"vrp"],
            "Juniper": [b"juniper", b"junos"],
            "H3C": [b"h3c", b"comware"],
            "Arista": [b"arista", b"eos"],
            "Dell": [b"dell"],
            "HP": [b"hp ", b"hewlett"],
            "VMware": [b"vmware", b"esxi"],
            "Microsoft": [b"windows", b"microsoft"],
            "Linux": [b"linux", b"ubuntu", b"centos", b"debian"],
        }
        
        for vendor, patterns in vendor_patterns.items():
            for pattern in patterns:
                if pattern in banner_lower:
                    return vendor
        
        return None
    
    def close(self):
        """Close the scanner and cleanup resources"""
        self._executor.shutdown(wait=False)


# Global scanner instance
_scanner: Optional[IPScanner] = None


def get_scanner() -> IPScanner:
    """Get or create global scanner instance"""
    global _scanner
    if _scanner is None:
        _scanner = IPScanner()
    return _scanner
