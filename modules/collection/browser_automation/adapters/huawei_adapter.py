"""
华为设备Web适配器
用于华为交换机、路由器、防火墙等设备的Web管理界面
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class HuaweiDeviceAdapter(BaseDeviceAdapter):
    """
    华为设备Web适配器
    
    适用于华为交换机、路由器、防火墙等设备的Web管理界面
    """
    
    DEVICE_TYPE = "huawei"
    
    # 华为设备默认选择器
    DEFAULT_SELECTORS = {
        'username': '#username, #userName, input[name="username"]',
        'password': '#password, #pwd, input[name="password"]',
        'submit': '#loginBtn, .login-btn, #btnLogin, button[type="submit"]',
        'main_frame': '#mainFrame, #mainfram, iframe[name="mainFrame"]',
        'system_info': '.system-info, #systemInfo, .sys-info',
        'port_table': '.port-table, #portTable, table.port',
        'interface_list': '#interfaceList, .interface-list',
        'status_indicator': '.status-indicator, .status-icon'
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        """初始化华为设备适配器"""
        super().__init__(credential, browser_config)
        
        # 更新选择器
        self.credential.username_selector = credential.username_selector or self.DEFAULT_SELECTORS['username']
        self.credential.password_selector = credential.password_selector or self.DEFAULT_SELECTORS['password']
        self.credential.submit_selector = credential.submit_selector or self.DEFAULT_SELECTORS['submit']
        
        # 内部状态
        self._device_info: Dict[str, Any] = {}
        self._interface_info: List[Dict[str, Any]] = []
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集华为设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': None,
            'system_info': await self._collect_system_info(),
            'interface_info': await self._collect_interface_info(),
            'vlan_info': await self._collect_vlan_info(),
            'arp_table': await self._collect_arp_table(),
            'routing_table': await self._collect_routing_table(),
            'logs': await self._collect_logs(),
            'screenshot': await self._take_dashboard_screenshot()
        }
        
        return data
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """采集系统信息"""
        try:
            # 导航到系统信息页面
            if await self._navigate_to_page('system', 'systeminfo'):
                await asyncio.sleep(1)
                
                info = {
                    'device_name': await self._get_text_safe('div.device-name, .hostname, #hostName'),
                    'device_model': await self._get_text_safe('div.model, .device-model, #model'),
                    'serial_number': await self._get_text_safe('div.serial, #serialNo'),
                    'software_version': await self._get_text_safe('div.version, #swVersion'),
                    'uptime': await self._get_text_safe('div.uptime, #upTime'),
                    'cpu_usage': await self._get_text_safe('div.cpu, .cpu-usage'),
                    'memory_usage': await self._get_text_safe('div.memory, .mem-usage')
                }
                
                self._device_info = info
                return info
        except Exception as e:
            logger.error(f"采集系统信息失败: {e}")
        
        return {}
    
    async def _collect_interface_info(self) -> List[Dict[str, Any]]:
        """采集接口信息"""
        try:
            if await self._navigate_to_page('interface', 'interface'):
                await asyncio.sleep(1)
                
                interfaces = []
                
                # 获取接口列表
                rows = await self._driver.find_elements(
                    ElementSelector('table.interface-table tr, #interfaceTable tr', 'css')
                )
                
                for row in rows:
                    interface = {
                        'name': await self._get_cell_text(row, 0),
                        'status': await self._get_cell_text(row, 1),
                        'speed': await self._get_cell_text(row, 2),
                        'duplex': await self._get_cell_text(row, 3),
                        'vlan': await self._get_cell_text(row, 4)
                    }
                    interfaces.append(interface)
                
                self._interface_info = interfaces
                return interfaces
        except Exception as e:
            logger.error(f"采集接口信息失败: {e}")
        
        return []
    
    async def _collect_vlan_info(self) -> List[Dict[str, Any]]:
        """采集VLAN信息"""
        try:
            if await self._navigate_to_page('vlan', 'vlan'):
                await asyncio.sleep(1)
                
                vlans = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.vlan-table tr, #vlanTable tr', 'css')
                )
                
                for row in rows:
                    vlan = {
                        'id': await self._get_cell_text(row, 0),
                        'name': await self._get_cell_text(row, 1),
                        'ports': await self._get_cell_text(row, 2),
                        'status': await self._get_cell_text(row, 3)
                    }
                    vlans.append(vlan)
                
                return vlans
        except Exception as e:
            logger.error(f"采集VLAN信息失败: {e}")
        
        return []
    
    async def _collect_arp_table(self) -> List[Dict[str, Any]]:
        """采集ARP表"""
        try:
            if await self._navigate_to_page('arp', 'arpTable'):
                await asyncio.sleep(1)
                
                arp_entries = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.arp-table tr, #arpTable tr', 'css')
                )
                
                for row in rows:
                    entry = {
                        'ip_address': await self._get_cell_text(row, 0),
                        'mac_address': await self._get_cell_text(row, 1),
                        'interface': await self._get_cell_text(row, 2),
                        'type': await self._get_cell_text(row, 3),
                        'age': await self._get_cell_text(row, 4)
                    }
                    arp_entries.append(entry)
                
                return arp_entries
        except Exception as e:
            logger.error(f"采集ARP表失败: {e}")
        
        return []
    
    async def _collect_routing_table(self) -> List[Dict[str, Any]]:
        """采集路由表"""
        try:
            if await self._navigate_to_page('route', 'ipRoute'):
                await asyncio.sleep(1)
                
                routes = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.route-table tr, #routeTable tr', 'css')
                )
                
                for row in rows:
                    route = {
                        'destination': await self._get_cell_text(row, 0),
                        'mask': await self._get_cell_text(row, 1),
                        'gateway': await self._get_cell_text(row, 2),
                        'interface': await self._get_cell_text(row, 3),
                        'metric': await self._get_cell_text(row, 4),
                        'type': await self._get_cell_text(row, 5)
                    }
                    routes.append(route)
                
                return routes
        except Exception as e:
            logger.error(f"采集路由表失败: {e}")
        
        return []
    
    async def _collect_logs(self) -> List[str]:
        """采集日志"""
        try:
            if await self._navigate_to_page('log', 'syslog'):
                await asyncio.sleep(1)
                
                logs = []
                entries = await self._driver.find_elements(
                    ElementSelector('.log-entry, #logList li', 'css')
                )
                
                for entry in entries:
                    text = await entry.text_content()
                    if text:
                        logs.append(text)
                
                return logs
        except Exception as e:
            logger.error(f"采集日志失败: {e}")
        
        return []
    
    async def _navigate_to_page(self, menu_name: str, page_id: str) -> bool:
        """
        导航到指定页面
        
        Args:
            menu_name: 菜单名称
            page_id: 页面ID
        
        Returns:
            是否成功
        """
        try:
            # 尝试直接导航到页面
            base_url = self.credential.get_login_url()
            page_url = f"{base_url}/{page_id}"
            
            await self._driver.navigate(page_url)
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.debug(f"直接导航失败: {e}")
            return False
    
    async def _get_text_safe(self, selector: str) -> Optional[str]:
        """安全获取文本"""
        try:
            el = await self._driver.find_element(
                ElementSelector(selector, 'css'),
                timeout=5000
            )
            if el:
                return await el.text_content()
        except Exception:
            pass
        return None
    
    async def _get_cell_text(self, row, cell_index: int) -> Optional[str]:
        """获取表格单元格文本"""
        try:
            cells = await row.query_selector_all('td')
            if cells and len(cells) > cell_index:
                return await cells[cell_index].text_content()
        except Exception:
            pass
        return None
    
    async def _take_dashboard_screenshot(self) -> Optional[str]:
        """截取仪表盘截图"""
        try:
            if await self._navigate_to_page('dashboard', 'dashboard'):
                await asyncio.sleep(1)
                
                screenshot_dir = '/tmp/device_screenshots'
                import os
                os.makedirs(screenshot_dir, exist_ok=True)
                
                filename = f"{self.credential.host}_{self.DEVICE_TYPE}_dashboard.png"
                path = f"{screenshot_dir}/{filename}"
                
                await self._driver.screenshot(path)
                return path
        except Exception as e:
            logger.error(f"截图失败: {e}")
        
        return None
    
    async def execute_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行设备命令
        
        Args:
            command_type: 命令类型
            params: 命令参数
        
        Returns:
            执行结果
        """
        if command_type == 'reboot':
            return await self._execute_reboot()
        elif command_type == 'save_config':
            return await self._execute_save_config()
        elif command_type == 'set_port_vlan':
            return await self._execute_set_port_vlan(params)
        
        return {'success': False, 'error': 'Unknown command'}
    
    async def _execute_reboot(self) -> Dict[str, Any]:
        """执行重启"""
        try:
            # 导航到系统管理页面
            if await self._navigate_to_page('system', 'systemMgt'):
                # 点击重启按钮
                await self._driver.click(
                    ElementSelector('.reboot-btn, #rebootBtn', 'css')
                )
                await asyncio.sleep(1)
                
                # 确认重启
                await self._driver.click(
                    ElementSelector('.confirm-btn, #confirmReboot', 'css')
                )
                
                return {'success': True, 'message': 'Reboot initiated'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Navigation failed'}
    
    async def _execute_save_config(self) -> Dict[str, Any]:
        """保存配置"""
        try:
            if await self._navigate_to_page('config', 'configMgt'):
                await self._driver.click(
                    ElementSelector('.save-btn, #saveConfig', 'css')
                )
                await asyncio.sleep(2)
                
                return {'success': True, 'message': 'Configuration saved'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Navigation failed'}
    
    async def _execute_set_port_vlan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """设置端口VLAN"""
        try:
            port_name = params.get('port')
            vlan_id = params.get('vlan_id')
            
            if not port_name or not vlan_id:
                return {'success': False, 'error': 'Missing parameters'}
            
            # 导航到接口配置页面
            if await self._navigate_to_page('interface', 'interface'):
                # 找到端口并点击配置
                selector = f"tr[data-port='{port_name}'] .config-btn"
                await self._driver.click(
                    ElementSelector(selector, 'css')
                )
                await asyncio.sleep(1)
                
                # 设置VLAN
                await self._driver.fill(
                    ElementSelector('#vlanIdInput', 'css'),
                    str(vlan_id)
                )
                
                # 点击应用
                await self._driver.click(
                    ElementSelector('.apply-btn, #applyConfig', 'css')
                )
                
                return {'success': True, 'message': f'Port {port_name} VLAN set to {vlan_id}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Operation failed'}
