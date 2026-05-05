"""
绿盟设备Web适配器
用于绿盟防火墙、IDS、IPS、WAF等设备的Web管理界面
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class NSFOCUSDeviceAdapter(BaseDeviceAdapter):
    """
    绿盟设备Web适配器
    
    适用于绿盟防火墙、IDS、IPS、WAF等设备的Web管理界面
    """
    
    DEVICE_TYPE = "nsfOCUS"
    
    # 绿盟设备默认选择器
    DEFAULT_SELECTORS = {
        # 登录页面
        'username': '#userName, #username, input[name="username"], .login-username',
        'password': '#passWord, #password, input[name="password"], .login-password',
        'submit': '#loginBtn, .login-btn, #submit, button[type="submit"]',
        
        # 框架
        'main_frame': '#mainFrame, #mainIframe, iframe[name="mainFrame"]',
        'left_menu': '#leftMenu, .menu-left, .sidebar',
        
        # 系统信息
        'system_dashboard': '.sys-dashboard, #sysDashboard, .dashboard',
        'device_name': '.hostname, #hostName, .device-name',
        'device_model': '.product-model, #productModel',
        'serial_number': '#serialNo, .serial-number',
        'software_version': '#softVersion, .version-info',
        'uptime': '#runTime, .uptime, .run-time',
        
        # 资源使用
        'cpu_usage': '#cpuUsage, .cpu-usage, .cpu-info',
        'mem_usage': '#memUsage, .mem-usage, .mem-info',
        'disk_usage': '#diskUsage, .disk-usage',
        'bandwidth': '#bandwidth, .bandwidth-usage',
        
        # 防火墙策略
        'policy_list': '#policyList, .policy-list, .rule-list',
        'policy_table': '.policy-table, #policyTable, table.rule-table',
        'policy_id': 'td:nth-child(1)',
        'policy_name': 'td:nth-child(2), .rule-name',
        'policy_src': 'td:nth-child(3), .src-zone',
        'policy_dst': 'td:nth-child(4), .dst-zone',
        'policy_service': 'td:nth-child(5), .service-type',
        'policy_action': 'td:nth-child(6), .action-type',
        
        # 攻击日志
        'attack_table': '#attackTable, .attack-list, table.attack-table',
        'attack_time': '.attack-time, #attackTime',
        'attack_type': '.attack-type, #attackType',
        'attack_src': '.attack-src, #srcIP',
        'attack_dst': '.attack-dst, #dstIP',
        'attack_level': '.attack-level, #attackLevel',
        
        # 网络接口
        'interface_table': '#interfaceTable, .interface-list, table.interface-table',
        'interface_name': '.if-name, #ifName',
        'interface_ip': '.if-ip, #ifIP',
        'interface_mask': '.if-mask, #ifMask',
        'interface_status': '.if-status, #ifStatus',
        
        # 认证验证码
        'verify_code': '#verifyCode, #checkCode, input[name="verifyCode"]',
        'verify_img': '#verifyCodeImg, #checkCodeImg, img.verify',
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        """初始化绿盟设备适配器"""
        super().__init__(credential, browser_config)
        
        # 更新选择器
        self.credential.username_selector = credential.username_selector or self.DEFAULT_SELECTORS['username']
        self.credential.password_selector = credential.password_selector or self.DEFAULT_SELECTORS['password']
        self.credential.submit_selector = credential.submit_selector or self.DEFAULT_SELECTORS['submit']
        
        # 内部状态
        self._device_info: Dict[str, Any] = {}
        self._policies: List[Dict[str, Any]] = []
        self._attacks: List[Dict[str, Any]] = []
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集绿盟设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': datetime.now().isoformat(),
            'system_info': await self._collect_system_info(),
            'resource_usage': await self._collect_resource_usage(),
            'interface_info': await self._collect_interface_info(),
            'policies': await self._collect_policies(),
            'attack_logs': await self._collect_attack_logs(),
            'screenshot': await self._take_dashboard_screenshot()
        }
        
        return data
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """采集系统信息"""
        try:
            if await self._navigate_to_page('monitor', 'system'):
                await asyncio.sleep(1)
                
                info = {
                    'device_name': await self._get_text_safe('.hostname, #hostName'),
                    'device_model': await self._get_text_safe('.product-model, #productModel'),
                    'software_version': await self._get_text_safe('#softVersion, .version-info'),
                    'serial_number': await self._get_text_safe('#serialNo'),
                    'uptime': await self._get_text_safe('#runTime'),
                    'last_update': await self._get_text_safe('.last-update, #lastUpdate'),
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
                    'cpu_usage': await self._get_text_safe('#cpuUsage, .cpu-usage'),
                    'cpu_count': await self._get_text_safe('.cpu-count, #cpuCount'),
                    'memory_usage': await self._get_text_safe('#memUsage, .mem-usage'),
                    'memory_total': await self._get_text_safe('.mem-total, #memTotal'),
                    'disk_usage': await self._get_text_safe('#diskUsage, .disk-usage'),
                    'disk_total': await self._get_text_safe('.disk-total, #diskTotal'),
                    'session_count': await self._get_text_safe('.session-count, #sessionCount'),
                    'session_max': await self._get_text_safe('.session-max, #sessionMax'),
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
                        'rx_bytes': await self._get_cell_text(row, 5),
                        'tx_bytes': await self._get_cell_text(row, 6)
                    }
                    interfaces.append(interface)
                
                return interfaces
        except Exception as e:
            logger.error(f"采集接口信息失败: {e}")
        
        return []
    
    async def _collect_policies(self) -> List[Dict[str, Any]]:
        """采集防火墙策略"""
        try:
            if await self._navigate_to_page('policy', 'list'):
                await asyncio.sleep(1)
                
                policies = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.rule-table tr, #policyTable tr', 'css')
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
                        'status': await self._get_cell_text(row, 9),
                        'hits': await self._get_cell_text(row, 10)
                    }
                    policies.append(policy)
                
                self._policies = policies
                return policies
        except Exception as e:
            logger.error(f"采集策略信息失败: {e}")
        
        return []
    
    async def _collect_attack_logs(self) -> List[Dict[str, Any]]:
        """采集攻击日志"""
        try:
            if await self._navigate_to_page('log', 'attack'):
                await asyncio.sleep(1)
                
                attacks = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.attack-table tr, #attackTable tr', 'css')
                )
                
                for row in rows[1:]:
                    attack = {
                        'time': await self._get_cell_text(row, 0),
                        'type': await self._get_cell_text(row, 1),
                        'level': await self._get_cell_text(row, 2),
                        'source_ip': await self._get_cell_text(row, 3),
                        'source_port': await self._get_cell_text(row, 4),
                        'dest_ip': await self._get_cell_text(row, 5),
                        'dest_port': await self._get_cell_text(row, 6),
                        'action': await self._get_cell_text(row, 7),
                        'detail': await self._get_cell_text(row, 8)
                    }
                    attacks.append(attack)
                
                self._attacks = attacks
                return attacks
        except Exception as e:
            logger.error(f"采集攻击日志失败: {e}")
        
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
            # 绿盟设备URL格式
            url_pattern = f"/{module}/{page}.html"
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
            if not await self._navigate_to_page('policy', 'add'):
                return False
            
            await asyncio.sleep(0.5)
            
            # 填写基本信息
            if 'name' in policy:
                await self._driver.fill(ElementSelector('#ruleName', 'css'), policy['name'])
            
            # 配置源区域
            if 'src_zone' in policy:
                await self._driver.select_option(ElementSelector('#srcZone', 'css'), policy['src_zone'])
            
            if 'src_addr' in policy:
                await self._driver.fill(ElementSelector('#srcAddr', 'css'), policy['src_addr'])
            
            # 配置目的区域
            if 'dst_zone' in policy:
                await self._driver.select_option(ElementSelector('#dstZone', 'css'), policy['dst_zone'])
            
            if 'dst_addr' in policy:
                await self._driver.fill(ElementSelector('#dstAddr', 'css'), policy['dst_addr'])
            
            # 配置服务
            if 'service' in policy:
                await self._driver.fill(ElementSelector('#service', 'css'), policy['service'])
            
            # 配置动作
            if 'action' in policy:
                action_map = {'permit': '1', 'deny': '0'}
                await self._driver.select_option(
                    ElementSelector('#action', 'css'), 
                    action_map.get(policy['action'], '1')
                )
            
            # 提交保存
            await self._driver.click(ElementSelector('#btnSubmit, .btn-submit', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return False
    
    async def enable_policy(self, policy_id: str) -> bool:
        """启用策略"""
        return await self._set_policy_status(policy_id, True)
    
    async def disable_policy(self, policy_id: str) -> bool:
        """禁用策略"""
        return await self._set_policy_status(policy_id, False)
    
    async def _set_policy_status(self, policy_id: str, enable: bool) -> bool:
        """设置策略状态"""
        try:
            if not await self._navigate_to_page('policy', 'list'):
                return False
            
            # 查找策略行
            checkbox = await self._driver.find_element(
                ElementSelector(f'input[value="{policy_id}"]', 'css')
            )
            if not checkbox:
                return False
            
            await checkbox.click()
            await asyncio.sleep(0.3)
            
            # 点击启用/禁用按钮
            btn_id = 'btnEnable' if enable else 'btnDisable'
            await self._driver.click(ElementSelector(f'#{btn_id}, .{btn_id}', 'css'))
            await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"设置策略状态失败: {e}")
            return False
    
    async def export_attack_logs(self, start_time: str = None, end_time: str = None) -> Optional[bytes]:
        """
        导出攻击日志
        
        Args:
            start_time: 开始时间 (YYYY-MM-DD HH:MM:SS)
            end_time: 结束时间 (YYYY-MM-DD HH:MM:SS)
        
        Returns:
            日志内容
        """
        try:
            if not await self._navigate_to_page('log', 'attack'):
                return None
            
            # 设置时间范围
            if start_time:
                await self._driver.fill(ElementSelector('#startTime', 'css'), start_time)
            if end_time:
                await self._driver.fill(ElementSelector('#endTime', 'css'), end_time)
            
            # 点击查询
            await self._driver.click(ElementSelector('#btnQuery, .btn-query', 'css'))
            await asyncio.sleep(2)
            
            # 导出
            await self._driver.click(ElementSelector('#btnExport, .btn-export', 'css'))
            await asyncio.sleep(2)
            
            download_path = await self._driver.get_download_path()
            if download_path:
                with open(download_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"导出攻击日志失败: {e}")
        
        return None
    
    async def get_threat_summary(self) -> Dict[str, Any]:
        """获取威胁摘要"""
        try:
            if not await self._navigate_to_page('dashboard', 'threat'):
                return {}
            
            await asyncio.sleep(1)
            
            return {
                'total_attacks': await self._get_text_safe('.total-attacks, #totalAttack'),
                'high_level': await self._get_text_safe('.high-level, #highLevel'),
                'medium_level': await self._get_text_safe('.medium-level, #mediumLevel'),
                'low_level': await self._get_text_safe('.low-level, #lowLevel'),
                'blocked': await self._get_text_safe('.blocked, #blocked'),
                'allowed': await self._get_text_safe('.allowed, #allowed'),
                'top_attack_type': await self._get_text_safe('.top-type, #topType'),
            }
        except Exception as e:
            logger.error(f"获取威胁摘要失败: {e}")
            return {'online': False}
    
    async def backup_config(self) -> Optional[bytes]:
        """备份设备配置"""
        try:
            if not await self._navigate_to_page('system', 'backup'):
                return None
            
            # 点击备份按钮
            await self._driver.click(ElementSelector('#btnBackup, .btn-backup', 'css'))
            await asyncio.sleep(3)
            
            download_path = await self._driver.get_download_path()
            if download_path:
                with open(download_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"备份配置失败: {e}")
        
        return None

# 向后兼容别名
NSFOCUSAdapter = NSFOCUSDeviceAdapter
__all__ = ['NSFOCUSDeviceAdapter', 'NSFOCUSAdapter']
