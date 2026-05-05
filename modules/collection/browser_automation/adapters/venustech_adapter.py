"""
启明星辰设备Web适配器
用于启明星辰防火墙、IDS、IPS等设备的Web管理界面
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class VenustechDeviceAdapter(BaseDeviceAdapter):
    """
    启明星辰设备Web适配器
    
    适用于启明星辰防火墙、IDS、IPS、UTM等设备的Web管理界面
    """
    
    DEVICE_TYPE = "venustech"
    
    # 启明星辰设备默认选择器
    DEFAULT_SELECTORS = {
        # 登录页面
        'username': '#user_name, #username, input[name="username"]',
        'password': '#pass_word, #password, input[name="password"]',
        'submit': '#login_button, #loginBtn, .submit-btn',
        
        # 框架
        'main_frame': '#main_iframe, #mainFrame, iframe[name="mainFrame"]',
        'top_frame': '#topFrame, .top-frame',
        'left_frame': '#leftFrame, .left-frame',
        
        # 系统信息
        'system_info': '.system-info, #systemInfo, .sys-info',
        'device_name': '.device-name, #deviceName, #sysname',
        'device_model': '.product-name, #productName, .model',
        'serial_number': '.serial-no, #serialNo, #sn',
        'software_version': '.soft-version, #softVersion, #version',
        'uptime': '.run-time, #runTime, .uptime',
        
        # 资源监控
        'cpu_monitor': '#cpuMonitor, .cpu-monitor, .cpu',
        'mem_monitor': '#memMonitor, .mem-monitor, .mem',
        'disk_monitor': '#diskMonitor, .disk-monitor, .disk',
        'conn_monitor': '#connMonitor, .conn-monitor',
        
        # 安全策略
        'security_policy': '#securityPolicy, .security-policy, .policy',
        'policy_table': '.policy-table, #policyTable, table.security-rule',
        'policy_name': 'td:nth-child(2)',
        'policy_src': 'td:nth-child(3)',
        'policy_dst': 'td:nth-child(4)',
        'policy_service': 'td:nth-child(5)',
        'policy_action': 'td:nth-child(6)',
        
        # 入侵检测
        'intrusion_log': '#intrusionLog, .intrusion-log, #idsLog',
        'intrusion_table': '.intrusion-table, #intrusionTable',
        'attack_name': '.attack-name, #attackName',
        'attack_time': '.attack-time, #attackTime',
        'attack_src': '.attack-src, #srcIP',
        'attack_dst': '.attack-dst, #dstIP',
        
        # 网络配置
        'network_interface': '#networkInterface, .network-interface',
        'interface_table': '.interface-table, #interfaceTable',
        
        # 告警
        'alarm_list': '#alarmList, .alarm-list, #eventList',
        'alarm_level': '.alarm-level, #alarmLevel',
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        """初始化启明星辰设备适配器"""
        super().__init__(credential, browser_config)
        
        # 更新选择器
        self.credential.username_selector = credential.username_selector or self.DEFAULT_SELECTORS['username']
        self.credential.password_selector = credential.password_selector or self.DEFAULT_SELECTORS['password']
        self.credential.submit_selector = credential.submit_selector or self.DEFAULT_SELECTORS['submit']
        
        # 内部状态
        self._device_info: Dict[str, Any] = {}
        self._policies: List[Dict[str, Any]] = []
        self._intrusion_logs: List[Dict[str, Any]] = []
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集启明星辰设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': datetime.now().isoformat(),
            'system_info': await self._collect_system_info(),
            'resource_usage': await self._collect_resource_usage(),
            'interface_info': await self._collect_interface_info(),
            'policies': await self._collect_policies(),
            'intrusion_logs': await self._collect_intrusion_logs(),
            'screenshot': await self._take_dashboard_screenshot()
        }
        
        return data
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """采集系统信息"""
        try:
            if await self._navigate_to_page('system', 'info'):
                await asyncio.sleep(1)
                
                info = {
                    'device_name': await self._get_text_safe('.device-name, #deviceName'),
                    'device_model': await self._get_text_safe('.product-name, #productName'),
                    'software_version': await self._get_text_safe('.soft-version, #softVersion'),
                    'kernel_version': await self._get_text_safe('.kernel-version, #kernelVersion'),
                    'serial_number': await self._get_text_safe('.serial-no, #serialNo'),
                    'uptime': await self._get_text_safe('.run-time, #runTime'),
                    'last_reboot': await self._get_text_safe('.last-reboot, #lastReboot'),
                }
                
                self._device_info = info
                return info
        except Exception as e:
            logger.error(f"采集系统信息失败: {e}")
        
        return {}
    
    async def _collect_resource_usage(self) -> Dict[str, Any]:
        """采集资源使用情况"""
        try:
            if await self._navigate_to_page('monitor', 'resource'):
                await asyncio.sleep(1)
                
                return {
                    'cpu_usage': await self._get_text_safe('.cpu-monitor, #cpuMonitor'),
                    'cpu_temp': await self._get_text_safe('.cpu-temp, #cpuTemp'),
                    'memory_usage': await self._get_text_safe('.mem-monitor, #memMonitor'),
                    'memory_available': await self._get_text_safe('.mem-avail, #memAvail'),
                    'disk_usage': await self._get_text_safe('.disk-monitor, #diskMonitor'),
                    'disk_available': await self._get_text_safe('.disk-avail, #diskAvail'),
                    'connection_count': await self._get_text_safe('.conn-monitor, #connMonitor'),
                    'connection_max': await self._get_text_safe('.conn-max, #connMax'),
                }
        except Exception as e:
            logger.error(f"采集资源使用情况失败: {e}")
        
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
                
                for row in rows[1:]:
                    interface = {
                        'name': await self._get_cell_text(row, 0),
                        'type': await self._get_cell_text(row, 1),
                        'ip_address': await self._get_cell_text(row, 2),
                        'netmask': await self._get_cell_text(row, 3),
                        'status': await self._get_cell_text(row, 4),
                        'rx_rate': await self._get_cell_text(row, 5),
                        'tx_rate': await self._get_cell_text(row, 6)
                    }
                    interfaces.append(interface)
                
                return interfaces
        except Exception as e:
            logger.error(f"采集接口信息失败: {e}")
        
        return []
    
    async def _collect_policies(self) -> List[Dict[str, Any]]:
        """采集安全策略"""
        try:
            if await self._navigate_to_page('policy', 'list'):
                await asyncio.sleep(1)
                
                policies = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.security-rule tr, #policyTable tr', 'css')
                )
                
                for row in rows[1:]:
                    policy = {
                        'id': await self._get_cell_text(row, 0),
                        'name': await self._get_cell_text(row, 1),
                        'source_zone': await self._get_cell_text(row, 2),
                        'dest_zone': await self._get_cell_text(row, 3),
                        'source_addr': await self._get_cell_text(row, 4),
                        'dest_addr': await self._get_cell_text(row, 5),
                        'service': await self._get_cell_text(row, 6),
                        'action': await self._get_cell_text(row, 7),
                        'schedule': await self._get_cell_text(row, 8),
                        'log': await self._get_cell_text(row, 9),
                        'status': await self._get_cell_text(row, 10),
                        'hits': await self._get_cell_text(row, 11)
                    }
                    policies.append(policy)
                
                self._policies = policies
                return policies
        except Exception as e:
            logger.error(f"采集策略信息失败: {e}")
        
        return []
    
    async def _collect_intrusion_logs(self) -> List[Dict[str, Any]]:
        """采集入侵检测日志"""
        try:
            if await self._navigate_to_page('log', 'intrusion'):
                await asyncio.sleep(1)
                
                logs = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.intrusion-table tr, #intrusionTable tr', 'css')
                )
                
                for row in rows[1:]:
                    log = {
                        'time': await self._get_cell_text(row, 0),
                        'attack_type': await self._get_cell_text(row, 1),
                        'attack_name': await self._get_cell_text(row, 2),
                        'severity': await self._get_cell_text(row, 3),
                        'source_ip': await self._get_cell_text(row, 4),
                        'source_port': await self._get_cell_text(row, 5),
                        'dest_ip': await self._get_cell_text(row, 6),
                        'dest_port': await self._get_cell_text(row, 7),
                        'action': await self._get_cell_text(row, 8),
                        'classification': await self._get_cell_text(row, 9)
                    }
                    logs.append(log)
                
                self._intrusion_logs = logs
                return logs
        except Exception as e:
            logger.error(f"采集入侵检测日志失败: {e}")
        
        return []
    
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
            # 启明星辰设备URL格式
            url_pattern = f"/{module}/{page}.htm"
            await self._driver.navigate(self.credential.get_login_url() + url_pattern)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
    
    async def create_policy(self, policy: Dict[str, Any]) -> bool:
        """
        创建安全策略
        
        Args:
            policy: 策略配置
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('policy', 'add'):
                return False
            
            await asyncio.sleep(0.5)
            
            # 填写基本信息
            if 'name' in policy:
                await self._driver.fill(ElementSelector('#rule_name', 'css'), policy['name'])
            
            # 源配置
            if 'src_zone' in policy:
                await self._driver.select_option(ElementSelector('#src_zone', 'css'), policy['src_zone'])
            
            if 'src_addr' in policy:
                await self._driver.fill(ElementSelector('#src_addr', 'css'), policy['src_addr'])
            
            # 目的配置
            if 'dst_zone' in policy:
                await self._driver.select_option(ElementSelector('#dst_zone', 'css'), policy['dst_zone'])
            
            if 'dst_addr' in policy:
                await self._driver.fill(ElementSelector('#dst_addr', 'css'), policy['dst_addr'])
            
            # 服务配置
            if 'service' in policy:
                await self._driver.fill(ElementSelector('#service', 'css'), policy['service'])
            
            # 动作配置
            if 'action' in policy:
                action_map = {'permit': '1', 'deny': '0', 'reject': '2'}
                await self._driver.select_option(
                    ElementSelector('#action', 'css'),
                    action_map.get(policy['action'], '1')
                )
            
            # 保存策略
            await self._driver.click(ElementSelector('#btn_save, .btn-save, #saveButton', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return False
    
    async def modify_policy(self, policy_id: str, updates: Dict[str, Any]) -> bool:
        """
        修改策略
        
        Args:
            policy_id: 策略ID
            updates: 更新的配置
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('policy', 'edit'):
                return False
            
            await asyncio.sleep(0.5)
            
            # 查找策略
            await self._driver.fill(ElementSelector('#policy_id', 'css'), policy_id)
            await self._driver.click(ElementSelector('#btn_search, .btn-search', 'css'))
            await asyncio.sleep(1)
            
            # 更新字段
            for key, value in updates.items():
                selector_map = {
                    'name': '#rule_name',
                    'src_addr': '#src_addr',
                    'dst_addr': '#dst_addr',
                    'service': '#service',
                    'action': '#action'
                }
                if key in selector_map:
                    await self._driver.fill(ElementSelector(selector_map[key], 'css'), str(value))
            
            # 保存
            await self._driver.click(ElementSelector('#btn_save, .btn-save', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"修改策略失败: {e}")
            return False
    
    async def delete_policy(self, policy_id: str) -> bool:
        """
        删除策略
        
        Args:
            policy_id: 策略ID
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('policy', 'list'):
                return False
            
            # 选择策略
            checkbox = await self._driver.find_element(
                ElementSelector(f'input[name="policy_ids"][value="{policy_id}"]', 'css')
            )
            if not checkbox:
                return False
            
            await checkbox.click()
            await asyncio.sleep(0.3)
            
            # 删除
            await self._driver.click(ElementSelector('#btn_delete, .btn-delete', 'css'))
            await asyncio.sleep(0.5)
            
            # 确认
            await self._driver.click(ElementSelector('.confirm-ok, #confirmOK', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            return False
    
    async def export_logs(self, log_type: str = "intrusion", 
                         start_time: str = None, end_time: str = None) -> Optional[bytes]:
        """
        导出日志
        
        Args:
            log_type: 日志类型 (intrusion, traffic, system)
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            日志内容
        """
        try:
            page_map = {
                'intrusion': 'intrusion',
                'traffic': 'traffic',
                'system': 'system'
            }
            
            if not await self._navigate_to_page('log', page_map.get(log_type, 'intrusion')):
                return None
            
            # 设置时间范围
            if start_time:
                await self._driver.fill(ElementSelector('#start_time', 'css'), start_time)
            if end_time:
                await self._driver.fill(ElementSelector('#end_time', 'css'), end_time)
            
            # 查询
            await self._driver.click(ElementSelector('#btn_query, .btn-query', 'css'))
            await asyncio.sleep(2)
            
            # 导出
            await self._driver.click(ElementSelector('#btn_export, .btn-export', 'css'))
            await asyncio.sleep(2)
            
            download_path = await self._driver.get_download_path()
            if download_path:
                with open(download_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
        
        return None
    
    async def get_defense_status(self) -> Dict[str, Any]:
        """获取防御状态"""
        try:
            if not await self._navigate_to_page('monitor', 'defense'):
                return {}
            
            await asyncio.sleep(1)
            
            return {
                'ids_status': await self._get_text_safe('.ids-status, #idsStatus'),
                'ips_status': await self._get_text_safe('.ips-status, #ipsStatus'),
                'firewall_status': await self._get_text_safe('.fw-status, #fwStatus'),
                'total_attacks_blocked': await self._get_text_safe('.blocked-count, #blockedCount'),
                'attacks_today': await self._get_text_safe('.today-attacks, #todayAttacks'),
                'top_attack': await self._get_text_safe('.top-attack, #topAttack'),
            }
        except Exception as e:
            logger.error(f"获取防御状态失败: {e}")
            return {'online': False}
    
    async def update_signature(self) -> bool:
        """更新威胁特征库"""
        try:
            if not await self._navigate_to_page('system', 'update'):
                return False
            
            # 点击更新按钮
            await self._driver.click(ElementSelector('#btn_update, .btn-update', 'css'))
            await asyncio.sleep(5)  # 等待下载和应用
            
            # 检查结果
            result = await self._get_text_safe('.update-result, #updateResult')
            return 'success' in result.lower() if result else False
        except Exception as e:
            logger.error(f"更新特征库失败: {e}")
            return False

# 向后兼容别名
VenustechAdapter = VenustechDeviceAdapter
__all__ = ['VenustechDeviceAdapter', 'VenustechAdapter']
