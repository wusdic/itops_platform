"""
IPMI Client Unit Tests

测试IPMI客户端的各个功能模块，包括:
- IPMIVersion枚举
- IPMIConfig数据类
- 连接认证 (_authenticate_v1_5, _authenticate_v2)
- 传感器操作 (get_sensor_list, read_sensor)
- FRU清单 (get_fru_inventory)
- 电源控制 (power_control)
- 校验和计算 (_calculate_checksum)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import struct

from modules.collection.ipmi_collector.ipmi_client import (
    IPMIClient,
    IPMIVersion,
    IPMIConfig,
)


class TestIPMIVersion(unittest.TestCase):
    """测试IPMIVersion枚举"""

    def test_ipmi_version_values(self):
        """测试版本枚举值"""
        self.assertEqual(IPMIVersion.V1_5.value, 'v1.5')
        self.assertEqual(IPMIVersion.V2_0.value, 'v2.0')

    def test_ipmi_version_is_string(self):
        """测试版本枚举继承自str"""
        self.assertIsInstance(IPMIVersion.V1_5, str)
        self.assertIsInstance(IPMIVersion.V2_0, str)


class TestIPMIConfig(unittest.TestCase):
    """测试IPMIConfig数据类"""

    def test_default_config(self):
        """测试默认配置"""
        config = IPMIConfig(host='192.168.1.1')
        self.assertEqual(config.host, '192.168.1.1')
        self.assertEqual(config.port, 623)
        self.assertEqual(config.username, 'admin')
        self.assertEqual(config.password, '')
        self.assertEqual(config.version, IPMIVersion.V2_0)
        self.assertEqual(config.timeout, 5)

    def test_custom_config(self):
        """测试自定义配置"""
        config = IPMIConfig(
            host='10.0.0.1',
            port=626,
            username='admin',
            password='secret',
            version=IPMIVersion.V1_5,
            timeout=10
        )
        self.assertEqual(config.host, '10.0.0.1')
        self.assertEqual(config.port, 626)
        self.assertEqual(config.username, 'admin')
        self.assertEqual(config.password, 'secret')
        self.assertEqual(config.version, IPMIVersion.V1_5)
        self.assertEqual(config.timeout, 10)


class TestIPMIChecksumCalculation(unittest.TestCase):
    """测试校验和计算"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    def test_checksum_basic(self):
        """测试基本校验和计算"""
        # 当数据和为0时，校验和应为0
        checksum = self.client._calculate_checksum(b'')
        self.assertEqual(checksum, 0)

    def test_checksum_single_byte(self):
        """测试单字节数据校验和"""
        # 如果sum=5, (256-5)%256 = 251
        checksum = self.client._calculate_checksum(b'\x05')
        self.assertEqual(checksum, 251)

    def test_checksum_multiple_bytes(self):
        """测试多字节数据校验和"""
        # 如果sum=10, (256-10)%256 = 246
        checksum = self.client._calculate_checksum(b'\x01\x02\x03\x04')
        self.assertEqual(checksum, 246)

    def test_checksum_with_extra(self):
        """测试带额外值的校验和"""
        # sum(data)=5, extra=10, total=15, (256-15)%256 = 241
        checksum = self.client._calculate_checksum(b'\x05', 10)
        self.assertEqual(checksum, 241)

    def test_checksum_boundary(self):
        """测试边界情况"""
        # 当sum%256=0时，校验和应为0
        checksum = self.client._calculate_checksum(b'\x00' * 256)
        self.assertEqual(checksum, 0)


class TestIPMIAuthentication(unittest.TestCase):
    """测试IPMI认证"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1', version=IPMIVersion.V2_0)
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_authenticate_v2_success(self, mock_send_raw):
        """测试v2.0认证成功"""
        mock_send_raw.return_value = bytes([0x00, 0x00, 0x00])
        result = self.client._authenticate_v2()
        self.assertTrue(result)
        mock_send_raw.assert_called_once()

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_authenticate_v2_failure(self, mock_send_raw):
        """测试v2.0认证失败"""
        mock_send_raw.return_value = None
        result = self.client._authenticate_v2()
        self.assertFalse(result)

    def test_authenticate_v1_5_success(self):
        """测试v1.5认证成功"""
        config_v15 = IPMIConfig(host='127.0.0.1', version=IPMIVersion.V1_5)
        client_v15 = IPMIClient(config_v15)
        with patch.object(client_v15, '_send_raw_ipmi') as mock_send:
            mock_send.return_value = bytes([0x01])
            result = client_v15._authenticate_v1_5()
            self.assertTrue(result)

    def test_authenticate_v1_5_failure(self):
        """测试v1.5认证失败"""
        config_v15 = IPMIConfig(host='127.0.0.1', version=IPMIVersion.V1_5)
        client_v15 = IPMIClient(config_v15)
        with patch.object(client_v15, '_send_raw_ipmi') as mock_send:
            mock_send.return_value = None
            result = client_v15._authenticate_v1_5()
            self.assertFalse(result)


class TestIPMISensorOperations(unittest.TestCase):
    """测试IPMI传感器操作"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_sensor_list(self, mock_send_raw):
        """测试获取传感器列表"""
        # 模拟响应: sensor_count=3, sensor_ids=[1,2,3]
        mock_send_raw.return_value = bytes([0x03, 0x01, 0x02, 0x03])
        sensors = self.client.get_sensor_list()
        self.assertEqual(len(sensors), 3)
        self.assertEqual(sensors[0]['sensor_id'], 1)
        self.assertEqual(sensors[1]['sensor_id'], 2)
        self.assertEqual(sensors[2]['sensor_id'], 3)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_sensor_list_empty(self, mock_send_raw):
        """测试获取空传感器列表"""
        mock_send_raw.return_value = bytes([0x00])
        sensors = self.client.get_sensor_list()
        self.assertEqual(len(sensors), 0)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_sensor_list_max_limit(self, mock_send_raw):
        """测试传感器列表最大数量限制"""
        # 模拟超过64个传感器
        response = bytes([0xFF] + list(range(65)))
        mock_send_raw.return_value = response
        sensors = self.client.get_sensor_list()
        self.assertEqual(len(sensors), 64)  # 应该限制在64个

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_read_sensor(self, mock_send_raw):
        """测试读取传感器"""
        # 模拟传感器响应
        mock_send_raw.return_value = bytes([0x2A, 0x05, 0x00, 0x00, 0xFF])
        result = self.client.read_sensor(10)
        self.assertIsNotNone(result)
        self.assertEqual(result['sensor_number'], 10)
        self.assertEqual(result['value'], 0x2A)
        self.assertEqual(result['flags'], 0x05)
        self.assertEqual(result['threshold_status'], 0x00)
        self.assertEqual(result['reserved'], 0x00)
        self.assertEqual(result['sensor_specific'], 0xFF)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_read_sensor_failure(self, mock_send_raw):
        """测试读取传感器失败"""
        mock_send_raw.return_value = bytes([0x00, 0x01])  # 数据太短
        result = self.client.read_sensor(1)
        self.assertIsNone(result)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_read_sensor_none_response(self, mock_send_raw):
        """测试读取传感器无响应"""
        mock_send_raw.return_value = None
        result = self.client.read_sensor(1)
        self.assertIsNone(result)


class TestIPMIFRUInventory(unittest.TestCase):
    """测试IPMI FRU清单"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_fru_inventory(self, mock_send_raw):
        """测试获取FRU清单"""
        mock_send_raw.return_value = bytes([0x01, 0x02, 0x03, 0x04, 0x05])
        result = self.client.get_fru_inventory(0)
        self.assertIsNotNone(result)
        self.assertEqual(result['fru_id'], 0)
        self.assertEqual(result['data_length'], 5)
        self.assertEqual(result['data'], '0102030405')

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_fru_inventory_custom_id(self, mock_send_raw):
        """测试获取指定ID的FRU清单"""
        mock_send_raw.return_value = bytes([0xAA, 0xBB])
        result = self.client.get_fru_inventory(5)
        self.assertIsNotNone(result)
        self.assertEqual(result['fru_id'], 5)
        mock_send_raw.assert_called_with(
            self.client.NETFN_STORAGE << 2,
            0x11,
            bytes([5, 0x00, 0x00])
        )

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_fru_inventory_failure(self, mock_send_raw):
        """测试获取FRU清单失败"""
        mock_send_raw.return_value = None
        result = self.client.get_fru_inventory(0)
        self.assertIsNone(result)


class TestIPMIPowerControl(unittest.TestCase):
    """测试IPMI电源控制"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_on(self, mock_send_raw):
        """测试开机"""
        mock_send_raw.return_value = bytes([0x00])
        result = self.client.power_control('on')
        self.assertTrue(result)
        mock_send_raw.assert_called_with(0x00, 0x02, bytes([0x01]))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_off(self, mock_send_raw):
        """测试关机"""
        mock_send_raw.return_value = bytes([0x00])
        result = self.client.power_control('off')
        self.assertTrue(result)
        mock_send_raw.assert_called_with(0x00, 0x02, bytes([0x00]))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_cycle(self, mock_send_raw):
        """测试重启"""
        mock_send_raw.return_value = bytes([0x00])
        result = self.client.power_control('cycle')
        self.assertTrue(result)
        mock_send_raw.assert_called_with(0x00, 0x02, bytes([0x02]))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_reset(self, mock_send_raw):
        """测试复位"""
        mock_send_raw.return_value = bytes([0x00])
        result = self.client.power_control('reset')
        self.assertTrue(result)
        mock_send_raw.assert_called_with(0x00, 0x02, bytes([0x03]))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_soft(self, mock_send_raw):
        """测试软关机"""
        mock_send_raw.return_value = bytes([0x00])
        result = self.client.power_control('soft')
        self.assertTrue(result)
        mock_send_raw.assert_called_with(0x00, 0x02, bytes([0x05]))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_power_control_failure(self, mock_send_raw):
        """测试电源控制失败"""
        mock_send_raw.return_value = None
        result = self.client.power_control('on')
        self.assertFalse(result)

    def test_power_control_invalid_action(self):
        """测试无效电源操作"""
        result = self.client.power_control('invalid')
        self.assertFalse(result)


class TestIPMIDeviceID(unittest.TestCase):
    """测试获取设备ID"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_device_id(self, mock_send_raw):
        """测试获取设备ID"""
        # 模拟设备ID响应
        # firmware_revision = (response[2] << 8) | response[3] = 0x01 << 8 | 0x02 = 258
        mock_send_raw.return_value = bytes([
            0x01,  # device_id
            0x11,  # device_revision
            0x01, 0x02,  # firmware_revision (major, minor) = 258
            0x21,  # ipmi_version (2.1)
            0x04,  # device_type
            0x00, 0x00, 0x00,  # manufacturer_id (3 bytes, LSB first)
            0x01, 0x00,  # product_id (LSB first)
        ])
        result = self.client.get_device_id()
        self.assertIsNotNone(result)
        self.assertEqual(result['device_id'], 1)
        self.assertEqual(result['device_revision'], 17)
        self.assertEqual(result['firmware_revision'], 258)
        self.assertEqual(result['ipmi_version'], '2.1')
        self.assertEqual(result['device_type'], 4)
        self.assertEqual(result['manufacturer_id'], 0)
        self.assertEqual(result['product_id'], 1)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_device_id_response_too_short(self, mock_send_raw):
        """测试响应数据太短"""
        mock_send_raw.return_value = bytes([0x01, 0x02])
        result = self.client.get_device_id()
        self.assertIsNone(result)


class TestIPMISendRawIPMI(unittest.TestCase):
    """测试发送原始IPMI消息"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)
        self.mock_socket = MagicMock()

    def test_send_raw_ipmi_no_socket(self):
        """测试无socket时返回None"""
        self.client._socket = None
        result = self.client._send_raw_ipmi(0x06, 0x01)
        self.assertIsNone(result)

    @patch.object(IPMIClient, '_calculate_checksum')
    def test_send_raw_ipmi_v1_5(self, mock_checksum):
        """测试v1.5发送"""
        mock_checksum.return_value = 0
        self.client._config.version = IPMIVersion.V1_5
        self.client._socket = self.mock_socket
        # 响应需要足够长 (>5) 才能通过检查
        self.mock_socket.recv.return_value = bytes([0x00] * 10)

        result = self.client._send_raw_ipmi(0x06, 0x01, b'\x00')

        self.assertIsNotNone(result)
        self.mock_socket.send.assert_called_once()
        self.mock_socket.recv.assert_called_once()

    @patch.object(IPMIClient, '_calculate_checksum')
    def test_send_raw_ipmi_v2_0(self, mock_checksum):
        """测试v2.0发送"""
        mock_checksum.return_value = 0
        self.client._config.version = IPMIVersion.V2_0
        self.client._socket = self.mock_socket
        # 响应需要足够长 (>5) 才能通过检查
        self.mock_socket.recv.return_value = bytes([0x00] * 10)

        result = self.client._send_raw_ipmi(0x06, 0x01, b'\x00')

        self.assertIsNotNone(result)
        self.mock_socket.send.assert_called_once()

    def test_send_raw_ipmi_socket_timeout(self):
        """测试socket超时"""
        self.client._socket = self.mock_socket
        self.mock_socket.recv.side_effect = TimeoutError()

        result = self.client._send_raw_ipmi(0x06, 0x01)

        self.assertIsNone(result)

    def test_send_raw_ipmi_exception(self):
        """测试发送异常"""
        self.client._socket = self.mock_socket
        self.mock_socket.send.side_effect = Exception("Network error")

        result = self.client._send_raw_ipmi(0x06, 0x01)

        self.assertIsNone(result)

    def test_send_raw_ipmi_empty_response(self):
        """测试空响应"""
        self.client._socket = self.mock_socket
        self.mock_socket.recv.return_value = bytes([0xFF] * 3)  # 太短

        result = self.client._send_raw_ipmi(0x06, 0x01)

        self.assertIsNone(result)


class TestIPMIConnect(unittest.TestCase):
    """测试IPMI连接"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1', version=IPMIVersion.V2_0)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    @patch('socket.socket')
    def test_connect_success_v2(self, mock_socket_class, mock_send_raw):
        """测试v2.0连接成功"""
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        mock_send_raw.return_value = bytes([0x00] * 10)

        client = IPMIClient(self.config)
        result = client.connect()

        self.assertTrue(result)
        mock_socket_instance.connect.assert_called_once_with(('127.0.0.1', 623))

    @patch.object(IPMIClient, '_send_raw_ipmi')
    @patch('socket.socket')
    def test_connect_success_v1_5(self, mock_socket_class, mock_send_raw):
        """测试v1.5连接成功"""
        self.config.version = IPMIVersion.V1_5
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        mock_send_raw.return_value = bytes([0x00] * 10)

        client = IPMIClient(self.config)
        result = client.connect()

        self.assertTrue(result)

    @patch('socket.socket')
    def test_connect_failure(self, mock_socket_class):
        """测试连接失败"""
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        mock_socket_instance.connect.side_effect = Exception("Connection refused")

        client = IPMIClient(self.config)
        result = client.connect()

        self.assertFalse(result)


class TestIPMIMessagePacking(unittest.TestCase):
    """测试IPMI消息打包/解包逻辑"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    def test_checksum_for_ipmi_message(self):
        """测试IPMI消息校验和计算"""
        # 测试IPMI消息校验和 - 使用整数extra参数
        # data = [0x20, 0x18], extra = 0x18
        data = bytes([0x20, 0x18])
        extra = 0x18

        # 计算校验和: (256 - (sum(data) + extra) % 256) % 256
        # sum = 0x20 + 0x18 = 32 + 24 = 56
        # total = 56 + 0x18 = 56 + 24 = 80
        # checksum = (256 - 80) % 256 = 176
        checksum = self.client._calculate_checksum(data, extra)
        self.assertEqual(checksum, 176)

    def test_checksum_zero_data(self):
        """测试空数据的校验和"""
        checksum = self.client._calculate_checksum(b'', 0)
        self.assertEqual(checksum, 0)


class TestIPMIChassisStatus(unittest.TestCase):
    """测试机箱状态"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_chassis_status(self, mock_send_raw):
        """测试获取机箱状态"""
        # response[0] = 0x01: current_power_state=1, power_restoration=0
        # response[1] = 0x02: power_control=2, power_override=0
        # response[2] = 0x0C: power_system=0, power_fan=0, cooling_fault=1, drive_fault=1, front_panel_lockout=0, sleep_switch=0
        # response[3] = 0x05: idle_timeout=5
        mock_send_raw.return_value = bytes([0x01, 0x02, 0x0C, 0x05])
        result = self.client.get_chassis_status()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['current_power_state'], 1)
        self.assertEqual(result['power_restoration'], 0)
        self.assertEqual(result['power_control'], 2)
        self.assertEqual(result['power_override'], 0)
        self.assertEqual(result['power_system'], 0)
        self.assertEqual(result['power_fan'], 0)
        self.assertEqual(result['cooling_fault'], 1)
        self.assertEqual(result['drive_fault'], 1)
        self.assertEqual(result['front_panel_lockout'], 0)
        self.assertEqual(result['sleep_switch'], 0)
        self.assertEqual(result['idle_timeout'], 5)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_chassis_status_too_short(self, mock_send_raw):
        """测试机箱状态响应太短"""
        mock_send_raw.return_value = bytes([0x01, 0x02])
        result = self.client.get_chassis_status()
        self.assertIsNone(result)


class TestIPMIBMCTime(unittest.TestCase):
    """测试BMC时间"""

    def setUp(self):
        """设置测试环境"""
        self.config = IPMIConfig(host='127.0.0.1')
        self.client = IPMIClient(self.config)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_bmc_time(self, mock_send_raw):
        """测试获取BMC时间"""
        # 0x5D = 93, 0xC2 = 194, 0x91 = 145, 0x5E = 94
        # 时间戳 = 93 + 194*256 + 145*256*256 + 94*256*256*256
        mock_send_raw.return_value = bytes([0x5D, 0xC2, 0x91, 0x5E])
        result = self.client.get_bmc_time()
        self.assertIsNotNone(result)
        self.assertEqual(result, 0x5DC2915E)

    @patch.object(IPMIClient, '_send_raw_ipmi')
    def test_get_bmc_time_response_too_short(self, mock_send_raw):
        """测试BMC时间响应太短"""
        mock_send_raw.return_value = bytes([0x5D, 0xC2])
        result = self.client.get_bmc_time()
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
