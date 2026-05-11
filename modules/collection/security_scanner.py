"""
Security Scanner Module
Nmap-based port scanning and CVE version detection
"""

import asyncio
import json
import logging
import re
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class ScanStatus(Enum):
    """Scan result status"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    HOST_UNREACHABLE = "host_unreachable"


class Severity(Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


@dataclass
class PortInfo:
    """Port information"""
    port: int
    protocol: str
    state: str
    service: str = ''
    version: str = ''
    product: str = ''
    banner: str = ''


@dataclass
class ScanResult:
    """Nmap scan result"""
    host: str
    status: ScanStatus
    ports: List[PortInfo] = field(default_factory=list)
    os_detection: str = ''
    scan_time: float = 0.0
    services: Dict[int, str] = field(default_factory=dict)
    error_message: str = ''


@dataclass
class CVEInfo:
    """CVE information"""
    cve_id: str
    severity: Severity
    description: str
    published_date: str = ''
    modified_date: str = ''
    cvss_score: float = 0.0
    references: List[str] = field(default_factory=list)


@dataclass
class VulnerabilityResult:
    """Vulnerability check result"""
    host: str
    port: int
    service: str
    vulnerability: str
    severity: Severity
    cve_id: Optional[str] = None
    description: str = ''
    solution: str = ''
    cvss_score: float = 0.0


class SecurityScanner:
    """
    Security Scanner using Nmap

    Features:
    - Port scanning (TCP/UDP)
    - Service version detection
    - OS fingerprinting
    - CVE vulnerability checking
    - Async operation support
    """

    # Common vulnerable service patterns
    SERVICE_PATTERNS = {
        'ssh': {
            'product': 'OpenSSH',
            'default_ports': [22],
            'version_regex': r'OpenSSH_(\d+\.\d+)',
        },
        'ftp': {
            'product': 'vsftpd',
            'default_ports': [21],
            'version_regex': r'vsftpd\s+(\d+\.\d+)',
        },
        'http': {
            'product': 'Apache',
            'default_ports': [80, 8080, 443, 8443],
            'version_regex': r'Apache/(\d+\.\d+\.\d+)',
        },
        'mysql': {
            'product': 'MySQL',
            'default_ports': [3306],
            'version_regex': r'MySQL\s+(\d+\.\d+\.\d+)',
        },
        'mssql': {
            'product': 'Microsoft SQL Server',
            'default_ports': [1433],
            'version_regex': r'SQL\s*Server\s+(\d+)',
        },
        'redis': {
            'product': 'Redis',
            'default_ports': [6379],
            'version_regex': r'Redis\s+version\s+(\d+\.\d+\.\d+)',
        },
        'mongodb': {
            'product': 'MongoDB',
            'default_ports': [27017],
            'version_regex': r'MongoDB\s+(\d+\.\d+\.\d+)',
        },
        'rdp': {
            'product': 'Windows RDP',
            'default_ports': [3389],
            'version_regex': r'RDP',
        },
        'sMB': {
            'product': 'Samba',
            'default_ports': [139, 445],
            'version_regex': r'Samba\s+(\d+\.\d+\.\d+)',
        },
        'dns': {
            'product': 'BIND',
            'default_ports': [53],
            'version_regex': r'BIND\s+(\d+\.\d+\.\d+)',
        },
        'ntp': {
            'product': 'NTP',
            'default_ports': [123],
            'version_regex': r'NTP',
        },
        'smtp': {
            'product': 'Postfix',
            'default_ports': [25, 587],
            'version_regex': r'Postfix',
        },
        'telnet': {
            'product': 'telnet',
            'default_ports': [23],
            'version_regex': r'telnet',
        },
    }

    # Known vulnerable versions database (simplified)
    VULNERABLE_VERSIONS = {
        'OpenSSH': {
            '7.4': {'cve': 'CVE-2018-15473', 'severity': Severity.MEDIUM, 'description': 'User enumeration vulnerability'},
            '7.3': {'cve': 'CVE-2016-6515', 'severity': Severity.HIGH, 'description': 'Remote code execution via integer overflow'},
            '7.2': {'cve': 'CVE-2016-3156', 'severity': Severity.HIGH, 'description': 'Double-free vulnerability'},
            '6.6': {'cve': 'CVE-2014-1692', 'severity': Severity.MEDIUM, 'description': 'Heap buffer overflow'},
        },
        'Apache': {
            '2.4.29': {'cve': 'CVE-2017-15710', 'severity': Severity.HIGH, 'description': 'Cross-site scripting'},
            '2.4.17': {'cve': 'CVE-2015-0253', 'severity': Severity.CRITICAL, 'description': 'Stack buffer overflow'},
        },
        'MySQL': {
            '5.5.49': {'cve': 'CVE-2016-6662', 'severity': Severity.CRITICAL, 'description': 'Remote code execution'},
            '5.6.33': {'cve': 'CVE-2016-6663', 'severity': Severity.CRITICAL, 'description': 'Privilege escalation'},
            '5.7.15': {'cve': 'CVE-2017-3637', 'severity': Severity.HIGH, 'description': 'Buffer overflow'},
        },
        'Redis': {
            '3.2.0': {'cve': 'CVE-2015-4335', 'severity': Severity.CRITICAL, 'description': 'Lua script execution vulnerability'},
            '4.0.0': {'cve': 'CVE-2017-15041', 'severity': Severity.HIGH, 'description': 'Integer overflow'},
        },
        'Samba': {
            '4.6.3': {'cve': 'CVE-2017-12150', 'severity': Severity.CRITICAL, 'description': 'Remote code execution'},
            '4.5.9': {'cve': 'CVE-2017-0145', 'severity': Severity.CRITICAL, 'description': ' EternalBlue-like vulnerability'},
        },
    }

    def __init__(
        self,
        nmap_path: str = 'nmap',
        timeout: int = 300,
        max_concurrent: int = 10
    ):
        """
        Initialize security scanner

        Args:
            nmap_path: Path to nmap executable
            timeout: Scan timeout in seconds
            max_concurrent: Maximum concurrent scans
        """
        self._nmap_path = nmap_path
        self._timeout = timeout
        self._max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _check_nmap_available(self) -> bool:
        """Check if nmap is available"""
        try:
            result = subprocess.run(
                [self._nmap_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def scan_host(
        self,
        host: str,
        ports: str = '1-1000',
        scan_type: str = '-sV',
        os_detection: bool = True
    ) -> ScanResult:
        """
        Scan a single host

        Args:
            host: Target host IP or hostname
            ports: Port range (e.g., '1-1000', '22,80,443')
            scan_type: Nmap scan type flags
            os_detection: Enable OS detection

        Returns:
            ScanResult with port and service information
        """
        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)

        async with self._semaphore:
            return await self._run_nmap_scan(host, ports, scan_type, os_detection)

    async def _run_nmap_scan(
        self,
        host: str,
        ports: str,
        scan_type: str,
        os_detection: bool
    ) -> ScanResult:
        """Run nmap scan asynchronously"""
        start_time = datetime.now()

        # Build nmap command
        cmd = [
            self._nmap_path,
            '-oX', '-',  # XML output to stdout
            '-p', ports,
        ]

        if os_detection:
            cmd.append('-O')

        if scan_type:
            cmd.extend(scan_type.split())

        cmd.append(host)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            proc = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout
                )),
                timeout=self._timeout
            )

            if proc.returncode != 0:
                return ScanResult(
                    host=host,
                    status=ScanStatus.ERROR,
                    error_message=proc.stderr or 'Nmap scan failed'
                )

            # Parse XML output
            result = self._parse_nmap_xml(proc.stdout, host)

            # Calculate scan time
            scan_time = (datetime.now() - start_time).total_seconds()
            result.scan_time = scan_time

            return result

        except asyncio.TimeoutError:
            return ScanResult(
                host=host,
                status=ScanStatus.TIMEOUT,
                error_message='Scan timeout'
            )
        except Exception as e:
            logger.error(f"Nmap scan error for {host}: {e}")
            return ScanResult(
                host=host,
                status=ScanStatus.ERROR,
                error_message=str(e)
            )

    def _parse_nmap_xml(self, xml_output: str, host: str) -> ScanResult:
        """Parse nmap XML output"""
        result = ScanResult(host=host, status=ScanStatus.SUCCESS)

        try:
            root = ET.fromstring(xml_output)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return ScanResult(
                host=host,
                status=ScanStatus.ERROR,
                error_message=f'XML parse error: {e}'
            )

        # Find host element
        for host_elem in root.findall('.//host'):
            # Check if this is our target
            addr = host_elem.find('.//address[@addrtype="ipv4"]')
            if addr is None:
                addr = host_elem.find('.//address[@addrtype="ipv6"]')
            if addr is None:
                addr = host_elem.find('.//address')

            if addr is None:
                continue

            # OS detection
            os_elem = host_elem.find('.//osmatch')
            if os_elem is not None:
                result.os_detection = os_elem.get('name', '')

            # Parse ports
            for port_elem in host_elem.findall('.//port'):
                port_id = port_elem.get('portid', '')
                protocol = port_elem.get('protocol', 'tcp')
                state_elem = port_elem.find('state')
                state = state_elem.get('state', 'unknown') if state_elem is not None else 'unknown'

                service_elem = port_elem.find('service')
                service_name = service_elem.get('name', '') if service_elem is not None else ''
                product = service_elem.get('product', '') if service_elem is not None else ''
                version = service_elem.get('version', '') if service_elem is not None else ''

                # Try to get banner from script output
                banner = ''
                script_elem = port_elem.find('.//script[@id="banner"]')
                if script_elem is not None:
                    banner = script_elem.get('output', '')

                port_info = PortInfo(
                    port=int(port_id),
                    protocol=protocol,
                    state=state,
                    service=service_name,
                    product=product,
                    version=version,
                    banner=banner
                )

                result.ports.append(port_info)
                result.services[int(port_id)] = service_name

        return result

    async def scan_multiple(
        self,
        hosts: List[str],
        ports: str = '1-1000',
        scan_type: str = '-sV'
    ) -> List[ScanResult]:
        """
        Scan multiple hosts concurrently

        Args:
            hosts: List of target hosts
            ports: Port range
            scan_type: Nmap scan type

        Returns:
            List of scan results
        """
        tasks = [
            self.scan_host(host, ports, scan_type)
            for host in hosts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScanResult(
                    host=hosts[i],
                    status=ScanStatus.ERROR,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def check_version_vulnerabilities(
        self,
        service: str,
        version: str
    ) -> List[VulnerabilityResult]:
        """
        Check if a service version has known vulnerabilities

        Args:
            service: Service name
            version: Service version string

        Returns:
            List of vulnerabilities found
        """
        vulnerabilities = []

        service_upper = service.upper()
        version_clean = re.sub(r'[^0-9.]', '', version)

        # Check known vulnerable versions
        for product_name, versions in self.VULNERABLE_VERSIONS.items():
            if product_name.upper() in service_upper:
                for vuln_version, vuln_info in versions.items():
                    if self._version_affected(version_clean, vuln_version):
                        vulnerabilities.append(VulnerabilityResult(
                            host='',
                            port=0,
                            service=service,
                            vulnerability=f"{product_name} {vuln_version}",
                            severity=vuln_info['severity'],
                            cve_id=vuln_info['cve'],
                            description=vuln_info['description']
                        ))

        return vulnerabilities

    def _version_affected(self, version: str, vulnerable_version: str) -> bool:
        """Check if version is affected by vulnerability"""
        if not version or not vulnerable_version:
            return False

        try:
            # Simple version comparison - check if major.minor matches
            v_parts = version.split('.')
            vuln_parts = vulnerable_version.split('.')

            if len(v_parts) >= 2 and len(vuln_parts) >= 2:
                # Compare major and minor version
                if v_parts[0] == vuln_parts[0] and v_parts[1] == vuln_parts[1]:
                    # Check if our version is less than or equal to vulnerable
                    v_minor = int(v_parts[1])
                    vuln_minor = int(vuln_parts[1])
                    return v_minor <= vuln_minor

            return False
        except (ValueError, IndexError):
            return False

    async def check_cve_for_service(
        self,
        service: str,
        version: str,
        port: int
    ) -> List[CVEInfo]:
        """
        Check CVEs for a specific service version

        Args:
            service: Service name
            version: Service version
            port: Port number

        Returns:
            List of CVE information
        """
        cves = []

        vulnerabilities = self.check_version_vulnerabilities(service, version)

        for vuln in vulnerabilities:
            cve_info = CVEInfo(
                cve_id=vuln.cve_id or 'UNKNOWN',
                severity=vuln.severity,
                description=vuln.description,
                cvss_score=vuln.cvss_score
            )
            cves.append(cve_info)

        return cves

    async def full_security_scan(
        self,
        host: str,
        ports: str = '1-10000',
        scan_type: str = '-sV -sC'
    ) -> Dict[str, Any]:
        """
        Perform full security scan with vulnerability checking

        Args:
            host: Target host
            ports: Port range
            scan_type: Nmap scan type

        Returns:
            Complete security scan report
        """
        report = {
            'host': host,
            'scan_time': datetime.now().isoformat(),
            'status': 'pending',
            'ports': [],
            'vulnerabilities': [],
            'services': {},
            'summary': {}
        }

        # Run port scan
        scan_result = await self.scan_host(host, ports, scan_type)
        report['status'] = scan_result.status.value

        if scan_result.status != ScanStatus.SUCCESS:
            report['error'] = scan_result.error_message
            return report

        # Process open ports
        open_ports = []
        for port_info in scan_result.ports:
            if port_info.state == 'open':
                open_ports.append({
                    'port': port_info.port,
                    'protocol': port_info.protocol,
                    'service': port_info.service,
                    'product': port_info.product,
                    'version': port_info.version,
                    'banner': port_info.banner
                })

                # Check for vulnerabilities
                if port_info.product or port_info.service:
                    service_name = port_info.product or port_info.service
                    vuln_results = self.check_version_vulnerabilities(
                        service_name,
                        port_info.version
                    )

                    for vuln in vuln_results:
                        report['vulnerabilities'].append({
                            'port': port_info.port,
                            'service': service_name,
                            'version': port_info.version,
                            'vulnerability': vuln.vulnerability,
                            'severity': vuln.severity.value,
                            'cve_id': vuln.cve_id,
                            'description': vuln.description
                        })

        report['ports'] = open_ports
        report['os'] = scan_result.os_detection
        report['scan_duration'] = scan_result.scan_time

        # Summary
        report['summary'] = {
            'total_open_ports': len(open_ports),
            'critical_vulns': sum(1 for v in report['vulnerabilities'] if v['severity'] == 'critical'),
            'high_vulns': sum(1 for v in report['vulnerabilities'] if v['severity'] == 'high'),
            'medium_vulns': sum(1 for v in report['vulnerabilities'] if v['severity'] == 'medium'),
            'low_vulns': sum(1 for v in report['vulnerabilities'] if v['severity'] == 'low'),
        }

        return report

    async def quick_scan(self, host: str) -> ScanResult:
        """
        Quick port scan for common ports

        Args:
            host: Target host

        Returns:
            Scan result with common ports
        """
        common_ports = '21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080'
        return await self.scan_host(host, common_ports, '-sV', os_detection=False)

    async def stealth_scan(self, host: str, ports: str = '1-1000') -> ScanResult:
        """
        Stealth scan with reduced detection

        Args:
            host: Target host
            ports: Port range

        Returns:
            Scan result
        """
        return await self.scan_host(
            host,
            ports,
            '-sS -Pn -T4',
            os_detection=False
        )

    def get_service_banner(self, host: str, port: int, timeout: int = 5) -> str:
        """
        Grab service banner

        Args:
            host: Target host
            port: Port number
            timeout: Connection timeout

        Returns:
            Banner string
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            return banner
        except Exception as e:
            logger.debug(f"Banner grab failed for {host}:{port} - {e}")
            return ''

    def check_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """
        Check if a specific port is open

        Args:
            host: Target host
            port: Port number
            timeout: Connection timeout

        Returns:
            True if port is open
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False


class CVEDatabase:
    """
    Local CVE database for vulnerability lookups
    """

    def __init__(self):
        self._cves: Dict[str, CVEInfo] = {}
        self._product_index: Dict[str, Set[str]] = {}

    def add_cve(self, cve: CVEInfo):
        """Add CVE to database"""
        self._cves[cve.cve_id] = cve

        # Index by product patterns
        for pattern in ['Apache', 'nginx', 'OpenSSH', 'MySQL', 'PostgreSQL', 'Redis', 'MongoDB']:
            if pattern.lower() in cve.description.lower():
                if pattern not in self._product_index:
                    self._product_index[pattern] = set()
                self._product_index[pattern].add(cve.cve_id)

    def get_cve(self, cve_id: str) -> Optional[CVEInfo]:
        """Get CVE by ID"""
        return self._cves.get(cve_id)

    def get_cves_for_product(self, product: str) -> List[CVEInfo]:
        """Get all CVEs for a product"""
        cve_ids = self._product_index.get(product, set())
        return [self._cves[cve_id] for cve_id in cve_ids if cve_id in self._cves]

    @staticmethod
    def load_from_nvd_feed(feed_path: str) -> 'CVEDatabase':
        """Load CVE database from NVD JSON feed"""
        db = CVEDatabase()

        try:
            with open(feed_path, 'r') as f:
                data = json.load(f)

            for item in data.get('CVE_Items', []):
                cve_id = item.get('cve', {}).get('CVE_data_meta', {}).get('ID', '')

                # Extract CVSS score
                impact = item.get('impact', {})
                cvss_data = impact.get('baseMetricV2', {}) or impact.get('baseMetricV3', {})
                cvss_score = cvss_data.get('cvssV2', {}).get('baseScore', 0.0) or \
                              cvss_data.get('cvssV3', {}).get('baseScore', 0.0)

                # Determine severity
                if cvss_score >= 9.0:
                    severity = Severity.CRITICAL
                elif cvss_score >= 7.0:
                    severity = Severity.HIGH
                elif cvss_score >= 4.0:
                    severity = Severity.MEDIUM
                elif cvss_score > 0:
                    severity = Severity.LOW
                else:
                    severity = Severity.UNKNOWN

                description = item.get('cve', {}).get('description', {}).get('description_data', [{}])[0].get('value', '')

                cve = CVEInfo(
                    cve_id=cve_id,
                    severity=severity,
                    description=description,
                    cvss_score=cvss_score
                )
                db.add_cve(cve)

        except Exception as e:
            logger.error(f"Failed to load CVE database: {e}")

        return db


# Quick vulnerability check helpers
def quick_vuln_check(host: str, port: int) -> List[VulnerabilityResult]:
    """
    Quick vulnerability check for a single port

    Args:
        host: Target host
        port: Port number

    Returns:
        List of potential vulnerabilities
    """
    scanner = SecurityScanner()

    # Check common services
    service_map = {
        22: ('ssh', 'OpenSSH'),
        21: ('ftp', 'vsftpd'),
        80: ('http', 'Apache'),
        443: ('http', 'Apache'),
        3306: ('mysql', 'MySQL'),
        1433: ('mssql', 'Microsoft SQL Server'),
        6379: ('redis', 'Redis'),
        27017: ('mongodb', 'MongoDB'),
        445: ('smb', 'Samba'),
        3389: ('rdp', 'Windows RDP'),
    }

    if port not in service_map:
        return []

    service_key, default_product = service_map[port]

    # Check if port is open first
    if not scanner.check_port_open(host, port):
        return []

    # Get banner
    banner = scanner.get_service_banner(host, port)
    version = ''

    # Try to extract version from banner
    version_match = re.search(r'\d+\.\d+\.\d+', banner)
    if version_match:
        version = version_match.group()

    # Check vulnerabilities
    return scanner.check_version_vulnerabilities(default_product, version)
