"""
Discovery Module Unit Tests

Tests for IP Scanner and SNMP Scanner modules.
Uses DataFactory for test data generation (TDD approach).
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')


# ============== DataFactory for Discovery Tests ==============

class DiscoveryDataFactory:
    """Test data factory for discovery module"""
    
    def __init__(self, seed: int = 42):
        import random
        import uuid
        self._random = random
        self._random.seed(seed)
        self._counter = 0
        self._uuid = uuid
    
    def _uid(self) -> str:
        self._counter += 1
        return f"test_{self._counter}_{self._uuid.uuid4().hex[:8]}"
    
    def ip_address(self, network: str = "192.168.1") -> str:
        return f"{network}.{self._random.randint(1, 254)}"
    
    def hostname(self) -> str:
        prefixes = ["web", "app", "db", "cache", "proxy", "lb", "storage", "node"]
        return f"{self._random.choice(prefixes)}-{self._random.choice(['prod', 'dev', 'test'])}-{self._random.randint(1,99):02d}"
    
    def mac_address(self) -> str:
        return ":".join([f"{self._random.randint(0, 255):02x}" for _ in range(6)])
    
    def discovered_host(self, **overrides) -> dict:
        """Generate DiscoveredHost data"""
        os_types = ["windows", "linux", "unix", "network", "unknown"]
        vendors = ["Cisco", "Huawei", "Juniper", "Dell", "HP", "VMware", "Microsoft", "Linux", None]
        
        data = {
            "ip": self.ip_address(),
            "hostname": self.hostname(),
            "mac": self.mac_address(),
            "os_type": self._random.choice(os_types),
            "os_version": f"{self._random.randint(1,9)}.{self._random.randint(0,20)}.{self._random.randint(0,100)}",
            "vendor": self._random.choice(vendors),
            "ports": self._random.sample([22, 80, 443, 3306, 3389, 8080], k=self._random.randint(1,4)),
            "services": {"http": "Apache", "ssh": "OpenSSH"},
            "status": "up",
            "response_time": self._random.uniform(0.5, 50.0),
            "ttl": self._random.choice([64, 128, 255]),
        }
        data.update(overrides)
        return data
    
    def snmp_device(self, **overrides) -> dict:
        """Generate SNMPDiscoveredDevice data"""
        device_types = ["router", "switch", "server", "workstation", "printer", "firewall", "load_balancer", "storage", "unknown"]
        vendors = ["Cisco", "Juniper", "Huawei", "H3C", "Arista", "Dell", "HP", "VMware", "Microsoft", "Linux"]
        os_types = ["Cisco IOS", "Juniper JunOS", "Huawei VRP", "Linux", "Windows", "VMware ESXi"]
        
        data = {
            "ip": self.ip_address(),
            "hostname": self.hostname(),
            "sys_descr": f"{self._random.choice(vendors)} {self._random.choice(os_types)} Software",
            "sys_object_id": f"1.3.6.1.4.1.{self._random.randint(1, 9999)}.{self._random.randint(1, 100)}",
            "sys_uptime": self._random.randint(100000, 100000000),
            "vendor": self._random.choice(vendors),
            "device_type": self._random.choice(device_types),
            "os_type": self._random.choice(os_types),
            "os_version": f"{self._random.randint(10, 15)}.{self._random.randint(1, 5)}.{self._random.randint(1, 10)}",
            "location": f"DataCenter-{self._random.choice(['A', 'B', 'C'])}",
            "contact": f"admin@{self.hostname()}.local",
            "mac_address": self.mac_address(),
            "interfaces": [
                {"index": i, "description": f"GigabitEthernet0/{i}", "type": "ethernet", "speed": 1000000000}
                for i in range(1, 5)
            ],
            "status": "responding",
            "response_time": self._random.uniform(1.0, 100.0),
            "community": "public",
            "snmp_version": self._random.choice(["v1", "v2c", "v3"]),
        }
        data.update(overrides)
        return data
    
    def ip_range(self, prefix: str = "192.168.1") -> str:
        """Generate random CIDR range"""
        return f"{prefix}.0/30"
    
    def cidr_small(self) -> str:
        """Small CIDR for testing (/30)"""
        return f"{self.ip_address()[:-4]}.0/30"
    
    def cidr_large(self) -> str:
        """Large CIDR for testing (/24)"""
        return f"{self.ip_address()[:-4]}.0/24"


# Fixture
@pytest.fixture
def factory():
    return DiscoveryDataFactory(seed=42)


class TestDiscoveredHost:
    """DiscoveredHost dataclass tests"""
    
    def test_discovered_host_creation(self):
        """Test creating a DiscoveredHost"""
        from modules.collection.discovery.scanner import DiscoveredHost, OSType
        from datetime import datetime
        
        host = DiscoveredHost(
            ip="192.168.1.1",
            hostname="test-host",
            os_type=OSType.LINUX,
            status="up",
            ttl=64,
        )
        
        assert host.ip == "192.168.1.1"
        assert host.hostname == "test-host"
        assert host.os_type == OSType.LINUX
        assert host.status == "up"
        assert host.ttl == 64
    
    def test_discovered_host_to_dict(self):
        """Test converting DiscoveredHost to dict"""
        from modules.collection.discovery.scanner import DiscoveredHost, OSType
        
        host = DiscoveredHost(
            ip="192.168.1.1",
            hostname="test-host",
            os_type=OSType.WINDOWS,
            vendor="Microsoft",
            status="up",
        )
        
        result = host.to_dict()
        
        assert result["ip"] == "192.168.1.1"
        assert result["hostname"] == "test-host"
        assert result["os_type"] == "windows"
        assert result["vendor"] == "Microsoft"
        assert result["status"] == "up"


class TestOSType:
    """OSType enum tests"""
    
    def test_os_type_values(self):
        """Test all OS type values"""
        from modules.collection.discovery.scanner import OSType
        
        assert OSType.WINDOWS.value == "windows"
        assert OSType.LINUX.value == "linux"
        assert OSType.UNIX.value == "unix"
        assert OSType.NETWORK.value == "network"
        assert OSType.UNKNOWN.value == "unknown"


class TestIPScanner:
    """IP Scanner tests"""
    
    def test_scanner_initialization(self):
        """Test IPScanner initialization"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner(timeout=1.0, ping_count=1, max_workers=10)
        
        assert scanner.timeout == 1.0
        assert scanner.ping_count == 1
        assert scanner.max_workers == 10
        assert scanner.ports == IPScanner.COMMON_PORTS
    
    def test_scanner_custom_ports(self):
        """Test IPScanner with custom ports"""
        from modules.collection.discovery.scanner import IPScanner
        
        custom_ports = [22, 80, 443]
        scanner = IPScanner(ports=custom_ports)
        
        assert scanner.ports == custom_ports
    
    def test_identify_service(self):
        """Test service identification"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        assert scanner._identify_service(22, "") == "ssh"
        assert scanner._identify_service(80, "") == "http"
        assert scanner._identify_service(443, "") == "https"
        assert scanner._identify_service(3306, "") == "mysql"
        assert scanner._identify_service(9999, "") == "port-9999"
    
    def test_detect_os_from_banner_windows(self):
        """Test OS detection from Windows banner"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        os_type, version = scanner._detect_os(128, b"Microsoft Windows Server 2012")
        
        assert os_type.value == "windows"
    
    def test_detect_os_from_banner_linux(self):
        """Test OS detection from Linux banner"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        os_type, version = scanner._detect_os(64, b"SSH-2.0-OpenSSH_7.4")
        
        assert os_type.value == "linux"
    
    def test_detect_os_from_banner_cisco(self):
        """Test OS detection from Cisco banner"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        os_type, version = scanner._detect_os(255, b"Cisco IOS Software")
        
        assert os_type.value == "network"
    
    def test_detect_os_from_ttl(self):
        """Test OS detection from TTL"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        # Low TTL = Linux/Unix
        os_type, version = scanner._detect_os(64, b"")
        assert os_type.value == "linux"
        
        # Medium TTL = Windows
        os_type, version = scanner._detect_os(128, b"")
        assert os_type.value == "windows"
        
        # High TTL = Network device
        os_type, version = scanner._detect_os(255, b"")
        assert os_type.value == "network"
    
    def test_detect_vendor(self):
        """Test vendor detection from banner"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        assert scanner._detect_vendor(b"Cisco IOS") == "Cisco"
        assert scanner._detect_vendor(b"Huawei VRP") == "Huawei"
        assert scanner._detect_vendor(b"VMware ESXi") == "VMware"
        assert scanner._detect_vendor(b"HP ProCurve") == "HP"
        assert scanner._detect_vendor(b"random text") is None
    
    def test_parse_target(self):
        """Test IP range parsing"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        # Test CIDR
        targets = scanner._parse_target("192.168.1.0/30")
        assert len(targets) == 2
        assert "192.168.1.1" in targets
        assert "192.168.1.2" in targets
        
        # Test single IP
        targets = scanner._parse_target("192.168.1.1")
        assert len(targets) == 1
        assert "192.168.1.1" in targets
    
    def test_invalid_cidr(self):
        """Test invalid CIDR handling"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        with pytest.raises(ValueError):
            scanner._parse_target("invalid")


class TestIPScannerAsync:
    """Async IPScanner tests"""
    
    @pytest.mark.asyncio
    async def test_scan_single_host_down(self):
        """Test scanning a host that is down"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner(timeout=0.5, ping_count=1)
        
        # Use a non-routable IP that should fail quickly
        result = await scanner._scan_single_host("10.255.255.1")
        
        assert result.status == "down"
        assert result.ip == "10.255.255.1"
    
    @pytest.mark.asyncio
    async def test_tcp_check(self):
        """Test TCP check functionality"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner(timeout=0.5)
        
        # Test against a known closed port
        result = await scanner._tcp_check("127.0.0.1", [65000])
        
        # Should return False for closed port on localhost
        assert result == False
    
    @pytest.mark.asyncio
    async def test_scan_small_range(self):
        """Test scanning a small IP range"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner(timeout=1.0, max_workers=5)
        
        # Scan a /30 range - should be quick
        results = await scanner.scan_ip_range("192.168.1.0/30")
        
        # Results should be a list (some may be down)
        assert isinstance(results, list)
        for host in results:
            assert host.status == "up"


class TestSNMPDiscoveredDevice:
    """SNMPDiscoveredDevice tests"""
    
    def test_device_creation(self):
        """Test creating SNMPDiscoveredDevice"""
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        
        device = SNMPDiscoveredDevice(
            ip="192.168.1.1",
            hostname="router1",
            vendor="Cisco",
            device_type=SNMPDeviceType.ROUTER,
            status="responding",
        )
        
        assert device.ip == "192.168.1.1"
        assert device.hostname == "router1"
        assert device.vendor == "Cisco"
        assert device.device_type == SNMPDeviceType.ROUTER
    
    def test_device_to_dict(self):
        """Test converting device to dict"""
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        
        device = SNMPDiscoveredDevice(
            ip="192.168.1.1",
            sys_descr="Cisco IOS Router",
            vendor="Cisco",
            device_type=SNMPDeviceType.ROUTER,
        )
        
        result = device.to_dict()
        
        assert result["ip"] == "192.168.1.1"
        assert result["sys_descr"] == "Cisco IOS Router"
        assert result["device_type"] == "router"


class TestSNMPDeviceType:
    """SNMPDeviceType enum tests"""
    
    def test_device_type_values(self):
        """Test all device type values"""
        from modules.collection.discovery.snmp_scanner import SNMPDeviceType
        
        assert SNMPDeviceType.ROUTER.value == "router"
        assert SNMPDeviceType.SWITCH.value == "switch"
        assert SNMPDeviceType.SERVER.value == "server"
        assert SNMPDeviceType.FIREWALL.value == "firewall"


class TestSNMPScanner:
    """SNMP Scanner tests"""
    
    def test_scanner_initialization(self):
        """Test SNMPScanner initialization"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner(timeout=3.0, retries=2, max_workers=10)
        
        assert scanner.timeout == 3.0
        assert scanner.retries == 2
        assert scanner.max_workers == 10
        assert "public" in scanner.communities
    
    def test_custom_communities(self):
        """Test SNMPScanner with custom communities"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        communities = ["public", "private", "custom"]
        scanner = SNMPScanner(communities=communities)
        
        assert scanner.communities == communities
    
    def test_parse_target_cidr(self):
        """Test target parsing for CIDR"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        targets = scanner._parse_target("192.168.1.0/28")
        
        assert len(targets) == 14  # /28 has 14 usable hosts
        assert "192.168.1.1" in targets
    
    def test_parse_target_single_ip(self):
        """Test target parsing for single IP"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        targets = scanner._parse_target("192.168.1.1")
        
        assert len(targets) == 1
        assert targets[0] == "192.168.1.1"
    
    def test_detect_vendor_from_object_id(self):
        """Test vendor detection from sysObjectID"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Cisco OID
        vendor = scanner._detect_vendor("1.3.6.1.4.1.9.1.1", None)
        assert vendor == "Cisco"
        
        # Juniper OID
        vendor = scanner._detect_vendor("1.3.6.1.4.1.2636.1.1", None)
        assert vendor == "Juniper"
    
    def test_detect_vendor_from_descr(self):
        """Test vendor detection from sysDescr"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        vendor = scanner._detect_vendor(None, "Cisco IOS Software")
        assert vendor == "Cisco"
        
        vendor = scanner._detect_vendor(None, "Juniper JunOS 12.3")
        assert vendor == "Juniper"
    
    def test_detect_device_type_router(self):
        """Test device type detection for router"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        device_type = scanner._detect_device_type("Cisco IOS Router", None)
        assert device_type == SNMPDeviceType.ROUTER
    
    def test_detect_device_type_firewall(self):
        """Test device type detection for firewall"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        device_type = scanner._detect_device_type("FortiGate Firewall", None)
        assert device_type == SNMPDeviceType.FIREWALL
    
    def test_detect_device_type_unknown(self):
        """Test device type detection for unknown"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        device_type = scanner._detect_device_type("Some Unknown Device", None)
        assert device_type == SNMPDeviceType.UNKNOWN
    
    def test_detect_os_type(self):
        """Test OS type detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        os_type = scanner._detect_os_type("Cisco IOS Software, Version 15.2")
        assert os_type == "Cisco IOS"
        
        os_type = scanner._detect_os_type("Linux server 3.10.0")
        assert os_type == "Linux"
        
        os_type = scanner._detect_os_type("Windows Server 2012 R2")
        assert os_type == "Windows"
    
    def test_detect_os_version(self):
        """Test OS version detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        version = scanner._detect_os_version("Cisco IOS 15.2.4M")
        assert version == "15.2.4M"
        
        version = scanner._detect_os_version("Linux version 3.10.0-514.el7.x86_64")
        assert version == "3.10.0"


class TestSNMPScannerAsync:
    """Async SNMPScanner tests"""
    
    @pytest.mark.asyncio
    async def test_scan_network_simulated(self):
        """Test network scan with simulated response"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # This will use simulated responses since pysnmp may not be available
        devices = await scanner.scan_network(
            target="192.168.1.1",
            community="public",
        )
        
        assert isinstance(devices, list)
    
    @pytest.mark.asyncio
    async def test_discover_snmp_devices(self):
        """Test SNMP device discovery"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        devices = await scanner.discover_snmp_devices(
            cidr="192.168.1.0/30",
            communities=["public"],
        )
        
        assert isinstance(devices, list)


class TestDiscoveryIntegration:
    """Integration tests for discovery module"""
    
    def test_import_discovered_device(self):
        """Test importing discovered device"""
        from modules.collection.discovery.scanner import DiscoveredHost, OSType
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        
        # IP Scanner host
        ip_host = DiscoveredHost(
            ip="192.168.1.100",
            hostname="new-server",
            os_type=OSType.LINUX,
            vendor="Ubuntu",
            status="up",
        )
        
        # SNMP device
        snmp_device = SNMPDiscoveredDevice(
            ip="192.168.1.100",
            hostname="new-server",
            sys_descr="Ubuntu 20.04 LTS",
            vendor="Linux",
            device_type=SNMPDeviceType.SERVER,
        )
        
        # Both should have the same IP
        assert ip_host.ip == snmp_device.ip


class TestScannerClose:
    """Test scanner cleanup"""
    
    def test_ip_scanner_close(self):
        """Test IPScanner close"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        scanner.close()  # Should not raise
    
    def test_snmp_scanner_close(self):
        """Test SNMPScanner close"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        scanner.close()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestDiscoveryDataFactory:
    """Tests for DiscoveryDataFactory"""
    
    def test_factory_ip_address(self, factory):
        """Test IP address generation"""
        ip = factory.ip_address()
        assert ip.startswith("192.168.1.")
        parts = ip.split(".")
        assert 1 <= int(parts[3]) <= 254
    
    def test_factory_hostname(self, factory):
        """Test hostname generation"""
        hostname = factory.hostname()
        assert "-" in hostname
        assert len(hostname) > 5
    
    def test_factory_mac_address(self, factory):
        """Test MAC address generation"""
        mac = factory.mac_address()
        parts = mac.split(":")
        assert len(parts) == 6
        for part in parts:
            assert len(part) == 2
            assert int(part, 16) <= 255
    
    def test_factory_discovered_host(self, factory):
        """Test discovered host data generation"""
        host_data = factory.discovered_host()
        
        assert "ip" in host_data
        assert "hostname" in host_data
        assert "mac" in host_data
        assert "os_type" in host_data
        assert "ports" in host_data
        assert isinstance(host_data["ports"], list)
    
    def test_factory_discovered_host_with_overrides(self, factory):
        """Test discovered host with overrides"""
        host_data = factory.discovered_host(ip="10.0.0.1", status="down")
        assert host_data["ip"] == "10.0.0.1"
        assert host_data["status"] == "down"
    
    def test_factory_snmp_device(self, factory):
        """Test SNMP device data generation"""
        device_data = factory.snmp_device()
        
        assert "ip" in device_data
        assert "hostname" in device_data
        assert "sys_descr" in device_data
        assert "vendor" in device_data
        assert "device_type" in device_data
        assert isinstance(device_data["interfaces"], list)
    
    def test_factory_cidr_small(self, factory):
        """Test small CIDR generation"""
        cidr = factory.cidr_small()
        assert "/30" in cidr
        parts = cidr.split(".")
        assert len(parts) == 4
    
    def test_factory_cidr_large(self, factory):
        """Test large CIDR generation"""
        cidr = factory.cidr_large()
        assert "/24" in cidr


class TestDiscoveryDataDriven:
    """Data-driven tests using factory-generated data"""
    
    def test_ip_scanner_with_factory_data(self, factory):
        """Test IPScanner with factory-generated data"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        # Generate multiple hosts
        for _ in range(3):
            ip = factory.ip_address()
            host_data = factory.discovered_host(ip=ip)
            
            # Test OS detection with generated data
            os_type, version = scanner._detect_os(
                host_data["ttl"], 
                host_data["vendor"].encode() if host_data["vendor"] else b""
            )
            assert os_type is not None
    
    def test_snmp_scanner_with_factory_data(self, factory):
        """Test SNMPScanner with factory-generated data"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Test vendor detection with factory data
        device_data = factory.snmp_device(vendor="Cisco", sys_object_id="1.3.6.1.4.1.9.1.1")
        vendor = scanner._detect_vendor(device_data["sys_object_id"], device_data["sys_descr"])
        assert vendor == "Cisco"
        
        # Test device type detection
        device_type = scanner._detect_device_type(device_data["sys_descr"], device_data["sys_object_id"])
        assert device_type is not None
    
    def test_multiple_hosts_to_dict(self, factory):
        """Test converting multiple hosts to dict"""
        from modules.collection.discovery.scanner import DiscoveredHost, OSType
        
        hosts = []
        for _ in range(5):
            data = factory.discovered_host()
            host = DiscoveredHost(
                ip=data["ip"],
                hostname=data["hostname"],
                os_type=OSType(data["os_type"]),
                status=data["status"],
            )
            hosts.append(host)
        
        # All hosts should convert to dict properly
        for host in hosts:
            d = host.to_dict()
            assert "ip" in d
            assert "os_type" in d
            assert "status" in d


class TestDiscoveryEdgeCases:
    """Edge case tests"""
    
    def test_ip_scanner_invalid_cidr_various(self):
        """Test various invalid CIDR formats"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        invalid_targets = ["invalid", "256.1.1.1/24", "192.168.1.0/33", ""]
        
        for target in invalid_targets:
            try:
                if target:  # Skip empty
                    scanner._parse_target(target)
                # If no exception, the test should handle it
                assert target == "" or "/" not in target
            except ValueError:
                pass  # Expected for invalid targets
    
    def test_snmp_scanner_empty_responses(self):
        """Test SNMP scanner with empty/no responses"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Test vendor detection with None values
        vendor = scanner._detect_vendor(None, None)
        assert vendor is None
        
        # Test device type detection with empty string
        device_type = scanner._detect_device_type("", "")
        from modules.collection.discovery.snmp_scanner import SNMPDeviceType
        assert device_type == SNMPDeviceType.UNKNOWN
    
    def test_os_detect_empty_banner(self):
        """Test OS detection with empty banner"""
        from modules.collection.discovery.scanner import IPScanner
        
        scanner = IPScanner()
        
        # Empty banner with different TTLs
        os_type, version = scanner._detect_os(64, b"")
        assert os_type.value == "linux"
        
        os_type, version = scanner._detect_os(128, b"")
        assert os_type.value == "windows"
        
        os_type, version = scanner._detect_os(255, b"")
        assert os_type.value == "network"
        
        os_type, version = scanner._detect_os(None, b"")
        assert os_type.value == "unknown"
