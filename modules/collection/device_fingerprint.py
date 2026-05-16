# -*- coding: utf-8 -*-
"""


banner、SNMP OID、MAC OUI、
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceCategory(str, Enum):
    """"""
    SERVER = "server"           # 
    SWITCH = "switch"           # 
    ROUTER = "router"          # 
    FIREWALL = "firewall"       # 
    WIRELESS = "wireless"       # AP
    STORAGE = "storage"         # 
    PRINTER = "printer"        # 
    CAMERA = "camera"           # 
    LOAD_BALANCER = "loadbalancer"  # 
    IDS_IPS = "ids_ips"        # /
    UPS = "ups"                # UPS
    OTHER = "other"


# =============================================================================
# 
# =============================================================================

@dataclass
class VendorSignature:
    """"""
    name: str                           # 
    short_name: str                     # 
    patterns: List[bytes]               # banner
    category: DeviceCategory            # 
    default_creds: List[Dict]           # 


@dataclass
class ModelSignature:
    """"""
    vendor: str                         # 
    model: str                          # 
    patterns: List[bytes]               # banner
    snmp_oids: List[str]               # SNMP OID
    ports: List[int]                   # 
    category: DeviceCategory            # 


# （）
VENDOR_SIGNATURES: List[VendorSignature] = [
    VendorSignature(
        name="Cisco Systems",
        short_name="Cisco",
        patterns=[
            b"cisco", b"ios-xe", b"ios-xr", b"nx-os", b"nexus",
            b"cisco ios", b"cisco internetwork operating system",
            b"cisco fabricpath", b"cisco me-fp",
            b"<cisco>", b"cisco networkus",
            b"cisco webex",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "cisco", "password": "cisco"},
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "cisco", "password": "Cisco123"},
            {"protocol": "ssh", "username": "admin", "password": "Cisco123"},
            {"protocol": "http", "username": "cisco", "password": "cisco"},
        ]
    ),
    VendorSignature(
        name="Huawei Technologies",
        short_name="Huawei",
        patterns=[
            b"huawei", b"vrp", b"quidway", b"sima",
            b"huawei proprietary", b"huawei vers",
            b"huawei s", b"huawei ar", b"huawei s5720",
            b"huawei s9700", b"huawei s9700",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin@huawei.com"},
            {"protocol": "ssh", "username": "admin", "password": "Admin@123"},
            {"protocol": "ssh", "username": "root", "password": "Huawei@123"},
            {"protocol": "http", "username": "admin", "password": "admin@huawei.com"},
        ]
    ),
    VendorSignature(
        name="H3C (Huawei 3Com)",
        short_name="H3C",
        patterns=[
            b"h3c", b"comware", b"3com",
            b"h3c s", b"h3c s5120", b"h3c s5500",
            b"imc", b"c3g", b"3com SuperStack",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "manager", "password": "manager"},
            {"protocol": "http", "username": "admin", "password": "admin123"},
        ]
    ),
    VendorSignature(
        name="Juniper Networks",
        short_name="Juniper",
        patterns=[
            b"juniper", b"junos", b"screenos",
            b"juniper networks", b"juniper srx",
            b"juniper ex", b"juniper mx",
            b"juniper networks, inc",
        ],
        category=DeviceCategory.ROUTER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": "root123"},
            {"protocol": "ssh", "username": "admin", "password": "admin123"},
            {"protocol": "http", "username": "admin", "password": "admin123"},
        ]
    ),
    VendorSignature(
        name="Arista Networks",
        short_name="Arista",
        patterns=[
            b"arista", b"eos",
            b"arista networks", b"arista switch",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": ""},
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": ""},
        ]
    ),
    VendorSignature(
        name="Dell EMC",
        short_name="Dell",
        patterns=[
            b"dell", b"powerconnect", b"poweredge",
            b"dell networking", b"dell emc",
            b"dell inc", b"dell s", b"dell n",
            b"dell force10", b"dell ftos",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "root", "password": "calvin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Hewlett Packard Enterprise",
        short_name="HPE",
        patterns=[
            b"hp ", b"hpe", b"procurve", b"aruba",
            b"hewlett", b"hewlett-packard", b"hp-ux",
            b"hp s", b"hp networking", b"hp l",
            b"hpe snmp", b"arubaos",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "manager", "password": "manager"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="TP-Link",
        short_name="TP-Link",
        patterns=[
            b"tp-link", b"tp link", b"tp-link technologies",
            b"tl-", b"tp-link n", b"tp-link corp",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="TP-Link Enterprise",
        short_name="TP-Link",
        patterns=[b"tp-link omada", b"omada controller"],
        category=DeviceCategory.WIRELESS,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="D-Link Corporation",
        short_name="D-Link",
        patterns=[
            b"d-link", b"dlink", b"d link",
            b"d-link corp", b"dlink systems",
            b"dgs-", b"des-", b"dgs",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
            {"protocol": "ssh", "username": "admin", "password": "admin123"},
        ]
    ),
    VendorSignature(
        name="TP-Link",
        short_name="IP-Camera",
        patterns=[
            b"ipcam", b"ip camera", b"ipcam_", b"camera",
            b"tutk", b"iotcamera", b"ipcamera",
        ],
        category=DeviceCategory.CAMERA,
        default_creds=[
            {"protocol": "rtsp", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Hikvision Digital Technology",
        short_name="Hikvision",
        patterns=[
            b"hikvision", b"hik digital", b"hik-connect",
            b"hikvision camera", b"hikvision nvr",
            b"DS-2CD", b"DS-2CE", b"DS-7100", b"DS-7600",
            b"iVMS", b"EZVIZ", b"ezviz",
        ],
        category=DeviceCategory.CAMERA,
        default_creds=[
            {"protocol": "rtsp", "username": "admin", "password": "admin"},
            {"protocol": "rtsp", "username": "admin", "password": "hikvision123"},
            {"protocol": "http", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "hikvision12345"},
        ]
    ),
    VendorSignature(
        name="Dahua Technology",
        short_name="Dahua",
        patterns=[
            b"dahua", b"dahua technology", b"dahuatech",
            b"dahua g", b"dahua s", b"dahua nvr",
            b"DH-IPC", b"DH-NVR", b"SmartPSS",
        ],
        category=DeviceCategory.CAMERA,
        default_creds=[
            {"protocol": "rtsp", "username": "admin", "password": "admin"},
            {"protocol": "rtsp", "username": "admin", "password": "admin12345"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Fortinet",
        short_name="Fortinet",
        patterns=[
            b"fortinet", b"fortigate", b"fortios",
            b"fortinet fortigate", b"forti OS",
            b"fortinet security fabric",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": ""},
            {"protocol": "http", "username": "admin", "password": ""},
        ]
    ),
    VendorSignature(
        name="Palo Alto Networks",
        short_name="PaloAlto",
        patterns=[
            b"palo alto", b"pan-", b"panos",
            b"palo alto networks", b"paloaltonetworks",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Check Point Software Technologies",
        short_name="CheckPoint",
        patterns=[
            b"check point", b"cpmodule", b"cpmodule",
            b"check point software", b"Gaia",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="SonicWall",
        short_name="SonicWall",
        patterns=[
            b"sonicwall", b"sonic os", b"sonicwall gms",
            b"sonicwall inc", b"sonicwall netext",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "password"},
            {"protocol": "http", "username": "admin", "password": "password"},
        ]
    ),
    VendorSignature(
        name="WatchGuard Technologies",
        short_name="WatchGuard",
        patterns=[
            b"watchguard", b"watch guard", b"firebox",
            b"wg", b"watchguard inc",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "wg"},
            {"protocol": "http", "username": "admin", "password": "wg"},
        ]
    ),
    VendorSignature(
        name="Ubuntu",
        short_name="Ubuntu",
        patterns=[
            b"ubuntu", b"ubuntu linux",
            b"ubuntu 2", b"ubuntu 3", b"ubuntu 4",
            b"ubuntu 2", b"ubuntu 24.04", b"ubuntu 22.04", b"ubuntu 20.04",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "ubuntu", "password": ""},
            {"protocol": "ssh", "username": "root", "password": ""},
        ]
    ),
    VendorSignature(
        name="CentOS",
        short_name="CentOS",
        patterns=[
            b"centos",
            b"centos linux", b"centos release",
            b"centos stream",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": ""},
        ]
    ),
    VendorSignature(
        name="Red Hat",
        short_name="RHEL",
        patterns=[
            b"red hat", b"redhat", b"rhel",
            b"red hat enterprise linux", b"rhel",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": ""},
        ]
    ),
    VendorSignature(
        name="Rocky Linux",
        short_name="Rocky",
        patterns=[
            b"rocky", b"rocky linux",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": ""},
        ]
    ),
    VendorSignature(
        name="Alibaba Cloud",
        short_name="Alibaba",
        patterns=[
            b"alibaba", b"aliyun", b"alisth",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[]
    ),
    VendorSignature(
        name="Tencent Cloud",
        short_name="Tencent",
        patterns=[b"tencent cloud", b"tencentcloud", b"tencent"],
        category=DeviceCategory.SERVER,
        default_creds=[]
    ),
    VendorSignature(
        name="VMware",
        short_name="VMware",
        patterns=[
            b"vmware", b"esxi", b"vsphere", b"vcenter",
            b"vmware esxi", b"vmware virtual platform",
            b"vmware, inc", b"vmware platform",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": ""},
            {"protocol": "http", "username": "root", "password": "vmware"},
        ]
    ),
    VendorSignature(
        name="Microsoft",
        short_name="Windows",
        patterns=[
            b"windows", b"microsoft", b"win32", b"iis",
            b"microsoft windows", b"win2000", b"win2003",
            b"win2008", b"win2012", b"win2016", b"win2019", b"win2022",
            b"windows server", b"microsoft windows server",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "rdp", "username": "administrator", "password": ""},
            {"protocol": "winrm", "username": "administrator", "password": ""},
        ]
    ),
    VendorSignature(
        name="Synology",
        short_name="Synology",
        patterns=[
            b"synology", b"diskstation", b"synology inc",
            b"synology nas", b"synology ds", b"synology rtd",
        ],
        category=DeviceCategory.STORAGE,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": ""},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="QNAP Systems",
        short_name="QNAP",
        patterns=[
            b"qnap", b"qnap systems", b"qnap nas",
            b"qfinder", b"qnap turbo station",
        ],
        category=DeviceCategory.STORAGE,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="APC by Schneider Electric",
        short_name="APC",
        patterns=[
            b"apc", b"apc by schneider", b"schneider",
            b"apc ups", b"apcupsd", b"apc smc",
            b"apc network management card",
        ],
        category=DeviceCategory.UPS,
        default_creds=[
            {"protocol": "http", "username": "apc", "password": "apc"},
            {"protocol": "snmp", "community": "private"},
        ]
    ),
    VendorSignature(
        name="Ruijie Networks",
        short_name="Ruijie",
        patterns=[
            b"ruijie", b"ruijie networks", b"raytalk",
            b"ruijie n", b"ruijie s",
        ],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Ruijie Reyee",
        short_name="Reyee",
        patterns=[b"reyee", b"reyee os", b"ruijie reyee"],
        category=DeviceCategory.SWITCH,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="zte",
        short_name="ZTE",
        patterns=[
            b"zte", b"zte corporation", b"zxr10",
            b"zte g", b"zte s", b"zxwn",
        ],
        category=DeviceCategory.ROUTER,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Nvidia",
        short_name="Nvidia",
        patterns=[
            b"nvidia", b"nvidia forceware", b"nvidia geforce",
            b"nvidia grid", b"nvidia vgpu",
        ],
        category=DeviceCategory.OTHER,
        default_creds=[]
    ),
    VendorSignature(
        name="Intel",
        short_name="Intel",
        patterns=[
            b"intel", b"intel corporation",
            b"intel(r)", b"intel amt",
            b"intel active management technology",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Supermicro",
        short_name="Supermicro",
        patterns=[
            b"supermicro", b"supermicro ltd", b"supermicro incorporated",
            b"smci",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": "admin"},
            {"protocol": "ipmi", "username": "ADMIN", "password": "ADMIN"},
        ]
    ),
    VendorSignature(
        name="Lenovo",
        short_name="Lenovo",
        patterns=[
            b"lenovo", b"lenovo global", b"thinkpad",
            b"thinkcentre", b"lenovo cloud",
            b"lenovo system",
        ],
        category=DeviceCategory.SERVER,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Cisco Meraki",
        short_name="Meraki",
        patterns=[b"meraki", b"cisco meraki", b"meraki cloud"],
        category=DeviceCategory.WIRELESS,
        default_creds=[
            {"protocol": "http", "username": "admin", "password": ""},
        ]
    ),
    VendorSignature(
        name="Ubiquiti Networks",
        short_name="Ubiquiti",
        patterns=[
            b"ubiquiti", b"ubnt", b"airrouter", b"unifi",
            b"ubiquiti networks", b"unifi security gateway",
        ],
        category=DeviceCategory.WIRELESS,
        default_creds=[
            {"protocol": "ssh", "username": "ubnt", "password": "ubnt"},
            {"protocol": "http", "username": "ubnt", "password": "ubnt"},
        ]
    ),
    VendorSignature(
        name="Ruckus Wireless",
        short_name="Ruckus",
        patterns=[
            b"ruckus", b"ruckuswireless", b"ruckus networks",
            b"ruckus zonedirector", b"ruckus smartzone",
        ],
        category=DeviceCategory.WIRELESS,
        default_creds=[
            {"protocol": "ssh", "username": "super", "password": "sp-admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="F5 Networks",
        short_name="F5",
        patterns=[
            b"f5", b"f5 networks", b"big-ip", b"bigip",
            b"f5os", b"f5 tmos",
        ],
        category=DeviceCategory.LOAD_BALANCER,
        default_creds=[
            {"protocol": "ssh", "username": "root", "password": "default"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Citrix ADC (NetScaler)",
        short_name="Citrix",
        patterns=[
            b"citrix", b"netscaler", b"citrix systems",
            b"netscaler gateway", b"citrix adc",
        ],
        category=DeviceCategory.LOAD_BALANCER,
        default_creds=[
            {"protocol": "ssh", "username": "nsroot", "password": "nsroot"},
            {"protocol": "http", "username": "nsroot", "password": "nsroot"},
        ]
    ),
    VendorSignature(
        name="A10 Networks",
        short_name="A10",
        patterns=[
            b"a10", b"a10 networks", b"thunder",
            b"a10 thunder",
        ],
        category=DeviceCategory.LOAD_BALANCER,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Sangfor Technologies",
        short_name="Sangfor",
        patterns=[
            b"sangfor", b"sangfor technologies", b"ac",
            b"sangfor af", b"sangfor ad", b"sangfor m",
            b"sangfor cloud", b"sangfor ssl vpn",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "Sangfor@123"},
            {"protocol": "http", "username": "admin", "password": "Sangfor@123"},
        ]
    ),
    VendorSignature(
        name="NSFOCUS",
        short_name="NSFOCUS",
        patterns=[
            b"nsfocus", b"nsfocus technology", b"",
            b"nsfocus ", b"nsfocus ids",
        ],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "admin"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Topsec",
        short_name="Topsec",
        patterns=[b"topsec", b"", b"topsec firewall", b"topgate"],
        category=DeviceCategory.FIREWALL,
        default_creds=[
            {"protocol": "ssh", "username": "admin", "password": "topsec"},
            {"protocol": "http", "username": "admin", "password": "admin"},
        ]
    ),
    VendorSignature(
        name="Baidu Cloud",
        short_name="Baidu",
        patterns=[b"baidu", b"baidu cloud", b"baiduyun", b"baidu bce"],
        category=DeviceCategory.SERVER,
        default_creds=[]
    ),
    VendorSignature(
        name="Kingsoft Cloud",
        short_name="Kingsoft",
        patterns=[b"kingsoft", b"ksyun", b"kingsoft cloud", b""],
        category=DeviceCategory.SERVER,
        default_creds=[]
    ),
    VendorSignature(
        name="QingCloud",
        short_name="QingCloud",
        patterns=[b"qingcloud", b"qingcloud computing", b"", b"qingcloud qing"],
        category=DeviceCategory.SERVER,
        default_creds=[]
    ),
]


# 
MODEL_PATTERNS: List[Tuple[bytes, str, str]] = [
    # Cisco
    (b"cisco ios-xe", "cisco", "IOS-XE"),
    (b"cisco nexus", "cisco", "Nexus"),
    (b"cisco catalyst", "cisco", "Catalyst"),
    (b"cisco 2960", "cisco", "Catalyst 2960"),
    (b"cisco 3750", "cisco", "Catalyst 3750"),
    (b"cisco 9300", "cisco", "Catalyst 9300"),
    (b"cisco 9500", "cisco", "Catalyst 9500"),
    (b"cisco ISR", "cisco", "ISR"),
    (b"cisco ASR", "cisco", "ASR"),
    (b"cisco ASA", "cisco", "ASA"),
    (b"cisco Meraki", "cisco", "Meraki"),
    # Huawei
    (b"huawei s5720", "huawei", "S5720"),
    (b"huawei s5700", "huawei", "S5700"),
    (b"huawei s9700", "huawei", "S9700"),
    (b"huawei s12700", "huawei", "S12700"),
    (b"huawei ar", "huawei", "AR Router"),
    (b"huawei ne", "huawei", "NE Router"),
    (b"huawei", "huawei", "USG Firewall"),
    # H3C
    (b"h3c s5120", "h3c", "S5120"),
    (b"h3c s5500", "h3c", "S5500"),
    (b"h3c s5800", "h3c", "S5800"),
    # Juniper
    (b"junos", "juniper", "JUNOS"),
    (b"juniper ex", "juniper", "EX Switch"),
    (b"juniper mx", "juniper", "MX Router"),
    (b"juniper srx", "juniper", "SRX Firewall"),
    # VMware
    (b"vmware esxi 6", "vmware", "ESXi 6.x"),
    (b"vmware esxi 7", "vmware", "ESXi 7.x"),
    (b"vmware esxi 8", "vmware", "ESXi 8.x"),
    # Linux
    (b"ubuntu 24.04", "ubuntu", "Ubuntu 24.04 LTS"),
    (b"ubuntu 22.04", "ubuntu", "Ubuntu 22.04 LTS"),
    (b"ubuntu 20.04", "ubuntu", "Ubuntu 20.04 LTS"),
    (b"centos 7", "centos", "CentOS 7"),
    (b"centos 8", "centos", "CentOS 8"),
    (b"centos stream", "centos", "CentOS Stream"),
    # Windows
    (b"windows server 2022", "windows", "Windows Server 2022"),
    (b"windows server 2019", "windows", "Windows Server 2019"),
    (b"windows server 2016", "windows", "Windows Server 2016"),
    (b"windows server 2012", "windows", "Windows Server 2012"),
    (b"windows 10", "windows", "Windows 10"),
    (b"windows 11", "windows", "Windows 11"),
    # NAS
    (b"synology ds", "synology", "DiskStation"),
    (b"synology rs", "synology", "RackStation"),
    (b"qnap ts", "qnap", "QNAP NAS"),
    # Camera
    (b"DS-2CD", "hikvision", "IPC"),
    (b"DS-7100", "hikvision", "NVR"),
    (b"DH-IPC", "dahua", "IPC"),
    # UPS
    (b"apc smart-ups", "apc", "Smart-UPS"),
    (b"apc back-ups", "apc", "Back-UPS"),
]


# =============================================================================
# SNMP OID 
# =============================================================================

SNMP_SYS_OBJECT_ID_PATTERNS: Dict[str, Dict] = {
    # Cisco
    "1.3.6.1.4.1.9.1": {"vendor": "cisco", "type": "router"},
    "1.3.6.1.4.1.9.1.1": {"vendor": "cisco", "type": "switch"},
    "1.3.6.1.4.1.9.6.1": {"vendor": "cisco", "type": "router"},
    # Huawei
    "1.3.6.1.4.1.2011": {"vendor": "huawei", "type": "network"},
    "1.3.6.1.4.1.25506": {"vendor": "huawei", "type": "switch"},
    # H3C
    "1.3.6.1.4.1.25506": {"vendor": "h3c", "type": "switch"},
    # Juniper
    "1.3.6.1.4.1.2636": {"vendor": "juniper", "type": "network"},
    # HP/Aruba
    "1.3.6.1.4.1.11.2": {"vendor": "hp", "type": "switch"},
    "1.3.6.1.4.1.11.27": {"vendor": "aruba", "type": "wireless"},
    # Dell
    "1.3.6.1.4.1.674.10895": {"vendor": "dell", "type": "switch"},
    # VMware
    "1.3.6.1.4.1.6876": {"vendor": "vmware", "type": "server"},
    # APC
    "1.3.6.1.4.1.318": {"vendor": "apc", "type": "ups"},
    # Synology
    "1.3.6.1.4.1.6574": {"vendor": "synology", "type": "storage"},
    # QNAP
    "1.3.6.1.4.1.24681": {"vendor": "qnap", "type": "storage"},
    # Hikvision
    "1.3.6.1.4.1.39165": {"vendor": "hikvision", "type": "camera"},
    # Ubiquiti
    "1.3.6.1.4.1.41112": {"vendor": "ubiquiti", "type": "wireless"},
}


# =============================================================================
# 
# =============================================================================

PORT_SIGNATURES: Dict[int, List[Dict]] = {
    22: [
        {"pattern": b"SSH-2.0-", "vendor_hint": "linux"},
        {"pattern": b"SSH-1.99-", "vendor_hint": "linux"},
        {"pattern": b"SSH-2.0-OpenSSH", "vendor_hint": "openssh"},
        {"pattern": b"OpenSSH", "vendor_hint": "openssh"},
        {"pattern": b"SSH-", "vendor_hint": "unix"},
        {"pattern": b"mobaxterm", "vendor_hint": "windows"},
    ],
    80: [
        {"pattern": b"Apache", "vendor_hint": "apache"},
        {"pattern": b"nginx", "vendor_hint": "nginx"},
        {"pattern": b"IIS", "vendor_hint": "iis"},
        {"pattern": b"Microsoft-HTTPAPI", "vendor_hint": "iis"},
        {"pattern": b"HTTP/1.1 401", "vendor_hint": "auth_required"},
        {"pattern": b"Basic realm=", "vendor_hint": "auth_basic"},
    ],
    443: [
        {"pattern": b"Apache", "vendor_hint": "apache"},
        {"pattern": b"nginx", "vendor_hint": "nginx"},
        {"pattern": b"IIS", "vendor_hint": "iis"},
    ],
    161: [
        {"pattern": b"snmp", "vendor_hint": "snmp_device"},
    ],
    8080: [
        {"pattern": b"Apache", "vendor_hint": "apache"},
        {"pattern": b"nginx", "vendor_hint": "nginx"},
        {"pattern": b"JBoss", "vendor_hint": "jboss"},
        {"pattern": b"Tomcat", "vendor_hint": "tomcat"},
        {"pattern": b"Apache CXF", "vendor_hint": "cxf"},
    ],
    4433: [
        {"pattern": b"Raiden", "vendor_hint": "raiden"},
    ],
    3389: [
        {"pattern": b"", "vendor_hint": "rdp"},
    ],
    5900: [
        {"pattern": b"RFB", "vendor_hint": "vnc"},
        {"pattern": b"", "vendor_hint": "vnc"},
    ],
    10000: [
        {"pattern": b"webmin", "vendor_hint": "webmin"},
    ],
    2375: [
        {"pattern": b"Docker", "vendor_hint": "docker"},
    ],
    2376: [
        {"pattern": b"Docker", "vendor_hint": "docker_tls"},
    ],
    6443: [
        {"pattern": b"Kubernetes", "vendor_hint": "kubernetes"},
    ],
    8443: [
        {"pattern": b"Apache", "vendor_hint": "apache_ssl"},
        {"pattern": b"nginx", "vendor_hint": "nginx_ssl"},
    ],
}


# =============================================================================
# MAC OUI 
# =============================================================================

MAC_OUI_DATABASE: Dict[str, str] = {
    "00:00:0c": "cisco",
    "00:1a:2b": "cisco",
    "00:50:56": "vmware",
    "00:0c:29": "vmware",
    "00:50:c2": "vmware",
    "08:00:27": "virtualbox",
    "0a:00:27": "virtualbox",
    "00:15:5d": "hyperv",
    "00:03:93": "huawei",
    "00:1e:10": "huawei",
    "00:25:9e": "huawei",
    "f4:8e:38": "huawei",
    "34:00:a3": "huawei",
    "00:1f:3b": "intel",
    "00:15:17": "intel",
    "3c:d9:2b": "hp",
    "00:21:5a": "hp",
    "00:22:64": "hp",
    "d4:c9:ef": "hp",
    "94:57:a5": "hp",
    "00:23:ae": "dell",
    "b8:ac:6f": "dell",
    "00:14:22": "dell",
    "ec:f4:bb": "dell",
    "b0:83:fe": "dell",
    "a4:1f:72": "dell",
    "44:a8:42": "dell",
    "00:1c:23": "dell",
    "00:25:64": "dell",
    "14:fe:b5": "dell",
    "18:66:da": "dell",
    "20:67:7c": "dell",
    "00:1e:67": "dell",
    "a0:36:9f": "dell",
    "00:0d:56": "dell",
    "00:14:6d": "dell",
    "f0:1f:af": "dell",
    "00:23:ae": "dell",
    "00:1a:a0": "dell",
    "78:2b:cb": "dell",
    "14:18:77": "dell",
    "00:1b:21": "dell",
    "00:22:19": "dell",
    "ac:1e:1a": "tp-link",
    "b0:4e:26": "tp-link",
    "c4:6e:1f": "tp-link",
    "d4:6e:0e": "tp-link",
    "e8:94:f6": "tp-link",
    "50:fa:84": "tp-link",
    "ac:84:c6": "tp-link",
    "f4:ec:38": "tp-link",
    "14:cc:20": "tp-link",
    "64:66:b3": "tp-link",
    "d8:07:b6": "tp-link",
    "b0:be:76": "tp-link",
    "88:c3:97": "tp-link",
    "a8:15:4d": "tp-link",
    "c0:25:e9": "tp-link",
    "f0:f3:36": "tp-link",
    "00:27:19": "tp-link",
    "30:b5:c2": "tp-link",
    "50:c7:bf": "tp-link",
    "e8:de:27": "tp-link",
    "20:dc:e6": "tp-link",
    "bc:46:06": "tp-link",
    "d4:6e:0e": "tp-link",
    "14:91:82": "tp-link",
    "f4:f2:6d": "tp-link",
    "34:e8:94": "tp-link",
    "d8:0d:17": "tp-link",
    "a0:f3:c1": "tp-link",
    "b0:95:8e": "tp-link",
    "ec:08:6b": "tp-link",
    "e8:94:f6": "tp-link",
    "c8:3a:35": "tenda",
    "c8:3a:6b": "tenda",
    "d4:83:04": "tenda",
    "14eb": "tenda",
    "78:44:76": "netgear",
    "9c:d3:6d": "netgear",
    "10:0c:6b": "netgear",
    "08:bd:43": "netgear",
    "00:14:6c": "netgear",
    "08:36:c9": "netgear",
    "9c:21:6a": "netgear",
    "30:46:9a": "netgear",
    "00:1b:2f": "netgear",
    "08:02:8e": "netgear",
    "00:1e:2a": "netgear",
    "00:1f:33": "netgear",
    "00:22:3f": "netgear",
    "ac:a4:30": "netgear",
    "b0:7f:b9": "netgear",
    "00:22:3f": "netgear",
    "c4:04:15": "netgear",
    "00:1f:33": "netgear",
    "d8:31:34": "hikvision",
    "f8:3d:ff": "hikvision",
    "64:80:99": "hikvision",
    "98:02:9f": "hikvision",
    "e8:a1:8a": "hikvision",
    "80:c2:89": "hikvision",
    "a0:6d:6f": "hikvision",
    "80:fa:84": "hikvision",
    "44:47:9d": "hikvision",
    "c0:56:e3": "hikvision",
    "e8:5b:5b": "hikvision",
    "8c:8c:aa": "hikvision",
    "c8:34:a1": "hikvision",
    "44:e2:44": "hikvision",
    "98:35:47": "hikvision",
    "c4:a8:1d": "hikvision",
    "84:a8:e3": "hikvision",
    "f4:4d:55": "hikvision",
    "24:29:2f": "hikvision",
    "a4:2b:ba": "hikvision",
    "64:09:80": "hikvision",
    "ac:1e:e2": "hikvision",
    "14:dd:a9": "hikvision",
    "00:a0:ed": "hikvision",
    "18:40:27": "hikvision",
    "f8:27:93": "hikvision",
    "3c:8c:f8": "hikvision",
    "88:a2:d7": "hikvision",
    "30:a2:43": "hikvision",
    "58:88:1b": "hikvision",
    "14:fe:b5": "hikvision",
    "e4:68:a3": "hikvision",
    "34:8e:81": "hikvision",
    "84:46:fe": "hikvision",
    "b0:e2:35": "hikvision",
    "80:c2:89": "hikvision",
    "bc:9f:ef": "hikvision",
    "c8:00:1e": "hikvision",
    "20:14:10": "hikvision",
    "c8:34:a1": "hikvision",
    "50:bd:5f": "hikvision",
    "e8:5c:8c": "hikvision",
    "e4:68:a3": "hikvision",
    "18:c5:8a": "hikvision",
    "00:a0:ed": "hikvision",
    "14:dd:a9": "hikvision",
    "78:a2:a0": "hikvision",
    "a4:2b:8c": "hikvision",
    "64:09:80": "hikvision",
    "bc:9f:ef": "hikvision",
    "f8:27:93": "hikvision",
    "f4:4d:55": "hikvision",
    "98:35:47": "hikvision",
    "34:e8:94": "hikvision",
    "c8:34:a1": "hikvision",
    "e8:5c:8c": "hikvision",
    "50:bd:5f": "hikvision",
    "54:4a:ea": "hikvision",
    "64:80:99": "hikvision",
    "44:47:9d": "hikvision",
    "20:14:10": "hikvision",
    "18:40:27": "hikvision",
    "14:fe:b5": "hikvision",
    "44:e2:44": "hikvision",
    "98:02:9f": "hikvision",
    "30:a2:43": "hikvision",
    "14:cc:20": "tp-link",
    "88:c3:97": "tp-link",
    "b0:be:76": "tp-link",
    "a8:15:4d": "tp-link",
    "d4:6e:0e": "tp-link",
    "e8:de:27": "tp-link",
    "00:27:19": "tp-link",
    "30:b5:c2": "tp-link",
    "f4:ec:38": "tp-link",
    "50:fa:84": "tp-link",
    "ac:84:c6": "tp-link",
    "c4:6e:1f": "tp-link",
    "14:91:82": "tp-link",
    "f0:f3:36": "tp-link",
    "c0:25:e9": "tp-link",
    "00:1b:2f": "netgear",
    "08:02:8e": "netgear",
    "00:1e:2a": "netgear",
    "00:1f:33": "netgear",
    "00:22:3f": "netgear",
    "ac:a4:30": "netgear",
    "b0:7f:b9": "netgear",
    "c4:04:15": "netgear",
    "30:46:9a": "netgear",
    "9c:21:6a": "netgear",
    "08:36:c9": "netgear",
    "00:14:6c": "netgear",
    "08:bd:43": "netgear",
    "9c:d3:6d": "netgear",
    "78:44:76": "netgear",
    "10:0c:6b": "netgear",
    "00:0d:3a": "microsoft",
    "00:12:5a": "microsoft",
    "00:15:5d": "microsoft",
    "00:17:fa": "microsoft",
    "00:1d:d8": "microsoft",
    "00:22:48": "microsoft",
    "00:25:ae": "microsoft",
    "00:03:ff": "microsoft",
    "00:0d:3a": "microsoft",
    "00:12:5a": "microsoft",
    "00:15:5d": "microsoft",
    "00:17:fa": "microsoft",
    "00:1d:d8": "microsoft",
    "00:22:48": "microsoft",
    "00:25:ae": "microsoft",
    "28:18:78": "microsoft",
    "00:50:56": "vmware",
    "00:0c:29": "vmware",
    "00:05:69": "vmware",
    "00:1c:14": "vmware",
    "00:0a:95": "vmware",
    "00:50:c2": "vmware",
    "08:00:27": "virtualbox",
    "0a:00:27": "virtualbox",
    "52:54:00": "qemu",
    "00:16:3e": "xen",
    "00:18:92": "xen",
    "00:1c:42": "parallels",
    "00:03:93": "huawei",
    "00:1e:10": "huawei",
    "00:25:9e": "huawei",
    "f4:8e:38": "huawei",
    "34:00:a3": "huawei",
    "00:25:9e": "huawei",
    "00:1e:10": "huawei",
    "f4:8e:38": "huawei",
    "34:00:a3": "huawei",
    "00:1e:67": "zte",
    "00:1f:a4": "zte",
    "48:f0:7f": "zte",
    "5c:63:bf": "zte",
    "5c:83:bf": "zte",
    "00:1e:67": "zte",
    "48:f0:7f": "zte",
    "00:1f:a4": "zte",
    "5c:63:bf": "zte",
    "5c:83:bf": "zte",
    "00:24:1d": "ruijie",
    "00:25:5d": "ruijie",
    "00:3a:9a": "ruijie",
    "0c:d2:92": "ruijie",
    "10:c3:7b": "ruijie",
    "14:db:e5": "ruijie",
    "18:a9:9b": "ruijie",
    "1c:1d:67": "ruijie",
    "20:f3:a3": "ruijie",
    "24:77:03": "ruijie",
    "2c:56:dc": "ruijie",
    "30:b4:9e": "ruijie",
    "34:ef:8b": "ruijie",
    "38:21:a7": "ruijie",
    "3c:57:8e": "ruijie",
    "40:66:72": "ruijie",
    "44:83:12": "ruijie",
    "4c:32:75": "ruijie",
    "50:7b:9d": "ruijie",
    "54:25:ea": "ruijie",
    "58:66:ba": "ruijie",
    "5c:5f:c1": "ruijie",
    "60:e3:27": "ruijie",
    "64:77:91": "ruijie",
    "68:ff:7b": "ruijie",
    "6c:76:8f": "ruijie",
    "70:85:c2": "ruijie",
    "74:02:8c": "ruijie",
    "78:44:76": "ruijie",
    "7c:8b:ca": "ruijie",
    "80:89:17": "ruijie",
    "84:8e:0c": "ruijie",
    "88:e3:ab": "ruijie",
    "8c:89:93": "ruijie",
    "90:17:ac": "ruijie",
    "94:75:6e": "ruijie",
    "98:6c:4f": "ruijie",
    "9c:5c:8e": "ruijie",
    "a0:98:05": "ruijie",
    "a4:42:a3": "ruijie",
    "a8:74:86": "ruijie",
    "ac:4e:91": "ruijie",
    "b0:5a:da": "ruijie",
    "b4:8b:19": "ruijie",
    "b8:6f:8d": "ruijie",
    "bc:62:0e": "ruijie",
    "c0:97:27": "ruijie",
    "c4:6e:1f": "tp-link",
    "cc:32:e5": "ruijie",
    "d0:59:e4": "ruijie",
    "d4:61:9d": "ruijie",
    "d8:47:32": "ruijie",
    "dc:fe:07": "ruijie",
    "e0:5f:45": "ruijie",
    "e4:68:a3": "hikvision",
    "f4:4d:55": "hikvision",
    "fc:74:5a": "ruijie",
    "00:18:82": "hikvision",
    "a4:2b:8c": "hikvision",
    "a8:c8:3a": "dahua",
    "b8:5a:73": "dahua",
    "c4:3a:84": "dahua",
    "c8:2a:1e": "dahua",
    "d4:09:c8": "dahua",
    "e8:5d:e4": "dahua",
    "f0:2f:74": "dahua",
    "f8:7b:8c": "dahua",
    "fc:5b:24": "dahua",
    "00:1f:29": "ubiquiti",
    "04:18:d6": "ubiquiti",
    "18:e8:29": "ubiquiti",
    "24:a4:3c": "ubiquiti",
    "34:e8:94": "tp-link",
    "44:94:fc": "ubiquiti",
    "48:8a:d2": "ubiquiti",
    "4c:5e:0c": "ubiquiti",
    "60:32:b1": "ubiquiti",
    "74:83:c2": "ubiquiti",
    "80:2a:a8": "ubiquiti",
    "ac:8b:a9": "ubiquiti",
    "b4:fb:e4": "ubiquiti",
    "d4:ca:6d": "ubiquiti",
    "dc:9f:db": "ubiquiti",
    "e4:8b:7f": "ubiquiti",
    "f0:9f:c2": "ubiquiti",
    "f4:e2:97": "ubiquiti",
    "fc:ec:da": "ubiquiti",
    "24:a4:3c": "ubiquiti",
    "04:18:d6": "ubiquiti",
    "18:e8:29": "ubiquiti",
    "34:e8:94": "tp-link",
    "44:94:fc": "ubiquiti",
    "48:8a:d2": "ubiquiti",
    "4c:5e:0c": "ubiquiti",
    "60:32:b1": "ubiquiti",
    "74:83:c2": "ubiquiti",
    "80:2a:a8": "ubiquiti",
    "ac:8b:a9": "ubiquiti",
    "b4:fb:e4": "ubiquiti",
    "d4:ca:6d": "ubiquiti",
    "dc:9f:db": "ubiquiti",
    "e4:8b:7f": "ubiquiti",
    "f0:9f:c2": "ubiquiti",
    "f4:e2:97": "ubiquiti",
    "fc:ec:da": "ubiquiti",
}


# =============================================================================
# 
# =============================================================================

class DeviceFingerprinter:
    """
    
    
    ：
    1. Banner （SSH、HTTP、Telnet ）
    2. SNMP sysObjectID
    3. MAC OUI（）
    4. 
    5. TTL 
    """

    def __init__(self):
        self.vendor_sigs = VENDOR_SIGNATURES
        self.model_patterns = MODEL_PATTERNS
        self.snmp_oid_map = SNMP_SYS_OBJECT_ID_PATTERNS
        self.port_sigs = PORT_SIGNATURES
        self.mac_oui = MAC_OUI_DATABASE

    def identify(
        self,
        banners: Dict[str, str] = None,
        ports: List[int] = None,
        mac: str = None,
        snmp_sys_object_id: str = None,
        snmp_sys_descr: str = None,
        ttl: int = None,
        hostname: str = None,
    ) -> Dict[str, Any]:
        """
        
        
        Args:
            banners: banner，key，valuebanner
            ports: 
            mac: MAC
            snmp_sys_object_id: SNMP sysObjectID（ .1.3.6.1.4.1.9.1.1）
            snmp_sys_descr: SNMP sysDescr 
            ttl: TTL
            hostname: 
            
        Returns:
             vendor、model、category、confidence、matched_by 
        """
        banners = banners or {}
        ports = ports or []
        
        result = {
            "vendor": None,
            "model": None,
            "category": DeviceCategory.OTHER,
            "confidence": 0.0,        # 0.0 ~ 1.0
            "matched_by": [],          # 
            "suggested_protocols": [],  # 
            "possible_creds": [],       # 
            "raw_hints": {},           # 
        }
        
        matched_vendor = None
        matched_vendor_sig = None
        
        # ---- 1. ：SNMP sysObjectID（）----
        if snmp_sys_object_id:
            oid_result = self._match_snmp_oid(snmp_sys_object_id)
            if oid_result:
                result["vendor"] = oid_result["vendor"]
                result["category"] = self._str_to_category(oid_result["type"])
                result["confidence"] = 0.95
                result["matched_by"].append(f"snmp_oid:{snmp_sys_object_id}")
                result["suggested_protocols"] = ["snmp"]
                result["raw_hints"]["snmp_oid"] = snmp_sys_object_id
                matched_vendor = oid_result["vendor"]
        
        # ---- 2. Banner （）----
        combined_banner = self._combine_banners(banners)
        if combined_banner:
            banner_result = self._match_banner(combined_banner)
            if banner_result:
                # BannerSNMP OID
                result["vendor"] = banner_result["vendor"]
                result["model"] = banner_result.get("model")
                result["category"] = banner_result["category"]
                result["matched_by"].append(f"banner:{banner_result['matched_pattern']}")
                result["raw_hints"]["banner"] = combined_banner[:200]
                
                if snmp_sys_object_id:
                    result["confidence"] = 0.98  # 
                else:
                    result["confidence"] = max(result["confidence"], 0.85)
                
                matched_vendor = banner_result["vendor"]
                
                # banner
                result["suggested_protocols"] = self._suggest_protocols(banners, ports)
        
        # ---- 3. MAC OUI（）----
        if mac:
            oui_result = self._match_mac_oui(mac)
            if oui_result:
                result["raw_hints"]["mac_oui"] = oui_result
                
                # MAC OUI，
                if not result["vendor"]:
                    result["vendor"] = oui_result
                    result["confidence"] = max(result["confidence"], 0.5)
                    result["matched_by"].append(f"mac_oui:{oui_result}")
        
        # ---- 4.  ----
        if ports and not result["vendor"]:
            port_result = self._match_ports(ports, banners)
            if port_result:
                result["vendor"] = port_result["vendor"]
                result["category"] = port_result["category"]
                result["confidence"] = max(result["confidence"], 0.6)
                result["matched_by"].append(f"ports:{port_result['matched_ports']}")
                result["suggested_protocols"] = port_result["protocols"]
        
        # ---- 5. TTL  ----
        if ttl and not result["vendor"]:
            category_hint = self._ttl_to_category(ttl)
            if category_hint:
                result["category"] = category_hint
                result["matched_by"].append(f"ttl:{ttl}")
        
        # ---- 6.  vendor  ----
        if result["vendor"]:
            creds = self._get_vendor_creds(result["vendor"])
            result["possible_creds"] = creds
        
        # ---- 7. ， ----
        if not result["vendor"]:
            result["vendor"], result["category"] = self._generic_identify(banners, ports, ttl)
            if result["vendor"]:
                result["confidence"] = 0.4
                result["matched_by"].append("generic_match")
        
        return result

    def _combine_banners(self, banners: Dict[str, str]) -> bytes:
        """合并多个端口的 banner 为单个字节串"""
        parts = []
        for port, banner in sorted(banners.items()):
            if banner:
                # 统一转为 bytes 再拼接，避免字符串转义破坏二进制特征
                if isinstance(banner, bytes):
                    banner_bytes = banner
                elif isinstance(banner, str):
                    # 字符串中已包含实际字节（如 \x00 是真实空字节），直接 utf-8 编码保留
                    banner_bytes = banner.encode('utf-8', errors='replace')
                else:
                    banner_bytes = str(banner).encode('utf-8', errors='ignore')
                parts.append(f"[{port}]".encode('utf-8') + banner_bytes)
        combined = b" ".join(parts)
        return combined.lower()

    def _match_banner(self, combined_banner: bytes) -> Optional[Dict]:
        """banner"""
        # （）
        for pattern, vendor, model in self.model_patterns:
            if pattern.lower() in combined_banner:
                # signaturecategory
                vendor_sig = self._get_vendor_sig(vendor)
                return {
                    "vendor": vendor,
                    "model": model,
                    "category": vendor_sig.category if vendor_sig else DeviceCategory.OTHER,
                    "matched_pattern": pattern.decode('utf-8', errors='ignore'),
                }
        
        # 按匹配长度降序排序，越长越精确
        vendor_candidates = []
        for sig in self.vendor_sigs:
            for pattern in sig.patterns:
                if not pattern:  # 跳过空模式
                    continue
                if pattern.lower() in combined_banner:
                    vendor_candidates.append((len(pattern), sig, pattern))
        
        if vendor_candidates:
            # 选择最长匹配
            _, best_sig, best_pattern = max(vendor_candidates, key=lambda x: x[0])
            return {
                "vendor": best_sig.short_name,
                "model": None,
                "category": best_sig.category,
                "matched_pattern": best_pattern.decode('utf-8', errors='ignore'),
            }
        
        return None

    def _match_snmp_oid(self, sys_object_id: str) -> Optional[Dict]:
        """SNMP sysObjectID"""
        # OID（）
        oid = sys_object_id.lstrip('.')
        
        # 
        for oid_prefix, info in sorted(self.snmp_oid_map.items(), key=lambda x: -len(x[0])):
            if oid.startswith(oid_prefix.lstrip('.')):
                return info
        
        return None

    def _match_mac_oui(self, mac: str) -> Optional[str]:
        """MACOUI"""
        if not mac:
            return None
        
        # MAC
        mac_clean = mac.upper().replace(':', '').replace('-', '').replace('.', '')
        if len(mac_clean) < 6:
            return None
        
        oui = mac_clean[:6]
        
        #  XX:XX:XX
        oui_formatted = f"{oui[0:2]}:{oui[2:4]}:{oui[4:6]}".upper()
        
        return self.mac_oui.get(oui_formatted)

    def _match_ports(self, ports: List[int], banners: Dict[str, str]) -> Optional[Dict]:
        """"""
        port_set = set(ports)
        
        # 
        if 161 in port_set or 162 in port_set:
            return {"vendor": "snmp_device", "category": DeviceCategory.OTHER, "matched_ports": "161/162", "protocols": ["snmp"]}
        
        if 22 in port_set and 80 in port_set:
            return {"vendor": "linux", "category": DeviceCategory.SERVER, "matched_ports": "22+80", "protocols": ["ssh", "http"]}
        
        if 22 in port_set and 443 in port_set:
            return {"vendor": "linux", "category": DeviceCategory.SERVER, "matched_ports": "22+443", "protocols": ["ssh", "https"]}
        
        if 3389 in port_set:
            return {"vendor": "windows", "category": DeviceCategory.SERVER, "matched_ports": "3389", "protocols": ["rdp", "winrm"]}
        
        if 445 in port_set:
            return {"vendor": "windows", "category": DeviceCategory.SERVER, "matched_ports": "445", "protocols": ["smb", "wmi"]}
        
        if 5900 in port_set:
            return {"vendor": "vnc", "category": DeviceCategory.OTHER, "matched_ports": "5900", "protocols": ["vnc"]}
        
        if 2375 in port_set or 2376 in port_set:
            return {"vendor": "docker", "category": DeviceCategory.OTHER, "matched_ports": "2375/2376", "protocols": ["docker"]}
        
        if 6443 in port_set or 10250 in port_set:
            return {"vendor": "kubernetes", "category": DeviceCategory.OTHER, "matched_ports": "6443/10250", "protocols": ["kubernetes"]}
        
        if 10000 in port_set:
            return {"vendor": "webmin", "category": DeviceCategory.OTHER, "matched_ports": "10000", "protocols": ["http"]}
        
        return None

    def _suggest_protocols(self, banners: Dict[str, str], ports: List[int]) -> List[str]:
        """banner"""
        protocols = []
        port_set = set(ports)
        
        if 161 in port_set or 162 in port_set:
            protocols.append("snmp")
        
        if 22 in port_set:
            protocols.append("ssh")
        
        if 3389 in port_set:
            protocols.append("rdp")
            protocols.append("winrm")
        
        if 80 in port_set or 443 in port_set:
            protocols.append("http")
        
        if 443 in port_set:
            protocols.append("https")
        
        if 445 in port_set:
            protocols.append("smb")
        
        if 623 in port_set:
            protocols.append("ipmi")
        
        return protocols

    def _ttl_to_category(self, ttl: int) -> DeviceCategory:
        """根据 TTL 推断设备类型（不精确，仅作辅助）"""
        # DeviceCategory 没有 LINUX/SERVER 等 OS 类型，仅有设备类型
        # 这里保守返回 SERVER，因为大多数 MySQL/SSH 等服务都运行在服务器上
        if ttl <= 64:
            return DeviceCategory.SERVER  # Linux/Unix
        elif ttl <= 128:
            return DeviceCategory.SERVER  # Windows
        else:
            return DeviceCategory.OTHER

    def _str_to_category(self, cat_str: str) -> DeviceCategory:
        """DeviceCategory"""
        mapping = {
            "server": DeviceCategory.SERVER,
            "switch": DeviceCategory.SWITCH,
            "router": DeviceCategory.ROUTER,
            "firewall": DeviceCategory.FIREWALL,
            "wireless": DeviceCategory.WIRELESS,
            "storage": DeviceCategory.STORAGE,
            "printer": DeviceCategory.PRINTER,
            "camera": DeviceCategory.CAMERA,
            "loadbalancer": DeviceCategory.LOAD_BALANCER,
            "ids_ips": DeviceCategory.IDS_IPS,
            "ups": DeviceCategory.UPS,
            "network": DeviceCategory.OTHER,
            "other": DeviceCategory.OTHER,
        }
        return mapping.get(cat_str.lower(), DeviceCategory.OTHER)

    def _get_vendor_sig(self, vendor_name: str) -> Optional[VendorSignature]:
        """"""
        vendor_lower = vendor_name.lower()
        for sig in self.vendor_sigs:
            if sig.short_name.lower() == vendor_lower or sig.name.lower() == vendor_lower:
                return sig
        return None

    def _get_vendor_creds(self, vendor_name: str) -> List[Dict]:
        """"""
        sig = self._get_vendor_sig(vendor_name)
        if sig:
            return sig.default_creds
        return []

    def _generic_identify(
        self, banners: Dict[str, str], ports: List[int], ttl: int
    ) -> Tuple[Optional[str], DeviceCategory]:
        """：TTL"""
        port_set = set(ports)
        
        # 
        network_ports = {22, 23, 80, 443, 161}
        if network_ports & port_set and not {3306, 5432, 6379} & port_set:
            return ("unknown_network", DeviceCategory.OTHER)
        
        # 
        server_ports = {22, 22, 3306, 5432, 6379, 8080}
        if server_ports & port_set:
            return ("unknown_server", DeviceCategory.SERVER)
        
        if ttl:
            if ttl <= 64:
                return ("unknown_linux", DeviceCategory.SERVER)
            elif ttl <= 128:
                return ("unknown_windows", DeviceCategory.SERVER)
        
        return None, DeviceCategory.OTHER

    def get_vendor_list(self) -> List[str]:
        """"""
        return [sig.short_name for sig in self.vendor_sigs]

    def get_all_default_creds(self) -> List[Dict]:
        """（）"""
        all_creds = []
        seen = set()
        
        for sig in self.vendor_sigs:
            for cred in sig.default_creds:
                key = f"{sig.short_name}:{cred.get('protocol')}:{cred.get('username')}:{cred.get('password')}"
                if key not in seen:
                    seen.add(key)
                    cred_entry = {
                        "vendor": sig.short_name,
                        **cred
                    }
                    all_creds.append(cred_entry)
        
        return all_creds


# 
_fingerprinter: Optional[DeviceFingerprinter] = None


def get_fingerprinter() -> DeviceFingerprinter:
    """"""
    global _fingerprinter
    if _fingerprinter is None:
        _fingerprinter = DeviceFingerprinter()
    return _fingerprinter
