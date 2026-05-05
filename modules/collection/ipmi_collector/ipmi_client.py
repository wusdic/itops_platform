"""
IPMI客户端
支持IPMI v1.5/v2.0协议，用于采集服务器BMC管理控制器数据
"""

import logging
import socket
import struct
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IPMIVersion(str, Enum):
    """IPMI版本枚举"""
    V1_5 = 'v1.5'
    V2_0 = 'v2.0'


@dataclass
class IPMIConfig:
    """IPMI配置"""
    host: str
    port: int = 623
    username: str = 'admin'
    password: str = ''
    version: IPMIVersion = IPMIVersion.V2_0
    timeout: int = 5


class IPMIClient:
    """
    IPMI客户端
    
    用于通过IPMI协议管理服务器BMC（基板管理控制器）。
    
    支持:
    - IPMI v1.5/v2.0
    - 传感器数据采集
    - 系统事件日志
    - 电源控制
    - 用户管理
    - FRU信息读取
    
    使用示例:
    >>> client = IPMIClient(host='192.168.1.1', username='admin', password='password')
    >>> client.connect()
    >>> sensors = client.get_sensors()
    >>> print(sensors)
    >>> client.close()
    """
    
    # IPMI命令代码
    CMD_GET_DEVICE_ID = 0x01
    CMD_GET_SENSOR_COUNT = 0x01
    CMD_GET_SENSOR_LIST = 0x02
    CMD_READ_SENSOR = 0x2D
    CMD_GET_FRU_DATA = 0x11
    CMD_GET_SDR = 0x23
    
    # NetFn代码
    NETFN_APP = 0x06
    NETFN_STORAGE = 0x0A
    NETFN_SENSOR = 0x04
    
    def __init__(self, config: IPMIConfig):
        self._config = config
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._session_id: int = 0
        self._max_payload_size: int = 255
        
        # IPMI v2.0 RAKP authentication
        self._rmcp_session_id: bytes = b''
        self._bmc_ipmb: bytes = b''
    
    def connect(self) -> bool:
        """
        建立IPMI连接
        
        Returns:
            连接是否成功
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(self._config.timeout)
            self._socket.connect((self._config.host, self._config.port))
            
            if self._config.version == IPMIVersion.V2_0:
                self._connected = self._authenticate_v2()
            else:
                self._connected = self._authenticate_v1_5()
            
            if self._connected:
                logger.info(f"IPMI连接成功: {self._config.host}:{self._config.port}")
            return self._connected
            
        except Exception as e:
            logger.error(f"IPMI连接失败: {self._config.host} - {e}")
            self._connected = False
            return False
    
    def _authenticate_v1_5(self) -> bool:
        """IPMI v1.5认证"""
        # 发送Get Device ID命令测试连接
        try:
            response = self._send_raw_ipmi(
                self.NETFN_APP << 2,  # NetFn
                0x01,  # Command
                b''    # Data
            )
            return response is not None
        except:
            return False
    
    def _authenticate_v2(self) -> bool:
        """IPMI v2.0认证 (RAKP)"""
        try:
            # 发送Open Session Request
            # 这里简化处理，实际需要完整的RAKP握手
            response = self._send_raw_ipmi(
                self.NETFN_APP << 2,
                0x38,  # Get Channel Authentication Capabilities
                bytes([0x0E, 0x00, 0x00])  # channel=14(all), priv=0
            )
            return response is not None
        except:
            return False
    
    def _send_raw_ipmi(self, netfn: int, command: int, data: bytes = b'') -> Optional[bytes]:
        """
        发送原始IPMI命令
        
        Args:
            netfn: NetFn功能码
            command: 命令码
            data: 命令数据
            
        Returns:
            响应数据
        """
        if not self._socket:
            return None
        
        try:
            # 构建IPMI消息头
            header = bytes([
                0x20 if self._config.version == IPMIVersion.V2_0 else 0x18,  # RMCP version
                0x00,  # Reserved
                0x00, 0x00,  # Message length (填充)
            ])
            
            if self._config.version == IPMIVersion.V2_0:
                header += bytes([0x07, 0x00, 0x00, 0x00])  # Session header
            
            # 构建IPMI消息
            # [ slave_addr | seq | netfn | cmd | data ]
            message = bytes([0x20, 0x18, netfn, command]) + data
            
            # 计算校验和
            if len(message) >= 4:
                checksum1 = self._calculate_checksum(message[:2], message[2:4])
                checksum2 = self._calculate_checksum(message[4:], 0)
                message += bytes([checksum1, checksum2])
            
            # 完整的IPMI包
            packet = header + message
            packet = packet[:4] + bytes([len(packet) - 5]) + packet[5:]
            
            self._socket.send(packet)
            
            # 接收响应
            response = self._socket.recv(1024)
            
            if response and len(response) > 5:
                return response[5:]
            
            return None
            
        except socket.timeout:
            logger.debug(f"IPMI请求超时: {self._config.host}")
            return None
        except Exception as e:
            logger.debug(f"IPMI请求失败: {e}")
            return None
    
    def _calculate_checksum(self, data: bytes, extra: int = 0) -> int:
        """计算IPMI校验和"""
        total = extra + sum(data)
        return (256 - (total % 256)) % 256
    
    def get_device_id(self) -> Optional[Dict[str, Any]]:
        """
        获取设备ID信息
        
        Returns:
            设备信息字典
        """
        response = self._send_raw_ipmi(
            self.NETFN_APP << 2,
            0x01,  # Get Device ID
            b''
        )
        
        if not response or len(response) < 10:
            return None
        
        return {
            'device_id': response[0],
            'device_revision': response[1] & 0x1F,
            'firmware_revision': (response[2] << 8) | response[3],
            'ipmi_version': f"{response[4] >> 4}.{response[4] & 0x0F}",
            'device_type': response[5],
            'manufacturer_id': (response[8] << 16) | (response[7] << 8) | response[6],
            'product_id': (response[10] << 8) | response[9],
        }
    
    def get_sensor_list(self) -> List[Dict[str, Any]]:
        """
        获取传感器列表
        
        Returns:
            传感器列表
        """
        sensors = []
        
        # 尝试使用Get Sensor List命令
        response = self._send_raw_ipmi(
            self.NETFN_SENSOR << 2,
            0x02,
            b''
        )
        
        if response and len(response) > 1:
            sensor_count = response[0]
            for i in range(min(sensor_count, 64)):
                sensor_id = response[i + 1] if i + 1 < len(response) else i
                sensors.append({
                    'sensor_id': sensor_id,
                    'name': f"Sensor-{sensor_id}",
                })
        
        return sensors
    
    def read_sensor(self, sensor_number: int) -> Optional[Dict[str, Any]]:
        """
        读取传感器数据
        
        Args:
            sensor_number: 传感器编号
            
        Returns:
            传感器数据
        """
        response = self._send_raw_ipmi(
            self.NETFN_SENSOR << 2,
            0x2D,
            bytes([sensor_number])
        )
        
        if not response or len(response) < 5:
            return None
        
        return {
            'sensor_number': sensor_number,
            'value': response[0],
            'flags': response[1],
            'threshold_status': response[2],
            'reserved': response[3],
            'sensor_specific': response[4],
        }
    
    def get_sdr_records(self) -> List[Dict[str, Any]]:
        """
        获取传感器数据记录
        
        Returns:
            SDR记录列表
        """
        records = []
        
        # 发送Get SDR Repository Info
        response = self._send_raw_ipmi(
            self.NETFN_STORAGE << 2,
            0x20,
            b''
        )
        
        if response and len(response) >= 5:
            record_count = (response[3] << 8) | response[4]
            
            # 遍历读取记录
            for i in range(min(record_count, 64)):
                record_response = self._send_raw_ipmi(
                    self.NETFN_STORAGE << 2,
                    0x23,
                    bytes([0x00, 0x00, 0x00, i & 0xFF, 0xFF])
                )
                
                if record_response and len(record_response) > 4:
                    records.append({
                        'index': i,
                        'data': record_response[4:].hex(),
                    })
        
        return records
    
    def get_fru_inventory(self, fru_id: int = 0) -> Optional[Dict[str, Any]]:
        """
        获取FRU设备信息
        
        Args:
            fru_id: FRU设备ID
            
        Returns:
            FRU信息
        """
        # 获取FRU信息
        response = self._send_raw_ipmi(
            self.NETFN_STORAGE << 2,
            0x11,
            bytes([fru_id, 0x00, 0x00])
        )
        
        if not response:
            return None
        
        return {
            'fru_id': fru_id,
            'data_length': len(response) if response else 0,
            'data': response.hex() if response else '',
        }
    
    def get_chassis_status(self) -> Optional[Dict[str, Any]]:
        """
        获取机箱状态
        
        Returns:
            机箱状态
        """
        response = self._send_raw_ipmi(
            0x00,  # NetFn Chassis
            0x01,  # Get Chassis Status
            b''
        )
        
        if not response or len(response) < 4:
            return None
        
        return {
            'current_power_state': response[0] & 0x01,
            'power_restoration': (response[0] >> 5) & 0x07,
            'power_control': response[1] & 0x07,
            'power_override': (response[1] >> 3) & 0x01,
            'power_system': (response[2] >> 0) & 0x01,
            'power_fan': (response[2] >> 1) & 0x01,
            'cooling_fault': (response[2] >> 2) & 0x01,
            'drive_fault': (response[2] >> 3) & 0x01,
            'front_panel_lockout': (response[2] >> 4) & 0x01,
            'sleep_switch': (response[2] >> 5) & 0x01,
            'idle_timeout': response[3],
        }
    
    def get_bmc_time(self) -> Optional[int]:
        """
        获取BMC时间
        
        Returns:
            BMC时间戳
        """
        response = self._send_raw_ipmi(
            self.NETFN_APP << 2,
            0x09,  # Get BMC Time
            b''
        )
        
        if response and len(response) >= 4:
            return (response[0] << 24) | (response[1] << 16) | (response[2] << 8) | response[3]
        
        return None
    
    def get_sel_entries(self, max_entries: int = 10) -> List[Dict[str, Any]]:
        """
        获取系统事件日志
        
        Args:
            max_entries: 最大条目数
            
        Returns:
            SEL条目列表
        """
        entries = []
        
        # 获取SEL信息
        response = self._send_raw_ipmi(
            self.NETFN_STORAGE << 2,
            0x40,  # Get SEL Info
            b''
        )
        
        if not response or len(response) < 16:
            return entries
        
        entry_count = (response[8] << 8) | response[9]
        
        # 读取SEL条目
        for i in range(min(entry_count, max_entries)):
            entry_response = self._send_raw_ipmi(
                self.NETFN_STORAGE << 2,
                0x43,  # Get SEL Entry
                bytes([0x00, 0x00, 0x00, i & 0xFF, 0xFF, 0x00])
            )
            
            if entry_response and len(entry_response) > 6:
                entries.append({
                    'record_id': i,
                    'data': entry_response[5:].hex(),
                })
        
        return entries
    
    def get_lan_config(self, channel: int = 1) -> Optional[Dict[str, Any]]:
        """
        获取网络配置
        
        Args:
            channel: 通道号
            
        Returns:
            网络配置
        """
        config = {}
        
        # 获取IP配置
        response = self._send_raw_ipmi(
            self.NETFN_APP << 2,
            0x02,  # Get Channel Authentication Capabilities
            bytes([0x0E, channel, 0x00])
        )
        
        if response:
            config['channel'] = channel
        
        # 获取IP地址
        ip_response = self._send_raw_ipmi(
            self.NETFN_APP << 2,
            0x01,  # Get IP Address
            bytes([0x0E, 0x00])  # channel=14, dest=0
        )
        
        if ip_response and len(ip_response) >= 5:
            ip = '.'.join(str(b) for b in ip_response[1:5])
            config['ip_address'] = ip
        
        # 获取MAC地址
        mac_response = self._send_raw_ipmi(
            self.NETFN_APP << 2,
            0x03,  # Get MAC Address
            bytes([0x0E, 0x00])
        )
        
        if mac_response and len(mac_response) >= 8:
            mac = ':'.join(f'{b:02X}' for b in mac_response[2:8])
            config['mac_address'] = mac
        
        return config if config else None
    
    def power_control(self, action: str) -> bool:
        """
        电源控制
        
        Args:
            action: 操作 (on, off, cycle, reset, soft)
            
        Returns:
            是否成功
        """
        actions = {
            'on': 0x01,
            'off': 0x00,
            'cycle': 0x02,
            'reset': 0x03,
            'soft': 0x05,
        }
        
        if action not in actions:
            logger.error(f"未知电源操作: {action}")
            return False
        
        response = self._send_raw_ipmi(
            0x00,  # NetFn Chassis
            0x02,  # Chassis Control
            bytes([actions[action]])
        )
        
        return response is not None
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        采集所有IPMI指标
        
        Returns:
            IPMI指标数据
        """
        metrics = {
            'host': self._config.host,
            'timestamp': None,
        }
        
        # 设备信息
        device_id = self.get_device_id()
        if device_id:
            metrics['device'] = device_id
        
        # 机箱状态
        chassis = self.get_chassis_status()
        if chassis:
            metrics['chassis'] = chassis
        
        # 传感器
        sensors = self.get_sensor_list()
        if sensors:
            metrics['sensors'] = sensors
        
        # FRU信息
        fru = self.get_fru_inventory()
        if fru:
            metrics['fru'] = fru
        
        # 网络配置
        lan = self.get_lan_config()
        if lan:
            metrics['network'] = lan
        
        # SEL日志
        sel = self.get_sel_entries()
        if sel:
            metrics['sel_entries'] = sel
        
        return metrics
    
    def close(self) -> None:
        """关闭连接"""
        if self._socket:
            self._socket.close()
        self._socket = None
        self._connected = False
        logger.debug(f"IPMI连接已关闭: {self._config.host}")


class IPMISensorParser:
    """
    IPMI传感器数据解析器
    
    解析IPMI传感器读数，支持多种传感器类型。
    """
    
    # 传感器类型代码
    SENSOR_TYPES = {
        0x01: 'Temperature',
        0x02: 'Voltage',
        0x03: 'Current',
        0x04: 'Fan',
        0x05: 'Physical Security',
        0x06: 'Platform Security',
        0x07: 'Processor',
        0x08: 'Power Supply',
        0x09: 'Power Unit',
        0x0A: 'Memory',
        0x0B: 'Drive Bay',
        0x0C: 'POST Memory Resize',
        0x0D: 'System Firmware Progress',
        0x0E: 'Event Logging Disabled',
        0x0F: 'Watchdog',
        0x10: 'System Event',
        0x11: 'Critical Interrupt',
        0x12: 'Button',
        0x13: 'Module/Board',
        0x14: 'Slot/Connector',
        0x15: 'System ACPI Power State',
        0x16: 'Watchdog',
        0x17: 'Platform Alert',
        0x18: 'Entity Presence',
        0x19: 'Monitor ASIC/IC',
        0x1A: 'LAN',
        0x1B: 'Management Subsystem Health',
        0x1C: 'Battery',
        0x1D: 'Session Audit',
        0x1E: 'Version Change',
        0x1F: 'FRU State',
    }
    
    # 阈值状态位
    THRESHOLD_STATES = {
        0x01: 'Lower Non-Critical',
        0x02: 'Lower Critical',
        0x04: 'Lower Non-Recoverable',
        0x08: 'Upper Non-Critical',
        0x10: 'Upper Critical',
        0x20: 'Upper Non-Recoverable',
        0x40: 'Init Hyteresis',
        0x80: 'Readable Hyteresis',
    }
    
    @classmethod
    def parse_sensor_reading(cls, sensor_type: int, raw_value: bytes) -> Dict[str, Any]:
        """
        解析传感器读数
        
        Args:
            sensor_type: 传感器类型代码
            raw_value: 原始数据
            
        Returns:
            解析后的数据
        """
        result = {
            'sensor_type': cls.SENSOR_TYPES.get(sensor_type, f'Unknown ({sensor_type})'),
            'raw_value': raw_value.hex() if raw_value else '',
        }
        
        if not raw_value:
            return result
        
        if len(raw_value) >= 2:
            value = (raw_value[0] << 8) | raw_value[1]
            result['value'] = value
        
        if len(raw_value) >= 3:
            result['flags'] = raw_value[2]
        
        return result
    
    @classmethod
    def interpret_status_bits(cls, status_byte: int) -> List[str]:
        """
        解析状态位
        
        Args:
            status_byte: 状态字节
            
        Returns:
            状态描述列表
        """
        states = []
        
        for bit, name in cls.THRESHOLD_STATES.items():
            if status_byte & bit:
                states.append(name)
        
        return states if states else ['Normal']


# 厂商特定IPMI配置
IPMI_VENDOR_CONFIGS = {
    'dell': {
        'manufacturer_id': 0x00001C,
        'default_username': 'root',
        'sensor_prefix': 'Dell_',
    },
    'hp': {
        'manufacturer_id': 0x000C28,
        'default_username': 'Administrator',
        'sensor_prefix': 'HP_',
    },
    'lenovo': {
        'manufacturer_id': 0x000C46,
        'default_username': 'root',
        'sensor_prefix': 'Lenovo_',
    },
    'inspur': {
        'manufacturer_id': 0x00006F,
        'default_username': 'admin',
        'sensor_prefix': 'Inspur_',
    },
    'huawei': {
        'manufacturer_id': 0x000193,
        'default_username': 'root',
        'sensor_prefix': 'Huawei_',
    },
}
