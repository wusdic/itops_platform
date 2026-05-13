"""
E2: Device Import - Unit Tests

测试设备批量导入功能:
- DeviceImporter类解析Excel/CSV
- 数据验证
- 批量创建设备
- API端点
"""

import pytest
import io
import uuid
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

# Import modules directly to avoid full app init
import importlib.util


def load_module_directly(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load DeviceImporter module
device_importer_module = load_module_directly(
    "device_importer",
    "/home/zcxx/.hermes/projects/itops_platform/modules/business/device_importer.py"
)

DeviceImporter = device_importer_module.DeviceImporter
ImportFormat = device_importer_module.ImportFormat
DeviceImportResult = device_importer_module.DeviceImportResult


# ============== DataFactory for Device Import Tests ==============

class DeviceImportDataFactory:
    """设备导入测试数据工厂"""
    
    def __init__(self, seed: int = None):
        import random
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
        self._random = random
    
    def _uid(self) -> str:
        self._counter += 1
        return f"dev_{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def device_type(self) -> str:
        """随机设备类型"""
        types = [
            'server_linux', 'server_windows', 'network_switch', 
            'network_router', 'network_firewall', 'storage_nas',
            'security_ids', 'other'
        ]
        return self._random.choice(types)
    
    def ip_address(self) -> str:
        """随机IP地址"""
        return f"192.168.{self._random.randint(1, 254)}.{self._random.randint(1, 254)}"
    
    def device_row(self, **overrides) -> dict:
        """生成单个设备数据行"""
        data = {
            'name': f"设备-{self._uid()}",
            'ip_address': self.ip_address(),
            'device_type': self.device_type(),
            'vendor': self._random.choice(['Dell', 'HP', 'Cisco', '华为', '联想', '']),
            'model': self._random.choice(['PowerEdge R740', 'ProLiant DL380', 'Catalyst 9300', '']),
            'snmp_community': self._random.choice(['public', 'private', '']),
            'location': self._random.choice(['机房A-机柜1', '机房B-机柜2', '']),
            'idc': self._random.choice(['IDC-A', 'IDC-B', '']),
        }
        data.update(overrides)
        return data


# ============== Test Cases ==============

class TestDeviceImporterBasics:
    """设备导入器基础测试"""
    
    def test_importer_init(self):
        """测试导入器初始化"""
        importer = DeviceImporter()
        assert importer is not None
        assert importer.REQUIRED_FIELDS == ['name', 'ip_address', 'device_type']
    
    def test_device_type_mapping(self):
        """测试设备类型映射"""
        importer = DeviceImporter()
        
        # 英文类型
        assert importer.DEVICE_TYPE_MAP['server'] == 'server_linux'
        assert importer.DEVICE_TYPE_MAP['server_linux'] == 'server_linux'
        assert importer.DEVICE_TYPE_MAP['network_switch'] == 'network_switch'
        
        # 中文类型
        assert importer.DEVICE_TYPE_MAP['服务器'] == 'server_linux'
        assert importer.DEVICE_TYPE_MAP['交换机'] == 'network_switch'
        assert importer.DEVICE_TYPE_MAP['防火墙'] == 'network_firewall'
    
    def test_ip_pattern_validation(self):
        """测试IP地址格式验证"""
        importer = DeviceImporter()
        
        # 有效IP
        assert importer.IP_PATTERN.match('192.168.1.1')
        assert importer.IP_PATTERN.match('10.0.0.1')
        assert importer.IP_PATTERN.match('255.255.255.255')
        assert importer.IP_PATTERN.match('0.0.0.0')
        
        # 无效IP
        assert not importer.IP_PATTERN.match('256.1.1.1')
        assert not importer.IP_PATTERN.match('192.168.1')
        assert not importer.IP_PATTERN.match('192.168.1.1.1')
        assert not importer.IP_PATTERN.match('abc.def.ghi.jkl')
        assert not importer.IP_PATTERN.match('')


class TestDeviceImporterValidation:
    """设备导入数据验证测试"""
    
    def test_validate_valid_row(self):
        """验证有效数据行"""
        importer = DeviceImporter()
        row = {
            'name': '测试服务器',
            'ip_address': '192.168.1.100',
            'device_type': 'server_linux'
        }
        
        is_valid, error = importer.validate_row(row)
        assert is_valid is True
        assert error == ''
    
    def test_validate_missing_required_field(self):
        """验证缺少必填字段"""
        importer = DeviceImporter()
        
        # 缺少name
        row = {
            'ip_address': '192.168.1.100',
            'device_type': 'server_linux'
        }
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert 'name' in error
        
        # 缺少ip_address
        row = {
            'name': '测试服务器',
            'device_type': 'server_linux'
        }
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert 'ip_address' in error
        
        # 缺少device_type
        row = {
            'name': '测试服务器',
            'ip_address': '192.168.1.100'
        }
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert 'device_type' in error
    
    def test_validate_invalid_ip(self):
        """验证无效IP地址"""
        importer = DeviceImporter()
        row = {
            'name': '测试服务器',
            'ip_address': 'invalid_ip',
            'device_type': 'server_linux'
        }
        
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert 'IP' in error
    
    def test_validate_invalid_device_type(self):
        """验证无效设备类型"""
        importer = DeviceImporter()
        row = {
            'name': '测试服务器',
            'ip_address': '192.168.1.100',
            'device_type': 'invalid_type'
        }
        
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert 'device_type' in error.lower() or '不支持' in error
    
    def test_validate_empty_string_required(self):
        """验证空白字符串视为缺失"""
        importer = DeviceImporter()
        row = {
            'name': '   ',
            'ip_address': '192.168.1.100',
            'device_type': 'server_linux'
        }
        
        is_valid, error = importer.validate_row(row)
        assert is_valid is False


class TestDeviceImporterParsing:
    """设备导入文件解析测试"""
    
    def test_parse_csv_basic(self):
        """测试解析基本CSV"""
        csv_content = b'\xe8\xae\xbe\xe5\xa4\x87\xe5\x90\x8d\xe7\xa7\xb0,\xe6\x95\xb0\xe6\x8d\xaeIP,server_linux,Dell\ntest,192.168.1.1,server_linux,Dell'
        
        importer = DeviceImporter()
        # CSV with headers
        csv_with_header = b'\xe8\xae\xbe\xe5\xa4\x87\xe5\x90\x8d\xe7\xa7\xb0,IP\xe5\x9c\xb0\xe5\x9d\x80,\xe8\xae\xbe\xe5\xa4\x87\xe7\xb1\xbb\xe5\x9e\x8b\ntest,192.168.1.1,server_linux'
        
        data = importer.parse_file(csv_with_header, 'test.csv', ImportFormat.CSV)
        assert isinstance(data, list)
    
    def test_parse_csv_no_header(self):
        """测试无表头CSV解析"""
        csv_content = b'test-server,192.168.1.1,server_linux'
        
        importer = DeviceImporter()
        data = importer.parse_file(csv_content, 'test.csv', ImportFormat.CSV)
        # Without header, data might be parsed differently
        assert isinstance(data, list)
    
    def test_generate_template_xlsx(self):
        """测试生成XLSX模板"""
        importer = DeviceImporter()
        
        try:
            content, content_type = importer.generate_template(ImportFormat.XLSX)
            assert content is not None
            assert len(content) > 0
            assert 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type
        except ImportError:
            # openpyxl not available, skip
            pytest.skip("openpyxl not available")
    
    def test_generate_template_csv(self):
        """测试生成CSV模板"""
        importer = DeviceImporter()
        
        content, content_type = importer.generate_template(ImportFormat.CSV)
        assert content is not None
        assert len(content) > 0
        assert 'text/csv' in content_type


class TestDeviceImporterValidateData:
    """设备导入数据验证测试"""
    
    def test_validate_data_all_valid(self):
        """验证全部有效数据"""
        importer = DeviceImporter()
        factory = DeviceImportDataFactory(seed=42)
        
        rows = [factory.device_row() for _ in range(5)]
        result = importer.validate_data(rows)
        
        assert result.total == 5
        assert len(result.success) == 5
        assert len(result.failed) == 0
    
    def test_validate_data_partial_valid(self):
        """验证部分有效数据"""
        importer = DeviceImporter()
        factory = DeviceImportDataFactory(seed=42)
        
        rows = [
            factory.device_row(),  # valid
            {'name': 'test', 'ip_address': 'invalid', 'device_type': 'server'},  # invalid IP
            factory.device_row(),  # valid
        ]
        
        result = importer.validate_data(rows)
        
        assert result.total == 3
        assert len(result.success) == 2
        assert len(result.failed) == 1
        assert result.failed[0]['error'] is not None


class TestDeviceImportResult:
    """设备导入结果测试"""
    
    def test_result_init(self):
        """测试结果初始化"""
        result = DeviceImportResult()
        assert result.total == 0
        assert len(result.success) == 0
        assert len(result.failed) == 0
    
    def test_result_add_success(self):
        """测试添加成功记录"""
        result = DeviceImportResult()
        row = {'name': 'test', 'ip_address': '192.168.1.1', 'device_type': 'server'}
        
        result.add_success(row, device_id=123)
        
        assert len(result.success) == 1
        assert result.success[0]['imported_id'] == 123
        assert result.success[0]['import_status'] == 'success'
    
    def test_result_add_failure(self):
        """测试添加失败记录"""
        result = DeviceImportResult()
        row = {'name': 'test', 'ip_address': '192.168.1.1', 'device_type': 'server'}
        
        result.add_failure(row, 'Test error', row_num=5)
        
        assert len(result.failed) == 1
        assert result.failed[0]['error'] == 'Test error'
        assert result.failed[0]['row'] == 5
        assert result.failed[0]['import_status'] == 'failed'
    
    def test_result_to_dict(self):
        """测试结果转换为字典"""
        result = DeviceImportResult()
        result.total = 10
        result.add_success({'name': 'test1'}, device_id=1)
        result.add_failure({'name': 'test2'}, 'error')
        
        d = result.to_dict()
        
        assert d['total'] == 10
        assert d['success_count'] == 1
        assert d['failed_count'] == 1


class TestDeviceImportEdgeCases:
    """设备导入边界情况测试"""
    
    def test_validate_row_name_too_long(self):
        """验证设备名称过长"""
        importer = DeviceImporter()
        row = {
            'name': 'x' * 200,  # 超过128字符
            'ip_address': '192.168.1.1',
            'device_type': 'server'
        }
        
        is_valid, error = importer.validate_row(row)
        assert is_valid is False
        assert '过长' in error
    
    def test_validate_chinese_device_type(self):
        """验证中文设备类型"""
        importer = DeviceImporter()
        
        # 服务器
        row = {'name': 'test', 'ip_address': '192.168.1.1', 'device_type': '服务器'}
        is_valid, error = importer.validate_row(row)
        assert is_valid is True
        
        # 交换机
        row = {'name': 'test', 'ip_address': '192.168.1.1', 'device_type': '交换机'}
        is_valid, error = importer.validate_row(row)
        assert is_valid is True
    
    def test_normalize_header(self):
        """测试列名标准化"""
        importer = DeviceImporter()
        
        assert importer._normalize_header('设备名称') == 'name'
        assert importer._normalize_header('IP地址') == 'ip_address'
        assert importer._normalize_header('ip') == 'ip_address'
        assert importer._normalize_header('设备类型') == 'device_type'
        assert importer._normalize_header('type') == 'device_type'


class TestDeviceImportWorkflow:
    """设备导入完整流程测试"""
    
    def test_import_workflow_mock(self):
        """测试导入完整流程（mock数据库）"""
        importer = DeviceImporter()
        factory = DeviceImportDataFactory(seed=100)
        
        # 生成测试数据
        rows = [factory.device_row() for _ in range(3)]
        
        # 验证数据
        validate_result = importer.validate_data(rows)
        assert validate_result.total == 3
        
        # 模拟导入（不实际连接数据库）
        # 注意：实际导入需要数据库连接
        for row in rows:
            is_valid, error = importer.validate_row(row)
            if is_valid:
                # 模拟成功
                assert row['name'] is not None
                assert row['ip_address'] is not None
    
    def test_csv_template_format(self):
        """测试CSV模板格式"""
        importer = DeviceImporter()
        
        content, content_type = importer.generate_template(ImportFormat.CSV)
        
        # 验证UTF-8 BOM
        assert content[:3] == b'\xef\xbb\xbf'
        
        # 验证内容包含表头
        text = content.decode('utf-8-sig')
        assert '设备名称' in text
        assert 'IP地址' in text
        assert '设备类型' in text


# ============== Run Tests ==============

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
