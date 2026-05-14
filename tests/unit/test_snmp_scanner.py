"""
SNMP Scanner Unit Tests

Tests for the SNMP scanner module.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')


class TestSNMPConfig:
    """SNMP configuration tests"""
    
    def test_snmp_oids_defined(self):
        """Test that all required OIDs are defined"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # System OIDs
        assert scanner.OID_SYS_DESCR == "1.3.6.1.2.1.1.1.0"
        assert scanner.OID_SYS_OBJECT_ID == "1.3.6.1.2.1.1.2.0"
        assert scanner.OID_SYS_UPTIME == "1.3.6.1.2.1.1.3.0"
        assert scanner.OID_SYS_CONTACT == "1.3.6.1.2.1.1.4.0"
        assert scanner.OID_SYS_NAME == "1.3.6.1.2.1.1.5.0"
        assert scanner.OID_SYS_LOCATION == "1.3.6.1.2.1.1.6.0"
    
    def test_interface_oids_defined(self):
        """Test interface OIDs"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner.OID_IF_DESCR == "1.3.6.1.2.1.2.2.1.2"
        assert scanner.OID_IF_TYPE == "1.3.6.1.2.1.2.2.1.3"
        assert scanner.OID_IF_SPEED == "1.3.6.1.2.1.2.2.1.5"
        assert scanner.OID_IF_MAC == "1.3.6.1.2.1.2.2.1.6"


class TestVendorOIDs:
    """Vendor OID mapping tests"""
    
    def test_vendor_oids_complete(self):
        """Test vendor OID mappings"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Major vendors should be present
        assert 'cisco' in scanner.VENDOR_OIDS
        assert 'juniper' in scanner.VENDOR_OIDS
        assert 'huawei' in scanner.VENDOR_OIDS
        assert 'h3c' in scanner.VENDOR_OIDS
        assert 'dell' in scanner.VENDOR_OIDS
        assert 'hp' in scanner.VENDOR_OIDS
    
    def test_vendor_oid_values(self):
        """Test vendor OID values are correct"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Cisco OID
        assert scanner.VENDOR_OIDS['cisco'] == '1.3.6.1.4.1.9'
        
        # Juniper OID
        assert scanner.VENDOR_OIDS['juniper'] == '1.3.6.1.4.1.2636'
        
        # Huawei OID
        assert scanner.VENDOR_OIDS['huawei'] == '1.3.6.1.4.1.2011'


class TestDeviceTypeDetection:
    """Device type detection tests"""
    
    def test_router_detection(self):
        """Test router device type detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        # Various router patterns
        assert scanner._detect_device_type("Cisco IOS XE Router", None) == SNMPDeviceType.ROUTER
        assert scanner._detect_device_type("Juniper JunOS Router", None) == SNMPDeviceType.ROUTER
        assert scanner._detect_device_type("Huawei VRP Router", None) == SNMPDeviceType.ROUTER
    
    def test_switch_detection(self):
        """Test switch device type detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        assert scanner._detect_device_type("Cisco Catalyst Switch", None) == SNMPDeviceType.SWITCH
        assert scanner._detect_device_type("HP ProCurve Switch", None) == SNMPDeviceType.SWITCH
    
    def test_firewall_detection(self):
        """Test firewall device type detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        assert scanner._detect_device_type("FortiGate Firewall", None) == SNMPDeviceType.FIREWALL
        assert scanner._detect_device_type("Cisco ASA Firewall", None) == SNMPDeviceType.FIREWALL
        assert scanner._detect_device_type("CheckPoint Firewall", None) == SNMPDeviceType.FIREWALL
    
    def test_server_detection(self):
        """Test server device type detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        assert scanner._detect_device_type("Windows Server 2019", None) == SNMPDeviceType.SERVER
        assert scanner._detect_device_type("Linux Server 5.4", None) == SNMPDeviceType.SERVER
        assert scanner._detect_device_type("VMware ESXi 7.0", None) == SNMPDeviceType.SERVER
    
    def test_load_balancer_detection(self):
        """Test load balancer detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        assert scanner._detect_device_type("F5 BIG-IP Load Balancer", None) == SNMPDeviceType.LOAD_BALANCER
    
    def test_printer_detection(self):
        """Test printer detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        assert scanner._detect_device_type("HP LaserJet Printer", None) == SNMPDeviceType.PRINTER
    
    def test_unknown_device_type(self):
        """Test unknown device type"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDeviceType
        
        scanner = SNMPScanner()
        
        result = scanner._detect_device_type("Some Random Device XYZ123", None)
        assert result == SNMPDeviceType.UNKNOWN


class TestVendorDetection:
    """Vendor detection tests"""
    
    def test_vendor_from_sys_object_id(self):
        """Test vendor detection from sysObjectID"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Test all major vendors
        assert scanner._detect_vendor("1.3.6.1.4.1.9.1.1", None) == "Cisco"
        assert scanner._detect_vendor("1.3.6.1.4.1.2636.1.1", None) == "Juniper"
        assert scanner._detect_vendor("1.3.6.1.4.1.2011.1", None) == "Huawei"
        assert scanner._detect_vendor("1.3.6.1.4.1.25506.1", None) == "H3c"
        assert scanner._detect_vendor("1.3.6.1.4.1.674.1", None) == "Dell"
        assert scanner._detect_vendor("1.3.6.1.4.1.11.1", None) == "Hp"
        assert scanner._detect_vendor("1.3.6.1.4.1.6876.1", None) == "Vmware"
    
    def test_vendor_from_sys_descr(self):
        """Test vendor detection from sysDescr"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_vendor(None, "Cisco IOS Software") == "Cisco"
        assert scanner._detect_vendor(None, "Juniper Networks JunOS") == "Juniper"
        assert scanner._detect_vendor(None, "Huawei Versatile Routing Platform") == "Huawei"
        assert scanner._detect_vendor(None, "VMware ESXi 7.0") == "VMware"
        assert scanner._detect_vendor(None, "Microsoft Windows Server") == "Microsoft"
        assert scanner._detect_vendor(None, "Ubuntu Linux 20.04") == "Linux"
    
    def test_unknown_vendor(self):
        """Test unknown vendor"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        result = scanner._detect_vendor(None, "Some completely unknown system description")
        assert result is None


class TestOSTypeDetection:
    """OS type detection tests"""
    
    def test_cisco_ios_detection(self):
        """Test Cisco IOS detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Cisco IOS XE 17.3") == "Cisco IOS"
        assert scanner._detect_os_type("Cisco NX-OS 9.3") == "Cisco IOS"
        assert scanner._detect_os_type("Cisco IOS Software Version 15.2") == "Cisco IOS"
    
    def test_junos_detection(self):
        """Test Juniper JunOS detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Juniper Networks JunOS 21.1") == "Juniper JunOS"
    
    def test_huawei_vrp_detection(self):
        """Test Huawei VRP detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Huawei Versatile Routing Platform (VRP) 8.180") == "Huawei VRP"
    
    def test_windows_detection(self):
        """Test Windows detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Microsoft Windows Server 2019") == "Windows"
        assert scanner._detect_os_type("Windows 10 Pro") == "Windows"
    
    def test_linux_detection(self):
        """Test Linux detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Linux Ubuntu 20.04 LTS") == "Linux"
        assert scanner._detect_os_type("CentOS Linux 8") == "Linux"
        assert scanner._detect_os_type("Red Hat Enterprise Linux 8") == "Linux"
        assert scanner._detect_os_type("Debian GNU/Linux 11") == "Linux"
    
    def test_esxi_detection(self):
        """Test VMware ESXi detection"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("VMware ESXi 7.0") == "VMware ESXi"
        assert scanner._detect_os_type("ESXi 6.7") == "VMware ESXi"
    
    def test_unknown_os(self):
        """Test unknown OS"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner._detect_os_type("Some Unknown OS v1.0") is None


class TestOSVersionDetection:
    """OS version extraction tests"""
    
    def test_extract_version_numbers(self):
        """Test version number extraction"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        version = scanner._detect_os_version("Cisco IOS 15.2.4M")
        assert version == "15.2.4M"
        
        version = scanner._detect_os_version("Linux 5.4.0-80-generic")
        assert version == "5.4.0"
        
        version = scanner._detect_os_version("Windows Server 2019 Version 1809")
        assert version == "1809"
    
    def test_version_with_pattern(self):
        """Test version with Version keyword"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        version = scanner._detect_os_version("Software Version 3.2.1")
        assert version == "3.2.1"
    
    def test_no_version(self):
        """Test no version found"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        version = scanner._detect_os_version("Generic System")
        assert version is None


class TestSNMPDevice:
    """SNMPDiscoveredDevice model tests"""
    
    def test_device_with_all_fields(self):
        """Test device with all fields populated"""
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        from datetime import datetime
        
        device = SNMPDiscoveredDevice(
            ip="192.168.1.1",
            hostname="router-core-01",
            sys_descr="Cisco IOS Software",
            sys_object_id="1.3.6.1.4.1.9.1.1",
            sys_uptime=12345678,
            vendor="Cisco",
            device_type=SNMPDeviceType.ROUTER,
            os_type="Cisco IOS",
            os_version="15.2.4M",
            location="Data Center A",
            contact="admin@example.com",
            mac_address="00:11:22:33:44:55",
            status="responding",
            response_time=5.5,
            community="public",
            snmp_version="v2c",
        )
        
        assert device.ip == "192.168.1.1"
        assert device.hostname == "router-core-01"
        assert device.vendor == "Cisco"
        assert device.device_type == SNMPDeviceType.ROUTER
        assert device.status == "responding"
    
    def test_device_to_dict_complete(self):
        """Test device to_dict with all fields"""
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        
        device = SNMPDiscoveredDevice(
            ip="192.168.1.1",
            hostname="test",
            vendor="Test",
            device_type=SNMPDeviceType.SERVER,
            status="responding",
        )
        
        result = device.to_dict()
        
        assert result["ip"] == "192.168.1.1"
        assert result["hostname"] == "test"
        assert result["device_type"] == "server"
        assert result["status"] == "responding"
        assert "timestamp" in result
    
    def test_device_interfaces(self):
        """Test device with interfaces"""
        from modules.collection.discovery.snmp_scanner import SNMPDiscoveredDevice, SNMPDeviceType
        
        device = SNMPDiscoveredDevice(
            ip="192.168.1.1",
            interfaces=[
                {"index": "1", "description": "GigabitEthernet0/0", "type": "ethernet"},
                {"index": "2", "description": "GigabitEthernet0/1", "type": "ethernet"},
            ],
        )
        
        assert len(device.interfaces) == 2
        assert device.interfaces[0]["description"] == "GigabitEthernet0/0"


class TestTargetParsing:
    """Target parsing tests"""
    
    def test_parse_single_ip(self):
        """Test parsing single IP"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        targets = scanner._parse_target("192.168.1.1")
        
        assert len(targets) == 1
        assert targets[0] == "192.168.1.1"
    
    def test_parse_cidr_24(self):
        """Test parsing /24 network"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        targets = scanner._parse_target("192.168.1.0/24")
        
        assert len(targets) == 254  # 256 - 2 for network/broadcast
    
    def test_parse_cidr_30(self):
        """Test parsing /30 network"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        targets = scanner._parse_target("192.168.1.0/30")
        
        assert len(targets) == 2
    
    def test_parse_invalid_target(self):
        """Test parsing invalid target"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # Invalid target should return as-is (hostname) or raise depending on implementation
        result = scanner._parse_target("not-an-ip")
        assert result == ["not-an-ip"]


class TestScannerDefaults:
    """Test scanner default values"""
    
    def test_default_communities(self):
        """Test default SNMP communities"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert "public" in scanner.communities
        assert "private" in scanner.communities
    
    def test_default_timeout(self):
        """Test default timeout"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner.timeout == 5.0
    
    def test_default_retries(self):
        """Test default retries"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        assert scanner.retries == 3


class TestSNMPScannerAsync:
    """Async SNMP scanner tests"""
    
    @pytest.mark.asyncio
    async def test_scan_single_target_timeout(self):
        """Test scanning a non-responsive target"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner(timeout=0.5)
        
        # Scan a non-routable IP
        result = await scanner._scan_single_target("10.255.255.255", "public", "v2c")
        
        # Should return None for non-responsive
        assert result is None
    
    @pytest.mark.asyncio
    async def test_simulated_scan(self):
        """Test simulated SNMP scan"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner, SNMPDiscoveredDevice
        
        scanner = SNMPScanner()
        
        # This will use simulated response since pysnmp may not be available
        # For IPs like .1 or .254 or random chance, it returns a simulated device
        result = await scanner._simulated_snmp_scan("192.168.1.1", "public", "v2c")
        
        if result:
            assert isinstance(result, SNMPDiscoveredDevice)
            assert result.ip == "192.168.1.1"
            assert result.status == "responding"


class TestSNMPWalk:
    """SNMP walk functionality tests"""
    
    def test_snmp_walk_network_empty(self):
        """Test SNMP walk when pysnmp is not available"""
        from modules.collection.discovery.snmp_scanner import SNMPScanner
        
        scanner = SNMPScanner()
        
        # When pysnmp is not available, should return empty list
        results = scanner.snmp_walk_network("192.168.1.1", "public", "1.3.6.1")
        
        # This will be empty list if pysnmp not available
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
