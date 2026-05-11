"""
SSH采集单元测试
"""

import io
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.collection.ssh_collector.ssh_client import (
    SSHConfig, SSHClient, SSHConnectionPool
)
from modules.collection.ssh_collector.winrm_client import (
    WinRMConfig, WinRMClient
)
from modules.collection.ssh_collector.collectors.linux_collector import LinuxCollector
from modules.collection.ssh_collector.collectors.windows_collector import WindowsCollector
from modules.collection.ssh_collector.collectors.kylin_collector import KylinCollector
from modules.collection.ssh_collector.config_deployer import (
    ConfigBackup, ConfigDeployer, DeployTask, DeployStatus
)


class TestSSHConfig(unittest.TestCase):
    """SSH配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SSHConfig(host='192.168.1.1')
        
        self.assertEqual(config.host, '192.168.1.1')
        self.assertEqual(config.port, 22)
        self.assertEqual(config.username, 'root')
        self.assertEqual(config.timeout, 10)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SSHConfig(
            host='192.168.1.1',
            port=2222,
            username='admin',
            password='secret',
            timeout=30
        )
        
        self.assertEqual(config.host, '192.168.1.1')
        self.assertEqual(config.port, 2222)
        self.assertEqual(config.username, 'admin')
        self.assertEqual(config.password, 'secret')
        self.assertEqual(config.timeout, 30)
    
    def test_key_auth_config(self):
        """测试密钥认证配置"""
        config = SSHConfig(
            host='192.168.1.1',
            key_file='/root/.ssh/id_rsa',
            key_password='key_passphrase'
        )
        
        self.assertEqual(config.key_file, '/root/.ssh/id_rsa')
        self.assertEqual(config.key_password, 'key_passphrase')


class TestSSHClient(unittest.TestCase):
    """SSH客户端测试"""
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_connect_password_auth(self, mock_paramiko):
        """测试密码认证连接"""
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(
            host='192.168.1.1',
            username='admin',
            password='secret'
        )
        
        client = SSHClient(config)
        result = client.connect()
        
        self.assertTrue(result)
        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once()
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_execute_command(self, mock_paramiko):
        """测试命令执行"""
        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b'output'
        mock_stderr.read.return_value = b''
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        client = SSHClient(config)
        client._connected = True
        client._client = mock_client
        
        exit_code, stdout, stderr = client.execute('ls -la')
        
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, 'output')
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_upload_file(self, mock_paramiko):
        """测试文件上传"""
        mock_sftp = MagicMock()
        mock_client = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        client = SSHClient(config)
        client._connected = True
        client._client = mock_client
        client._sftp = None
        
        # 测试上传BytesIO
        content = io.BytesIO(b'test content')
        result = client.upload_file(content, '/tmp/test.txt')
        
        self.assertTrue(result)
        mock_sftp.putfo.assert_called_once()
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_close_connection(self, mock_paramiko):
        """测试关闭连接"""
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        client = SSHClient(config)
        client._connected = True
        client._client = mock_client
        
        client.close()
        
        self.assertFalse(client._connected)
        mock_client.close.assert_called_once()


class TestSSHConnectionPool(unittest.TestCase):
    """SSH连接池测试"""
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_pool_initialization(self, mock_paramiko):
        """测试连接池初始化"""
        pool = SSHConnectionPool(max_connections=5)
        
        self.assertEqual(pool._max_connections, 5)
        self.assertEqual(len(pool._pool), 0)
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_get_client(self, mock_paramiko):
        """测试获取客户端"""
        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.connect.return_value = True
        mock_paramiko.SSHClient.return_value = mock_client
        
        pool = SSHConnectionPool()
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        
        client = pool.get_client(config)
        
        self.assertIsNotNone(client)
        mock_client.connect.assert_called_once()


class TestWinRMConfig(unittest.TestCase):
    """WinRM配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = WinRMConfig(
            host='192.168.1.1',
            username='admin',
            password='secret'
        )
        
        self.assertEqual(config.host, '192.168.1.1')
        self.assertEqual(config.port, 5985)
        self.assertEqual(config.username, 'admin')
        self.assertFalse(config.ssl)
    
    def test_https_config(self):
        """测试HTTPS配置"""
        config = WinRMConfig(
            host='192.168.1.1',
            username='admin',
            password='secret',
            ssl=True
        )
        
        self.assertEqual(config.port, 5986)
        self.assertTrue(config.ssl)


class TestLinuxCollector(unittest.TestCase):
    """Linux采集器测试"""
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_detect_distro_centos(self, mock_paramiko):
        """测试检测CentOS"""
        mock_client = MagicMock()
        mock_client.execute.return_value = (0, 'CentOS Linux release 7.9', '')
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = LinuxCollector(ssh_client)
        distro = collector.detect_distro()
        
        self.assertEqual(distro, 'centos')
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_detect_distro_ubuntu(self, mock_paramiko):
        """测试检测Ubuntu"""
        mock_client = MagicMock()
        mock_client.execute.return_value = (0, 'Ubuntu 22.04 LTS', '')
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = LinuxCollector(ssh_client)
        distro = collector.detect_distro()
        
        self.assertEqual(distro, 'ubuntu')
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_collect_system_info(self, mock_paramiko):
        """测试采集系统信息"""
        mock_client = MagicMock()
        
        # 模拟多个命令输出
        def execute_side_effect(cmd, timeout=None, block=True):
            if 'hostname' in cmd:
                return (0, 'server01', '')
            elif 'uname -r' in cmd:
                return (0, '5.4.0-90-generic', '')
            elif 'PRETTY_NAME' in cmd:
                return (0, 'PRETTY_NAME="Ubuntu 22.04 LTS"', '')
            elif 'uptime' in cmd:
                return (0, 'up 5 days, 3:22', '')
            return (0, '', '')
        
        mock_client.execute.side_effect = execute_side_effect
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = LinuxCollector(ssh_client)
        info = collector.collect_system_info()
        
        self.assertIn('hostname', info)
        self.assertEqual(info['hostname'], 'server01')
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_collect_memory_info(self, mock_paramiko):
        """测试采集内存信息"""
        mock_client = MagicMock()
        mock_client.execute.return_value = (0, '''MemTotal:        16384000 kB
MemFree:          8192000 kB
MemAvailable:    12288000 kB
Buffers:          2048000 kB
Cached:           4096000 kB
''', '')
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = LinuxCollector(ssh_client)
        info = collector.collect_memory_info()
        
        self.assertIn('total_mb', info)
        self.assertEqual(info['total_mb'], 16000)


class TestKylinCollector(unittest.TestCase):
    """麒麟采集器测试"""
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_detect_version_kylin_v10(self, mock_paramiko):
        """测试检测银河麒麟V10"""
        mock_client = MagicMock()
        mock_client.execute.return_value = (0, 'Kylin Linux Advanced Server V10', '')
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = KylinCollector(ssh_client)
        version = collector.detect_version()
        
        self.assertEqual(version, 'kylin_v10')
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_collect_security_info(self, mock_paramiko):
        """测试采集安全信息"""
        mock_client = MagicMock()
        
        def execute_side_effect(cmd, timeout=None, block=True):
            if 'kylin-audit' in cmd:
                return (0, 'Active: active', '')
            return (0, '', '')
        
        mock_client.execute.side_effect = execute_side_effect
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        collector = KylinCollector(ssh_client)
        info = collector.collect_sec_info()
        
        self.assertIn('audit_enabled', info)
        self.assertTrue(info['audit_enabled'])


class TestConfigBackup(unittest.TestCase):
    """配置备份测试"""
    
    def setUp(self):
        """设置测试"""
        self.backup_dir = '/tmp/test_backups'
    
    @patch('modules.collection.ssh_collector.ssh_client.paramiko')
    def test_backup_config(self, mock_paramiko):
        """测试配置备份"""
        mock_client = MagicMock()
        mock_client.execute.return_value = (0, 'interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0', '')
        
        mock_paramiko.SSHClient.return_value = mock_client
        
        config = SSHConfig(host='192.168.1.1', username='admin', password='secret')
        ssh_client = SSHClient(config)
        ssh_client._connected = True
        ssh_client._client = mock_client
        
        backup_manager = ConfigBackup(self.backup_dir)
        backup_path = backup_manager.backup_config(ssh_client, 'running', 'Test backup')
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # 清理
        import shutil
        if os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)
    
    def test_get_backup_list(self):
        """测试获取备份列表"""
        backup_manager = ConfigBackup(self.backup_dir)
        backups = backup_manager.get_backup_list()
        
        self.assertIsInstance(backups, list)


class TestConfigDeployer(unittest.TestCase):
    """配置下发器测试"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = DeployTask(
            id='test-task',
            name='Test Deploy',
            target_type='device',
            targets=['192.168.1.1'],
            config_type='running',
            config_content='interface GigabitEthernet0/0'
        )
        
        self.assertEqual(task.id, 'test-task')
        self.assertEqual(task.target_type, 'device')
        self.assertEqual(len(task.targets), 1)
        self.assertTrue(task.backup)
    
    def test_validate_config_syntax(self):
        """测试配置语法验证"""
        deployer = ConfigDeployer()
        
        # 有效配置
        valid_config = '''
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
'''
        result = deployer.validate_config_syntax(valid_config)
        self.assertTrue(result['valid'])
        
        # 无效IP
        invalid_config = '''
interface GigabitEthernet0/0
 ip address 192.168.1.256 255.255.255.0
'''
        result = deployer.validate_config_syntax(invalid_config)
        self.assertFalse(result['valid'])
        self.assertTrue(len(result['errors']) > 0)


class TestConfigDiff(unittest.TestCase):
    """配置差异测试"""
    
    def test_generate_config_diff(self):
        """测试生成配置差异"""
        deployer = ConfigDeployer()
        
        config1 = '''
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
!
'''
        config2 = '''
interface GigabitEthernet0/0
 ip address 192.168.1.2 255.255.255.0
!
'''
        diff = deployer.generate_config_diff(config1, config2)
        
        self.assertIn('192.168.1.1', diff)
        self.assertIn('192.168.1.2', diff)


class TestDeployStatus(unittest.TestCase):
    """部署状态测试"""
    
    def test_status_values(self):
        """测试状态值"""
        self.assertEqual(DeployStatus.PENDING.value, 'pending')
        self.assertEqual(DeployStatus.RUNNING.value, 'running')
        self.assertEqual(DeployStatus.SUCCESS.value, 'success')
        self.assertEqual(DeployStatus.FAILED.value, 'failed')


class TestWindowsCollector(unittest.TestCase):
    """Windows采集器测试"""
    
    @patch('modules.collection.ssh_collector.winrm_client.winrm')
    def test_collect_system_info(self, mock_winrm):
        """测试采集系统信息"""
        mock_client = MagicMock()
        
        # 模拟PowerShell输出
        mock_result = MagicMock()
        mock_result.status_code = 0
        mock_result.std_out = '''{"ComputerName":"WIN-SERVER","Domain":"WORKGROUP","CPUName":"Intel Xeon","TotalMemoryGB":16}'''
        mock_result.std_err = ''
        
        mock_client.run_ps.return_value = mock_result
        
        config = WinRMConfig(
            host='192.168.1.1',
            username='admin',
            password='secret'
        )
        
        client = WinRMClient(config)
        client._session = mock_client
        client._connected = True
        
        collector = WindowsCollector(client)
        info = collector.collect_system_info()
        
        self.assertIn('ComputerName', info)


if __name__ == '__main__':
    unittest.main()
