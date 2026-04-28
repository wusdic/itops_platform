"""
配置管理模块单元测试
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.foundation.config_manager.config import ConfigManager, create_default_config, DatabaseConfig, RedisConfig
from modules.foundation.config_manager.loader import ConfigLoader
from modules.foundation.config_manager.validator import ConfigValidator, ValidationError


class TestConfigManager:
    """配置管理器测试"""
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_content = """
app:
  host: 127.0.0.1
  port: 9000
  debug: true
  log_level: DEBUG

database:
  host: localhost
  port: 3306
  username: testuser
  password: testpass
  database: test_db
  pool_size: 5

redis:
  host: localhost
  port: 6379
  db: 1

monitor:
  snmp_timeout: 10
  collection_interval: 120
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(config_content)
            f.flush()
            yield f.name
            os.unlink(f.name)
    
    def test_load_config(self, temp_config_file):
        """测试加载配置"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        assert config.get('app.host') == '127.0.0.1'
        assert config.get('app.port') == 9000
        assert config.get('database.host') == 'localhost'
    
    def test_get_nested_value(self, temp_config_file):
        """测试获取嵌套配置"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        assert config.get('database.username') == 'testuser'
        assert config.get('database.pool_size') == 5
    
    def test_get_with_default(self, temp_config_file):
        """测试获取默认值"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        assert config.get('nonexistent.key', 'default') == 'default'
        assert config.get('app.nonexistent', 123) == 123
    
    def test_set_config(self, temp_config_file):
        """测试设置配置"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        config.set('app.debug', False)
        assert config.get('app.debug') == False
        
        config.set('app.new_key', 'new_value')
        assert config.get('app.new_key') == 'new_value'
    
    def test_get_database_config(self, temp_config_file):
        """测试获取数据库配置对象"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        db_config = config.get_database()
        assert isinstance(db_config, DatabaseConfig)
        assert db_config.host == 'localhost'
        assert db_config.port == 3306
        assert db_config.username == 'testuser'
    
    def test_get_redis_config(self, temp_config_file):
        """测试获取Redis配置对象"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        redis_config = config.get_redis()
        assert isinstance(redis_config, RedisConfig)
        assert redis_config.host == 'localhost'
        assert redis_config.port == 6379
        assert redis_config.db == 1
    
    def test_env_override(self, temp_config_file):
        """测试环境变量覆盖"""
        # 创建新的ConfigManager实例（因为单例模式）
        config = ConfigManager()
        # 清除之前的配置
        config._config = {}
        
        os.environ['ITOPS_APP_PORT'] = '8888'
        os.environ['ITOPS_DATABASE_HOST'] = 'env-host'
        
        config.load(temp_config_file)
        
        assert config.get('app.port') == 8888
        assert config.get('database.host') == 'env-host'
        
        # 清理
        del os.environ['ITOPS_APP_PORT']
        del os.environ['ITOPS_DATABASE_HOST']
    
    def test_encrypt_decrypt(self, temp_config_file):
        """测试加密解密"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        encrypted = config.encrypt_value('my-secret-password')
        assert encrypted.startswith('enc:')
        assert 'my-secret-password' not in encrypted
    
    def test_to_dict(self, temp_config_file):
        """测试导出配置字典"""
        config = ConfigManager()
        config.load(temp_config_file)
        
        config_dict = config.to_dict()
        assert 'app' in config_dict
        # 密码应该被脱敏
        assert 'database' in config_dict


class TestConfigLoader:
    """配置加载器测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        import shutil
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / 'config'
        config_dir.mkdir()
        
        # 创建默认配置
        base_config = """
app:
  name: itops
  version: 1.0
database:
  host: base-host
  port: 3306
"""
        with open(config_dir / 'default.yaml', 'w') as f:
            f.write(base_config)
        
        # 创建开发环境配置
        dev_config = """
database:
  host: dev-host
  pool_size: 5
app:
  debug: true
"""
        with open(config_dir / 'dev.yaml', 'w') as f:
            f.write(dev_config)
        
        yield temp_dir
        
        shutil.rmtree(temp_dir)
    
    def test_load_single_file(self, temp_config_dir):
        """测试加载单个文件"""
        loader = ConfigLoader()
        loader.set_base_dir(temp_config_dir)
        loader.add_path('config/default.yaml')
        config = loader.load()
        
        assert config['app']['name'] == 'itops'
    
    def test_load_multiple_files(self, temp_config_dir):
        """测试加载多个文件并合并"""
        loader = ConfigLoader()
        loader.set_base_dir(temp_config_dir)
        loader.add_path('config/default.yaml')
        loader.add_path('config/dev.yaml')
        config = loader.load()
        
        # dev配置应该覆盖base配置
        assert config['database']['host'] == 'dev-host'
        assert config['app']['debug'] == True
        # base配置应该保留
        assert config['app']['name'] == 'itops'
        assert config['database']['port'] == 3306
    
    def test_add_search_paths(self, temp_config_dir):
        """测试自动搜索路径"""
        loader = ConfigLoader()
        loader.set_base_dir(temp_config_dir)
        loader.set_env('dev')
        loader.add_search_paths()
        config = loader.load()
        
        assert config['database']['host'] == 'dev-host'
        assert config['app']['name'] == 'itops'


class TestConfigValidator:
    """配置验证器测试"""
    
    def test_required(self):
        """测试必填验证"""
        validator = ConfigValidator()
        validator.required('name')
        validator.required('email', '邮箱必填')
        
        # 测试缺少必填项时的错误提示
        validator2 = ConfigValidator()
        validator2.required('name')
        assert len(validator2.get_errors()) == 0  # 初始化时没有错误
        
        with pytest.raises(ValidationError):
            validator2.validate({})
        
        # 测试正常情况
        validator3 = ConfigValidator()
        validator3.required('name')
        validator3.required('email', '邮箱必填')
        config = {'name': 'test', 'email': 'test@example.com'}
        assert validator3.validate(config) == True
    
    def test_range(self):
        """测试范围验证"""
        validator = ConfigValidator()
        validator.range('port', 1, 65535)
        
        # 应该通过
        validator.validate({'port': 8080})
        
        # 应该失败
        with pytest.raises(ValidationError):
            validator.validate({'port': 70000})
    
    def test_pattern(self):
        """测试正则验证"""
        validator = ConfigValidator()
        validator.pattern('ip', r'^[\d.]+$')
        
        assert validator.validate({'ip': '192.168.1.1'}) == True
        
        with pytest.raises(ValidationError):
            validator.validate({'ip': 'invalid-ip'})
    
    def test_in_list(self):
        """测试枚举验证"""
        validator = ConfigValidator()
        validator.in_list('env', ['dev', 'test', 'prod'])
        
        assert validator.validate({'env': 'dev'}) == True
        
        with pytest.raises(ValidationError):
            validator.validate({'env': 'invalid'})
    
    def test_custom_validator(self):
        """测试自定义验证"""
        validator = ConfigValidator()
        validator.custom('port', lambda v: v is None or (v > 0 and v < 65536))
        
        assert validator.validate({'port': 8080}) == True
        assert validator.validate({'port': None}) == True  # None应该通过
        
        with pytest.raises(ValidationError):
            validator.validate({'port': -1})


class TestCreateDefaultConfig:
    """创建默认配置测试"""
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            path = create_default_config(config_path)
            assert Path(path).exists()
            
            # 验证配置可以被加载
            config = ConfigManager()
            config.load(path)
            assert config.get('app.port') == 8080
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])