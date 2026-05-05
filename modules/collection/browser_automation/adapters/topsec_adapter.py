"""
天融信设备Web适配器
用于天融信防火墙、IDS、IPS、WAF等设备的Web管理界面
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class TopsecDeviceAdapter(BaseDeviceAdapter):
    """
    天融信设备Web适配器
    
    适用于天融信防火墙、IDS、IPS、WAF等设备的Web管理界面
    """
    
    DEVICE_TYPE = "topsec"
    
    # 天融信设备默认选择器
    DEFAULT_SELECTORS = {
        # 登录页面
        'username': '#userName, #username, input[name="username"]',
        'password': '#password, #pwd, input[name="password"]',
        'submit': '#loginButton, .btn-login, #btn_login',
        
        # 框架
        'main_frame': '#mainFrame, #main, iframe[name="mainFrame"]',
        'left_menu': '#leftFrame, .left-menu',
        
        # 系统信息
        'system_status': '.system-status, #sysStatus, .device-info',
        'device_name': '.device-name, #deviceName, .sys-name',
        'cpu_usage': '.cpu-usage, #cpuUsage, .cpu-info',
        'mem_usage': '.mem-usage, #memUsage, .memory-info',
        'disk_usage': '.disk-usage, #diskUsage',
        
        # 防火墙策略
        'policy_table': '#policyTable, .policy-list, table.policy-table',
        'policy_name': 'td:nth-child(2), .policy-name',
        'policy_action': 'td:nth-child(3), .policy-action',
        'policy_status': 'td:nth-child(4), .policy-status',
        
        # 告警日志
        'alert_table': '#alertTable, .alert-list, table.alert-table',
        'alert_level': '.alert-level, #alertLevel',
        'alert_time': '.alert-time, #alertTime',
        'alert_src': '.alert-src, #srcIp',
        'alert_dst': '.alert-dst, #dstIp',
        
        # 网络接口
        'interface_table': '#interfaceTable, .interface-list, table.interface-table',
        'interface_name': '.if-name, #ifName',
        'interface_ip': '.if-ip, #ifIp',
        'interface_status': '.if-status, #ifStatus',
        
        # 认证页面特定
        'captcha_input': '#captcha, #checkCode, input[name="captcha"]',
        'captcha_image': '#captchaImg, #checkCodeImg, img.captcha',
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        """初始化天融信设备适配器"""
        super().__init__(credential, browser_config)
        
        # 更新选择器
        self.credential.username_selector = credential.username_selector or self.DEFAULT_SELECTORS['username']
        self.credential.password_selector = credential.password_selector or self.DEFAULT_SELECTORS['password']
        self.credential.submit_selector = credential.submit_selector or self.DEFAULT_SELECTORS['submit']
        
        # 内部状态
        self._device_info: Dict[str, Any] = {}
        self._policies: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集天融信设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': None,
            'system_info': await self._collect_system_info(),
            'interface_info': await self._collect_interface_info(),
            'policies': await self._collect_policies(),
            'alerts': await self._collect_alerts(),
            'sessions': await self._collect_sessions(),
            'screenshot': await self._take_dashboard_screenshot()
        }
        
        return data
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """采集系统信息"""
        try:
            # 导航到系统状态页面
            if await self._navigate_to_page('system', 'status'):
                await asyncio.sleep(1)
                
                info = {
                    'device_name': await self._get_text_safe('.device-name, #deviceName'),
                    'device_model': await self._get_text_safe('.device-model, #model'),
                    'software_version': await self._get_text_safe('.version, #version'),
                    'serial_number': await self._get_text_safe('.serial, #serialNo'),
                    'uptime': await self._get_text_safe('.uptime, #uptime'),
                    'cpu_usage': await self._get_text_safe('.cpu-usage, #cpuUsage'),
                    'memory_usage': await self._get_text_safe('.memory-usage, #memUsage'),
                    'disk_usage': await self._get_text_safe('.disk-usage, #diskUsage'),
                }
                
                self._device_info = info
                return info
        except Exception as e:
            logger.error(f"采集系统信息失败: {e}")
        
        return {}
    
    async def _collect_interface_info(self) -> List[Dict[str, Any]]:
        """采集网络接口信息"""
        try:
            if await self._navigate_to_page('network', 'interface'):
                await asyncio.sleep(1)
                
                interfaces = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.interface-table tr, #interfaceTable tr', 'css')
                )
                
                for row in rows[1:]:  # 跳过表头
                    interface = {
                        'name': await self._get_cell_text(row, 0),
                        'ip_address': await self._get_cell_text(row, 1),
                        'netmask': await self._get_cell_text(row, 2),
                        'status': await self._get_cell_text(row, 3),
                        'description': await self._get_cell_text(row, 4)
                    }
                    interfaces.append(interface)
                
                return interfaces
        except Exception as e:
            logger.error(f"采集接口信息失败: {e}")
        
        return []
    
    async def _collect_policies(self) -> List[Dict[str, Any]]:
        """采集防火墙策略"""
        try:
            if await self._navigate_to_page('firewall', 'policy'):
                await asyncio.sleep(1)
                
                policies = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.policy-table tr, #policyTable tr', 'css')
                )
                
                for row in rows[1:]:  # 跳过表头
                    policy = {
                        'id': await self._get_cell_text(row, 0),
                        'name': await self._get_cell_text(row, 1),
                        'source': await self._get_cell_text(row, 2),
                        'destination': await self._get_cell_text(row, 3),
                        'service': await self._get_cell_text(row, 4),
                        'action': await self._get_cell_text(row, 5),
                        'status': await self._get_cell_text(row, 6),
                        'hit_count': await self._get_cell_text(row, 7)
                    }
                    policies.append(policy)
                
                self._policies = policies
                return policies
        except Exception as e:
            logger.error(f"采集策略信息失败: {e}")
        
        return []
    
    async def _collect_alerts(self) -> List[Dict[str, Any]]:
        """采集告警日志"""
        try:
            if await self._navigate_to_page('log', 'alert'):
                await asyncio.sleep(1)
                
                alerts = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.alert-table tr, #alertTable tr', 'css')
                )
                
                for row in rows[1:]:  # 跳过表头
                    alert = {
                        'time': await self._get_cell_text(row, 0),
                        'level': await self._get_cell_text(row, 1),
                        'source_ip': await self._get_cell_text(row, 2),
                        'dest_ip': await self._get_cell_text(row, 3),
                        'protocol': await self._get_cell_text(row, 4),
                        'description': await self._get_cell_text(row, 5),
                        'action': await self._get_cell_text(row, 6)
                    }
                    alerts.append(alert)
                
                self._alerts = alerts
                return alerts
        except Exception as e:
            logger.error(f"采集告警日志失败: {e}")
        
        return []
    
    async def _collect_sessions(self) -> Dict[str, Any]:
        """采集会话状态"""
        try:
            if await self._navigate_to_page('system', 'session'):
                await asyncio.sleep(1)
                
                return {
                    'total_sessions': await self._get_text_safe('.total-sessions, #totalSession'),
                    'new_sessions': await self._get_text_safe('.new-sessions, #newSession'),
                    'max_sessions': await self._get_text_safe('.max-sessions, #maxSession'),
                }
        except Exception as e:
            logger.error(f"采集会话信息失败: {e}")
        
        return {}
    
    async def _navigate_to_page(self, module: str, page: str) -> bool:
        """
        导航到指定页面
        
        Args:
            module: 模块名称
            page: 页面名称
        
        Returns:
            是否成功
        """
        try:
            # 天融信设备URL格式
            url_pattern = f"/{module}/{page}.do"
            await self._driver.navigate(self.credential.get_login_url() + url_pattern)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
    
    async def create_policy(self, policy: Dict[str, Any]) -> bool:
        """
        创建防火墙策略
        
        Args:
            policy: 策略配置
        
        Returns:
            是否成功
        """
        try:
            # 导航到策略页面
            if not await self._navigate_to_page('firewall', 'policy'):
                return False
            
            # 点击新建按钮
            await self._driver.click(ElementSelector('.btn-add, #btnAdd', 'css'))
            await asyncio.sleep(0.5)
            
            # 填写策略信息
            if 'name' in policy:
                await self._driver.fill(ElementSelector('#policyName', 'css'), policy['name'])
            
            if 'source' in policy:
                await self._driver.fill(ElementSelector('#srcAddress', 'css'), policy['source'])
            
            if 'destination' in policy:
                await self._driver.fill(ElementSelector('#dstAddress', 'css'), policy['destination'])
            
            if 'service' in policy:
                await self._driver.select_option(ElementSelector('#service', 'css'), policy['service'])
            
            if 'action' in policy:
                await self._driver.select_option(ElementSelector('#action', 'css'), policy['action'])
            
            # 保存策略
            await self._driver.click(ElementSelector('#btnSave, .btn-save', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return False
    
    async def delete_policy(self, policy_id: str) -> bool:
        """
        删除防火墙策略
        
        Args:
            policy_id: 策略ID
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('firewall', 'policy'):
                return False
            
            # 查找并选中策略
            checkbox = await self._driver.find_element(
                ElementSelector(f'input[value="{policy_id}"]', 'css')
            )
            if checkbox:
                await checkbox.click()
                await asyncio.sleep(0.3)
                
                # 点击删除按钮
                await self._driver.click(ElementSelector('#btnDelete, .btn-delete', 'css'))
                await asyncio.sleep(0.5)
                
                # 确认删除
                await self._driver.click(ElementSelector('.confirm-yes, #confirmYes', 'css'))
                await asyncio.sleep(1)
                
                return True
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
        
        return False
    
    async def export_config(self, config_type: str = "all") -> Optional[bytes]:
        """
        导出配置
        
        Args:
            config_type: 配置类型 (all, policy, system)
        
        Returns:
            配置内容
        """
        try:
            if not await self._navigate_to_page('system', 'config'):
                return None
            
            # 选择导出类型
            await self._driver.select_option(ElementSelector('#exportType', 'css'), config_type)
            await asyncio.sleep(0.3)
            
            # 点击导出按钮
            await self._driver.click(ElementSelector('#btnExport, .btn-export', 'css'))
            await asyncio.sleep(2)
            
            # 获取下载的文件
            download_path = await self._driver.get_download_path()
            if download_path:
                with open(download_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
        
        return None
    
    async def get_device_status(self) -> Dict[str, Any]:
        """获取设备状态概览"""
        try:
            if not await self._navigate_to_page('system', 'dashboard'):
                return {}
            
            await asyncio.sleep(1)
            
            # 获取关键指标
            status = {
                'online': await self._is_online(),
                'cpu': await self._get_text_safe('.cpu-usage, #cpuUsage'),
                'memory': await self._get_text_safe('.memory-usage, #memUsage'),
                'sessions': await self._get_text_safe('.session-count, #sessionCount'),
                'alerts': await self._get_text_safe('.alert-count, #alertCount'),
                'timestamp': asyncio.get_event_loop().time()
            }
            
            return status
        except Exception as e:
            logger.error(f"获取设备状态失败: {e}")
            return {'online': False}


# 向后兼容别名
TopSecAdapter = TopsecDeviceAdapter
__all__ = ['TopsecDeviceAdapter', 'TopSecAdapter']