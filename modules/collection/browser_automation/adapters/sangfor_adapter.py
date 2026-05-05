"""
深信服设备Web适配器
用于深信服AD(应用交付)、DC(统一运维管理)、AF(防火墙)等设备的Web管理界面
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..browser_driver import BrowserDriver, BrowserConfig, ElementSelector
from .base_adapter import BaseDeviceAdapter, DeviceCredential

logger = logging.getLogger(__name__)


class SangforDeviceAdapter(BaseDeviceAdapter):
    """
    深信服设备Web适配器
    
    适用于深信服AD、DC、AF、SSL VPN等设备的Web管理界面
    """
    
    DEVICE_TYPE = "sangfor"
    
    # 深信服设备默认选择器
    DEFAULT_SELECTORS = {
        # 登录页面
        'username': '#user_name, #username, input[name="username"], .user-name-input',
        'password': '#password, input[name="password"], .password-input',
        'submit': '#login_btn, #loginBtn, button[type="submit"]',
        
        # 框架
        'main_frame': '#mainFrame, #main_iframe, iframe[name="mainFrame"]',
        'nav_frame': '#navFrame, .nav-frame, iframe.nav',
        
        # 系统信息
        'system_info': '.sys-info, #sysInfo, .system-info',
        'device_name': '.device-name, #deviceName, #hostName',
        'device_model': '.product-model, #productModel, .model-name',
        'serial_number': '.serial-no, #serialNo, #sn',
        'software_version': '.version-info, #softVersion, #version',
        'uptime': '.run-time, #runTime, .uptime',
        
        # 资源监控
        'cpu_usage': '#cpuUsage, .cpu-usage, .cpu-info',
        'mem_usage': '#memUsage, .mem-usage, .mem-info',
        'disk_usage': '#diskUsage, .disk-usage',
        'connection_count': '#connCount, .conn-count',
        
        # 负载均衡 (AD)
        'vs_list': '#vsList, .vs-list, table.vs-table',
        'vs_name': '.vs-name, #vsName',
        'vs_ip': '.vs-ip, #vsIP',
        'vs_port': '.vs-port, #vsPort',
        'vs_status': '.vs-status, #vsStatus',
        'vs_method': '.vs-method, #vsMethod',
        'rs_list': '#rsList, .rs-list, table.rs-table',
        'rs_name': '.rs-name, #rsName',
        'rs_ip': '.rs-ip, #rsIP',
        'rs_status': '.rs-status, #rsStatus',
        'rs_weight': '.rs-weight, #rsWeight',
        
        # 服务器健康检查
        'health_check': '.health-check, #healthCheck',
        'health_status': '.health-status, #healthStatus',
        
        # SSL证书
        'ssl_cert': '#certList, .cert-list, table.cert-table',
        'cert_name': '.cert-name, #certName',
        'cert_expire': '.cert-expire, #certExpire',
        'cert_status': '.cert-status, #certStatus',
        
        # 防火墙策略 (AF)
        'policy_list': '#policyList, .policy-list, table.policy-table',
        'policy_name': '.policy-name, #policyName',
        'policy_src': '.policy-src, #srcZone',
        'policy_dst': '.policy-dst, #dstZone',
        'policy_service': '.policy-service, #service',
        'policy_action': '.policy-action, #action',
        
        # 流量统计
        'traffic_stats': '#trafficStats, .traffic-stats',
        'bandwidth_in': '.bw-in, #bwIn',
        'bandwidth_out': '.bw-out, #bwOut',
        
        # 会话表
        'session_table': '#sessionTable, .session-list, table.session-table',
        'session_src': '.session-src, #srcIP',
        'session_dst': '.session-dst, #dstIP',
        'session_proto': '.session-proto, #protocol',
    }
    
    def __init__(self, credential: DeviceCredential, browser_config: BrowserConfig = None):
        """初始化深信服设备适配器"""
        super().__init__(credential, browser_config)
        
        # 更新选择器
        self.credential.username_selector = credential.username_selector or self.DEFAULT_SELECTORS['username']
        self.credential.password_selector = credential.password_selector or self.DEFAULT_SELECTORS['password']
        self.credential.submit_selector = credential.submit_selector or self.DEFAULT_SELECTORS['submit']
        
        # 内部状态
        self._device_info: Dict[str, Any] = {}
        self._vs_list: List[Dict[str, Any]] = []
        self._rs_list: List[Dict[str, Any]] = []
        self._cert_list: List[Dict[str, Any]] = []
    
    async def _collect_data(self) -> Dict[str, Any]:
        """采集深信服设备数据"""
        data = {
            'device_type': self.DEVICE_TYPE,
            'host': self.credential.host,
            'timestamp': datetime.now().isoformat(),
            'system_info': await self._collect_system_info(),
            'resource_usage': await self._collect_resource_usage(),
            'virtual_servers': await self._collect_virtual_servers(),
            'real_servers': await self._collect_real_servers(),
            'ssl_certificates': await self._collect_ssl_certs(),
            'traffic_stats': await self._collect_traffic_stats(),
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
                    'device_model': await self._get_text_safe('.product-model, #productModel'),
                    'software_version': await self._get_text_safe('.version-info, #softVersion'),
                    'serial_number': await self._get_text_safe('.serial-no, #serialNo'),
                    'uptime': await self._get_text_safe('.run-time, #runTime'),
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
                    'connection_count': await self._get_text_safe('#connCount, .conn-count'),
                    'connection_max': await self._get_text_safe('.conn-max, #connMax'),
                }
        except Exception as e:
            logger.error(f"采集资源使用情况失败: {e}")
        
        return {}
    
    async def _collect_virtual_servers(self) -> List[Dict[str, Any]]:
        """采集虚拟服务器(AD)"""
        try:
            if await self._navigate_to_page('loadbalance', 'vs'):
                await asyncio.sleep(1)
                
                vservers = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.vs-table tr, #vsList tr', 'css')
                )
                
                for row in rows[1:]:
                    vs = {
                        'name': await self._get_cell_text(row, 0),
                        'ip': await self._get_cell_text(row, 1),
                        'port': await self._get_cell_text(row, 2),
                        'method': await self._get_cell_text(row, 3),
                        'status': await self._get_cell_text(row, 4),
                        'connections': await self._get_cell_text(row, 5),
                        'throughput': await self._get_cell_text(row, 6),
                        'rs_count': await self._get_cell_text(row, 7)
                    }
                    vservers.append(vs)
                
                self._vs_list = vservers
                return vservers
        except Exception as e:
            logger.error(f"采集虚拟服务器失败: {e}")
        
        return []
    
    async def _collect_real_servers(self) -> List[Dict[str, Any]]:
        """采集真实服务器"""
        try:
            if await self._navigate_to_page('loadbalance', 'rs'):
                await asyncio.sleep(1)
                
                rservers = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.rs-table tr, #rsList tr', 'css')
                )
                
                for row in rows[1:]:
                    rs = {
                        'name': await self._get_cell_text(row, 0),
                        'ip': await self._get_cell_text(row, 1),
                        'port': await self._get_cell_text(row, 2),
                        'status': await self._get_cell_text(row, 3),
                        'weight': await self._get_cell_text(row, 4),
                        'connections': await self._get_cell_text(row, 5),
                        'response_time': await self._get_cell_text(row, 6),
                        'vs_name': await self._get_cell_text(row, 7)
                    }
                    rservers.append(rs)
                
                self._rs_list = rservers
                return rservers
        except Exception as e:
            logger.error(f"采集真实服务器失败: {e}")
        
        return []
    
    async def _collect_ssl_certs(self) -> List[Dict[str, Any]]:
        """采集SSL证书"""
        try:
            if await self._navigate_to_page('ssl', 'cert'):
                await asyncio.sleep(1)
                
                certs = []
                rows = await self._driver.find_elements(
                    ElementSelector('table.cert-table tr, #certList tr', 'css')
                )
                
                for row in rows[1:]:
                    cert = {
                        'name': await self._get_cell_text(row, 0),
                        'type': await self._get_cell_text(row, 1),
                        'issuer': await self._get_cell_text(row, 2),
                        'expire_date': await self._get_cell_text(row, 3),
                        'status': await self._get_cell_text(row, 4),
                        'domain': await self._get_cell_text(row, 5)
                    }
                    certs.append(cert)
                
                self._cert_list = certs
                return certs
        except Exception as e:
            logger.error(f"采集SSL证书失败: {e}")
        
        return []
    
    async def _collect_traffic_stats(self) -> Dict[str, Any]:
        """采集流量统计"""
        try:
            if await self._navigate_to_page('monitor', 'traffic'):
                await asyncio.sleep(1)
                
                return {
                    'bandwidth_in': await self._get_text_safe('.bw-in, #bwIn'),
                    'bandwidth_out': await self._get_text_safe('.bw-out, #bwOut'),
                    'total_in': await self._get_text_safe('.total-in, #totalIn'),
                    'total_out': await self._get_text_safe('.total-out, #totalOut'),
                    'connections': await self._get_text_safe('.conn-total, #connTotal'),
                    'requests': await self._get_text_safe('.req-total, #reqTotal'),
                }
        except Exception as e:
            logger.error(f"采集流量统计失败: {e}")
        
        return {}
    
    async def _navigate_to_page(self, module: str, page: str) -> bool:
        """导航到指定页面"""
        try:
            # 深信服设备URL格式
            url_pattern = f"/{module}/{page}.html"
            await self._driver.navigate(self.credential.get_login_url() + url_pattern)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
    
    # ==================== AD负载均衡功能 ====================
    
    async def create_virtual_server(self, vs: Dict[str, Any]) -> bool:
        """
        创建虚拟服务器
        
        Args:
            vs: 虚拟服务器配置
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('loadbalance', 'vs_add'):
                return False
            
            await asyncio.sleep(0.5)
            
            # 基本信息
            if 'name' in vs:
                await self._driver.fill(ElementSelector('#vsName', 'css'), vs['name'])
            
            if 'ip' in vs:
                await self._driver.fill(ElementSelector('#vsIP', 'css'), vs['ip'])
            
            if 'port' in vs:
                await self._driver.fill(ElementSelector('#vsPort', 'css'), str(vs['port']))
            
            # 负载均衡方法
            if 'method' in vs:
                method_map = {
                    'round_robin': 'rr',
                    'least_connection': 'lc',
                    'ip_hash': 'iphash',
                    'weighted': 'wlc'
                }
                await self._driver.select_option(
                    ElementSelector('#vsMethod', 'css'),
                    method_map.get(vs['method'], 'rr')
                )
            
            # 协议类型
            if 'protocol' in vs:
                proto_map = {'tcp': 'tcp', 'udp': 'udp', 'http': 'http', 'https': 'https'}
                await self._driver.select_option(
                    ElementSelector('#protocol', 'css'),
                    proto_map.get(vs['protocol'], 'tcp')
                )
            
            # 保存
            await self._driver.click(ElementSelector('#btnSave, .btn-save', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"创建虚拟服务器失败: {e}")
            return False
    
    async def add_real_server(self, rs: Dict[str, Any]) -> bool:
        """
        添加真实服务器到虚拟服务器
        
        Args:
            rs: 真实服务器配置
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('loadbalance', 'rs_add'):
                return False
            
            await asyncio.sleep(0.5)
            
            if 'name' in rs:
                await self._driver.fill(ElementSelector('#rsName', 'css'), rs['name'])
            
            if 'ip' in rs:
                await self._driver.fill(ElementSelector('#rsIP', 'css'), rs['ip'])
            
            if 'port' in rs:
                await self._driver.fill(ElementSelector('#rsPort', 'css'), str(rs['port']))
            
            if 'weight' in rs:
                await self._driver.fill(ElementSelector('#rsWeight', 'css'), str(rs.get('weight', 100)))
            
            if 'vs_name' in rs:
                await self._driver.select_option(
                    ElementSelector('#vsName', 'css'),
                    rs['vs_name']
                )
            
            await self._driver.click(ElementSelector('#btnSave, .btn-save', 'css'))
            await asyncio.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"添加真实服务器失败: {e}")
            return False
    
    async def enable_real_server(self, rs_ip: str) -> bool:
        """启用真实服务器"""
        return await self._set_rs_status(rs_ip, True)
    
    async def disable_real_server(self, rs_ip: str) -> bool:
        """禁用真实服务器"""
        return await self._set_rs_status(rs_ip, False)
    
    async def _set_rs_status(self, rs_ip: str, enable: bool) -> bool:
        """设置真实服务器状态"""
        try:
            if not await self._navigate_to_page('loadbalance', 'rs'):
                return False
            
            # 查找服务器行
            row = await self._driver.find_element(
                ElementSelector(f'table.rs-table tr:has-text("{rs_ip}")', 'css')
            )
            if not row:
                return False
            
            # 点击启用/禁用按钮
            btn_class = 'btn-enable' if enable else 'btn-disable'
            await self._driver.click(ElementSelector(f'.{btn_class}', 'css'))
            await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"设置真实服务器状态失败: {e}")
            return False
    
    # ==================== 证书管理 ====================
    
    async def upload_ssl_cert(self, cert_file: str, cert_name: str) -> bool:
        """
        上传SSL证书
        
        Args:
            cert_file: 证书文件路径
            cert_name: 证书名称
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('ssl', 'cert_upload'):
                return False
            
            await asyncio.sleep(0.5)
            
            # 上传证书文件
            await self._driver.upload_file(
                ElementSelector('#certFile, input[type="file"]', 'css'),
                cert_file
            )
            
            if cert_name:
                await self._driver.fill(ElementSelector('#certName', 'css'), cert_name)
            
            await self._driver.click(ElementSelector('#btnUpload, .btn-upload', 'css'))
            await asyncio.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"上传SSL证书失败: {e}")
            return False
    
    async def check_cert_expiry(self) -> List[Dict[str, Any]]:
        """检查证书过期情况"""
        await self._collect_ssl_certs()
        
        expiring = []
        for cert in self._cert_list:
            expire_date = cert.get('expire_date', '')
            if expire_date:
                # 检查是否30天内过期
                try:
                    from datetime import datetime, timedelta
                    exp_date = datetime.strptime(expire_date, '%Y-%m-%d')
                    if exp_date - datetime.now() < timedelta(days=30):
                        cert['warning'] = '即将过期'
                        expiring.append(cert)
                except:
                    pass
        
        return expiring
    
    # ==================== 健康检查 ====================
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取服务器健康状态"""
        try:
            if not await self._navigate_to_page('monitor', 'health'):
                return {}
            
            await asyncio.sleep(1)
            
            return {
                'total_rs': await self._get_text_safe('.rs-total, #rsTotal'),
                'healthy_rs': await self._get_text_safe('.rs-healthy, #rsHealthy'),
                'unhealthy_rs': await self._get_text_safe('.rs-unhealthy, #rsUnhealthy'),
                'check_failures': await self._get_text_safe('.check-fail, #checkFail'),
                'last_check': await self._get_text_safe('.last-check, #lastCheck'),
            }
        except Exception as e:
            logger.error(f"获取健康状态失败: {e}")
            return {}
    
    # ==================== 配置备份 ====================
    
    async def backup_config(self) -> Optional[bytes]:
        """备份设备配置"""
        try:
            if not await self._navigate_to_page('system', 'backup'):
                return None
            
            await self._driver.click(ElementSelector('#btnBackup, .btn-backup', 'css'))
            await asyncio.sleep(3)
            
            download_path = await self._driver.get_download_path()
            if download_path:
                with open(download_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"备份配置失败: {e}")
        
        return None
    
    async def restore_config(self, config_file: str) -> bool:
        """
        恢复设备配置
        
        Args:
            config_file: 配置文件路径
        
        Returns:
            是否成功
        """
        try:
            if not await self._navigate_to_page('system', 'restore'):
                return False
            
            await self._driver.upload_file(
                ElementSelector('#configFile, input[type="file"]', 'css'),
                config_file
            )
            
            await self._driver.click(ElementSelector('#btnRestore, .btn-restore', 'css'))
            await asyncio.sleep(5)
            
            # 确认恢复
            await self._driver.click(ElementSelector('.confirm-ok, #confirmOK', 'css'))
            
            return True
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False


# 向后兼容别名
SangforAdapter = SangforDeviceAdapter
__all__ = ['SangforDeviceAdapter', 'SangforAdapter']
