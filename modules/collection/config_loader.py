"""
设备配置加载器

负责从配置文件加载设备信息、适配器配置，并提供统一的配置访问接口
支持YAML和JSON格式配置文件
"""

import os
import re
import yaml
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# 环境变量模式
ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}|\$(\w+)')


class ConfigLoader:
    """
    配置加载器
    
    从配置文件和环境变量加载设备、适配器等配置
    支持YAML和JSON格式，自动热加载
    
    使用示例:
    >>> loader = ConfigLoader('/etc/itops/config')
    >>> devices = loader.get_devices()
    >>> adapters = loader.get_adapters()
    >>> loader.reload()  # 热重载
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录，默认为项目config目录
        """
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'config'
            )
        
        self._config_dir = Path(config_dir)
        self._devices_dir = self._config_dir / 'devices'
        
        # 配置缓存
        self._devices: List[Dict[str, Any]] = []
        self._adapters: Dict[str, Dict[str, Any]] = {}
        self._global_config: Dict[str, Any] = {}
        
        # 加载时间戳
        self._last_load: Optional[datetime] = None
        
        # 初始加载
        self.reload()
    
    def reload(self) -> None:
        """重新加载所有配置"""
        logger.info(f"开始加载配置目录: {self._config_dir}")
        
        self._load_global_config()
        self._load_adapters()
        self._load_devices()
        
        self._last_load = datetime.now()
        logger.info(f"配置加载完成: {len(self._devices)}个设备, {len(self._adapters)}个适配器")
    
    def _load_global_config(self) -> None:
        """加载全局配置"""
        global_config_path = self._config_dir / 'config.yaml'
        
        if global_config_path.exists():
            with open(global_config_path, 'r', encoding='utf-8') as f:
                self._global_config = yaml.safe_load(f) or {}
            logger.debug(f"加载全局配置: {global_config_path}")
        else:
            self._global_config = self._get_default_global_config()
    
    def _get_default_global_config(self) -> Dict[str, Any]:
        """获取默认全局配置"""
        return {
            'platform': {
                'name': 'ITOps Platform',
                'version': '1.0.0',
            },
            'collect': {
                'default_interval': 60,
                'max_concurrent': 10,
                'timeout': 30,
                'retry_times': 3,
                'retry_interval': 5,
            },
            'storage': {
                'type': 'tdengine',
                'host': 'localhost',
                'port': 6041,
                'database': 'itops',
            },
            'alert': {
                'enabled': True,
                'max_per_device': 100,
            }
        }
    
    def _load_adapters(self) -> None:
        """加载适配器配置"""
        adapter_files = [
            self._devices_dir / 'adapters.yaml',
            self._config_dir / 'adapters.yaml',
        ]
        
        self._adapters = {}
        
        for adapter_file in adapter_files:
            if adapter_file.exists():
                with open(adapter_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    adapters = data.get('adapters', {})
                    
                    # 合并适配器配置
                    for name, adapter in adapters.items():
                        adapter['config_file'] = str(adapter_file)
                        self._adapters[name] = adapter
                    
                    logger.debug(f"从{adapter_file}加载{len(adapters)}个适配器")
    
    def _load_devices(self) -> None:
        """加载设备配置"""
        device_files = []
        
        # 从devices目录加载所有yaml/json文件
        if self._devices_dir.exists():
            device_files = list(self._devices_dir.glob('*.yaml')) + \
                          list(self._devices_dir.glob('*.yml')) + \
                          list(self._devices_dir.glob('*.json'))
        
        # 也加载根目录的devices.yaml
        root_devices = self._config_dir / 'devices.yaml'
        if root_devices.exists():
            device_files.append(root_devices)
        
        self._devices = []
        
        for device_file in device_files:
            try:
                with open(device_file, 'r', encoding='utf-8') as f:
                    if device_file.suffix in ['.json']:
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)
                    
                    if data and 'devices' in data:
                        devices = data['devices']
                        for device in devices:
                            # 处理环境变量
                            device = self._resolve_env_vars(device)
                            # 添加配置来源
                            device['_config_file'] = str(device_file)
                            # 验证设备配置
                            if self._validate_device(device):
                                self._devices.append(device)
                    
                    logger.debug(f"从{device_file}加载{len(data.get('devices', []))}个设备")
                    
            except Exception as e:
                logger.error(f"加载设备配置文件{device_file}失败: {e}")
    
    def _resolve_env_vars(self, obj: Any) -> Any:
        """递归解析对象中的环境变量${VAR}或$VAR"""
        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._resolve_env_var_string(obj)
        return obj
    
    def _resolve_env_var_string(self, value: str) -> str:
        """解析字符串中的环境变量"""
        def replacer(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, match.group(0))
        
        return ENV_VAR_PATTERN.sub(replacer, value)
    
    def _validate_device(self, device: Dict[str, Any]) -> bool:
        """验证设备配置"""
        required_fields = ['name', 'ip', 'type']
        
        for field in required_fields:
            if field not in device or not device[field]:
                logger.warning(f"设备缺少必需字段'{field}': {device.get('name', 'Unknown')}")
                return False
        
        return True
    
    def get_devices(self, 
                   enabled_only: bool = False,
                   device_type: str = None,
                   vendor: str = None,
                   tag: str = None) -> List[Dict[str, Any]]:
        """
        获取设备列表
        
        Args:
            enabled_only: 只返回已启用的设备
            device_type: 按设备类型过滤 (server/network/security/container/monitor)
            vendor: 按厂商过滤
            tag: 按标签过滤 (e.g. "env:production")
            
        Returns:
            设备配置列表
        """
        devices = self._devices
        
        if enabled_only:
            devices = [d for d in devices if d.get('collect', {}).get('enabled', True)]
        
        if device_type:
            devices = [d for d in devices if d.get('type') == device_type]
        
        if vendor:
            devices = [d for d in devices if d.get('vendor') == vendor]
        
        if tag:
            key, _, value = tag.partition(':')
            devices = [d for d in devices 
                      if d.get('tags', {}).get(key) == value]
        
        return devices
    
    def get_device_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取设备"""
        for device in self._devices:
            if device.get('name') == name:
                return device
        return None
    
    def get_device_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """根据IP获取设备"""
        for device in self._devices:
            if device.get('ip') == ip:
                return device
        return None
    
    def get_adapters(self, vendor: str = None) -> Dict[str, Dict[str, Any]]:
        """
        获取适配器配置
        
        Args:
            vendor: 按厂商名过滤
            
        Returns:
            适配器配置字典
        """
        if vendor:
            return {k: v for k, v in self._adapters.items() 
                   if vendor.lower() in k.lower() or 
                      any(vendor.lower() in p.lower() for p in v.get('vendor_patterns', []))}
        return self._adapters.copy()
    
    def get_adapter_for_device(self, device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据设备配置获取匹配的适配器
        
        Args:
            device: 设备配置
            
        Returns:
            匹配的适配器配置，如果没有匹配则返回None
        """
        os_info = device.get('os', '').lower()
        vendor = device.get('vendor', '').lower()
        
        # 按优先级排序匹配
        matched_adapters = []
        
        for adapter_name, adapter in self._adapters.items():
            patterns = adapter.get('vendor_patterns', [])
            
            # 检查厂商模式匹配
            matched = False
            for pattern in patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in os_info or pattern_lower in vendor:
                    matched = True
                    break
            
            if matched:
                priority = adapter.get('priority', 50)
                matched_adapters.append((priority, adapter_name, adapter))
        
        # 返回优先级最高的匹配
        if matched_adapters:
            matched_adapters.sort(key=lambda x: x[0], reverse=True)
            return matched_adapters[0][2]
        
        # 返回默认适配器
        return self._adapters.get('network_generic') or self._adapters.get('linux_generic')
    
    def get_protocol_config(self, device: Dict[str, Any], protocol: str) -> Dict[str, Any]:
        """
        获取设备指定协议的配置
        
        Args:
            device: 设备配置
            protocol: 协议类型 (ssh/snmp/http/ipmi/winrm/kubernetes/docker)
            
        Returns:
            协议配置
        """
        # 优先级: 设备自身配置 > 适配器配置
        if protocol in device.get('credentials', {}):
            return device['credentials'][protocol]
        
        if protocol in device:
            return device[protocol]
        
        # 从适配器获取默认配置
        adapter = self.get_adapter_for_device(device)
        if adapter and protocol in adapter.get('protocols', {}):
            return adapter['protocols'][protocol]
        
        return {}
    
    def get_global_config(self, key_path: str = None) -> Any:
        """
        获取全局配置
        
        Args:
            key_path: 配置路径，支持点号分隔 (e.g. 'collect.default_interval')
            
        Returns:
            配置值
        """
        if not key_path:
            return self._global_config.copy()
        
        keys = key_path.split('.')
        value = self._global_config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def add_device(self, device: Dict[str, Any]) -> bool:
        """
        添加设备配置
        
        Args:
            device: 设备配置
            
        Returns:
            是否成功
        """
        if not self._validate_device(device):
            return False
        
        # 处理环境变量
        device = self._resolve_env_vars(device)
        
        self._devices.append(device)
        logger.info(f"添加设备: {device.get('name')}")
        return True
    
    def update_device(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        更新设备配置
        
        Args:
            name: 设备名称
            updates: 更新内容
            
        Returns:
            是否成功
        """
        for device in self._devices:
            if device.get('name') == name:
                device.update(updates)
                logger.info(f"更新设备: {name}")
                return True
        
        return False
    
    def remove_device(self, name: str) -> bool:
        """
        移除设备配置
        
        Args:
            name: 设备名称
            
        Returns:
            是否成功
        """
        for i, device in enumerate(self._devices):
            if device.get('name') == name:
                self._devices.pop(i)
                logger.info(f"移除设备: {name}")
                return True
        
        return False
    
    def save_devices(self) -> bool:
        """
        保存设备配置到文件
        
        Returns:
            是否成功
        """
        # 合并所有设备并保存
        output = {'devices': self._devices}
        
        output_file = self._devices_dir / 'devices.yaml'
        
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            logger.info(f"保存设备配置到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存设备配置失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        stats = {
            'total_devices': len(self._devices),
            'total_adapters': len(self._adapters),
            'last_load': str(self._last_load) if self._last_load else None,
            'devices_by_type': {},
            'devices_by_vendor': {},
            'devices_by_status': {},
        }
        
        for device in self._devices:
            # 按类型统计
            dev_type = device.get('type', 'unknown')
            stats['devices_by_type'][dev_type] = stats['devices_by_type'].get(dev_type, 0) + 1
            
            # 按厂商统计
            vendor = device.get('vendor', 'unknown')
            stats['devices_by_vendor'][vendor] = stats['devices_by_vendor'].get(vendor, 0) + 1
            
            # 按启用状态统计
            enabled = device.get('collect', {}).get('enabled', True)
            status = 'enabled' if enabled else 'disabled'
            stats['devices_by_status'][status] = stats['devices_by_status'].get(status, 0) + 1
        
        return stats


# 全局配置加载器实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: str = None) -> ConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    
    return _config_loader


def reload_config() -> None:
    """重新加载配置"""
    global _config_loader
    
    if _config_loader:
        _config_loader.reload()
    else:
        _config_loader = ConfigLoader()


# 便捷函数
def get_devices(**kwargs) -> List[Dict[str, Any]]:
    """获取设备列表"""
    return get_config_loader().get_devices(**kwargs)


def get_device(name: str = None, ip: str = None) -> Optional[Dict[str, Any]]:
    """获取单个设备"""
    if name:
        return get_config_loader().get_device_by_name(name)
    if ip:
        return get_config_loader().get_device_by_ip(ip)
    return None


def get_adapters(vendor: str = None) -> Dict[str, Dict[str, Any]]:
    """获取适配器配置"""
    return get_config_loader().get_adapters(vendor)


def get_adapter_for_device(device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """获取设备对应的适配器"""
    return get_config_loader().get_adapter_for_device(device)
