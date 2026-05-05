"""
Linux系统信息采集器
"""

import logging
import re
from typing import Any, Dict, List, Optional

from ..ssh_client import SSHClient, SSHConfig

logger = logging.getLogger(__name__)


class LinuxCollector:
    """
    Linux系统信息采集器
    
    支持主流Linux发行版的系统信息采集
    """
    
    def __init__(self, client: SSHClient):
        """
        初始化采集器
        
        Args:
            client: SSH客户端
        """
        self._client = client
        self._distro: Optional[str] = None
    
    def detect_distro(self) -> str:
        """
        检测Linux发行版
        
        Returns:
            发行版名称 (centos, ubuntu, debian, redhat, kylin, etc)
        """
        _, os_release, _ = self._client.execute('cat /etc/os-release')
        
        if 'centos' in os_release.lower():
            self._distro = 'centos'
        elif 'ubuntu' in os_release.lower():
            self._distro = 'ubuntu'
        elif 'debian' in os_release.lower():
            self._distro = 'debian'
        elif 'red hat' in os_release.lower():
            self._distro = 'redhat'
        elif 'kylin' in os_release.lower() or 'kylin' in os_release.lower():
            self._distro = 'kylin'
        elif 'anolis' in os_release.lower():
            self._distro = 'anolis'
        elif 'uos' in os_release.lower():
            self._distro = 'uos'
        else:
            self._distro = 'unknown'
        
        logger.debug(f"检测到发行版: {self._distro}")
        return self._distro
    
    def collect_system_info(self) -> Dict[str, Any]:
        """
        采集系统信息
        
        Returns:
            系统信息字典
        """
        info = {}
        
        # 主机名
        _, hostname, _ = self._client.execute('hostname')
        info['hostname'] = hostname.strip()
        
        # 内核版本
        _, kernel, _ = self._client.execute('uname -r')
        info['kernel'] = kernel.strip()
        
        # 操作系统版本
        _, os_info, _ = self._client.execute('cat /etc/os-release | grep PRETTY_NAME')
        match = re.search(r'PRETTY_NAME="([^"]+)"', os_info)
        info['os_name'] = match.group(1) if match else 'Unknown'
        
        # 运行时间
        _, uptime, _ = self._client.execute('uptime -p 2>/dev/null || uptime')
        info['uptime'] = uptime.strip()
        
        # 当前运行级别
        _, runlevel, _ = self._client.execute('runlevel')
        info['runlevel'] = runlevel.strip()
        
        return info
    
    def collect_cpu_info(self) -> Dict[str, Any]:
        """
        采集CPU信息
        
        Returns:
            CPU信息字典
        """
        info = {}
        
        # CPU型号
        _, cpu_model, _ = self._client.execute(
            "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d':' -f2"
        )
        info['model'] = cpu_model.strip()
        
        # CPU核心数
        _, cpu_cores, _ = self._client.execute('nproc')
        info['cores'] = int(cpu_cores.strip()) if cpu_cores.strip().isdigit() else 0
        
        # CPU使用率
        _, cpu_usage, _ = self._client.execute(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"
        )
        info['usage'] = float(cpu_usage.strip().replace('%us', '')) if cpu_usage.strip() else 0
        
        # CPU负载
        _, load_avg, _ = self._client.execute('cat /proc/loadavg')
        load_parts = load_avg.strip().split()
        info['load_avg_1m'] = float(load_parts[0]) if len(load_parts) > 0 else 0
        info['load_avg_5m'] = float(load_parts[1]) if len(load_parts) > 1 else 0
        info['load_avg_15m'] = float(load_parts[2]) if len(load_parts) > 2 else 0
        
        return info
    
    def collect_memory_info(self) -> Dict[str, Any]:
        """
        采集内存信息
        
        Returns:
            内存信息字典
        """
        info = {}
        
        # 获取内存信息
        _, meminfo, _ = self._client.execute('cat /proc/meminfo')
        
        def get_mem_value(key: str) -> int:
            match = re.search(rf'{key}:\s+(\d+)\s+kB', meminfo)
            return int(match.group(1)) if match else 0
        
        mem_total = get_mem_value('MemTotal')
        mem_free = get_mem_value('MemFree')
        mem_available = get_mem_value('MemAvailable') or mem_free
        buffers = get_mem_value('Buffers')
        cached = get_mem_value('Cached')
        
        info['total_mb'] = round(mem_total / 1024, 2)
        info['free_mb'] = round(mem_free / 1024, 2)
        info['available_mb'] = round(mem_available / 1024, 2)
        info['used_mb'] = round((mem_total - mem_available) / 1024, 2)
        info['usage_percent'] = round((mem_total - mem_available) / mem_total * 100, 2) if mem_total else 0
        info['buffers_mb'] = round(buffers / 1024, 2)
        info['cached_mb'] = round(cached / 1024, 2)
        
        # Swap信息
        swap_total = get_mem_value('SwapTotal')
        swap_free = get_mem_value('SwapFree')
        info['swap_total_mb'] = round(swap_total / 1024, 2)
        info['swap_free_mb'] = round(swap_free / 1024, 2)
        info['swap_used_mb'] = round((swap_total - swap_free) / 1024, 2)
        
        return info
    
    def collect_disk_info(self) -> List[Dict[str, Any]]:
        """
        采集磁盘信息
        
        Returns:
            磁盘信息列表
        """
        disks = []
        
        # 使用df获取磁盘使用情况
        _, df_output, _ = self._client.execute(
            "df -h | grep -v 'tmpfs\\|devtmpfs\\|loop\\|overlay' | tail -n +2"
        )
        
        for line in df_output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split()
            if len(parts) >= 6:
                disks.append({
                    'filesystem': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'usage_percent': parts[4].replace('%', ''),
                    'mounted_on': parts[5]
                })
        
        return disks
    
    def collect_network_info(self) -> List[Dict[str, Any]]:
        """
        采集网络接口信息
        
        Returns:
            网络接口信息列表
        """
        interfaces = []
        
        # 获取IP地址和MAC地址
        _, ip_output, _ = self._client.execute(
            "ip -br addr show | awk '{print $1, $2, $3}'"
        )
        
        for line in ip_output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                iface = {
                    'name': parts[0],
                    'state': parts[1] if len(parts) > 1 else 'unknown',
                    'ip_address': parts[2] if len(parts) > 2 else 'N/A'
                }
                
                # 获取MAC地址
                _, mac_addr, _ = self._client.execute(f"cat /sys/class/net/{parts[0]}/address")
                iface['mac_address'] = mac_addr.strip() if mac_addr else 'N/A'
                
                interfaces.append(iface)
        
        return interfaces
    
    def collect_network_stats(self) -> List[Dict[str, Any]]:
        """
        采集网络流量统计
        
        Returns:
            网络流量统计列表
        """
        stats = []
        
        _, netstat, _ = self._client.execute(
            "cat /proc/net/dev | tail -n +3"
        )
        
        for line in netstat.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) >= 2:
                iface_name = parts[0].strip()
                data = parts[1].split()
                
                if len(data) >= 10:
                    stats.append({
                        'interface': iface_name,
                        'rx_bytes': int(data[0]),
                        'rx_packets': int(data[1]),
                        'rx_errors': int(data[2]),
                        'rx_dropped': int(data[3]),
                        'tx_bytes': int(data[8]),
                        'tx_packets': int(data[9]),
                        'tx_errors': int(data[10]),
                        'tx_dropped': int(data[11])
                    })
        
        return stats
    
    def collect_process_info(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        采集进程信息
        
        Args:
            top_n: 获取前N个CPU占用最高的进程
        
        Returns:
            进程信息列表
        """
        processes = []
        
        _, ps_output, _ = self._client.execute(
            f'ps aux --sort=-%cpu | head -n {top_n + 1}'
        )
        
        lines = ps_output.strip().split('\n')
        # 跳过标题行
        for line in lines[1:]:
            if not line:
                continue
            
            parts = line.split(None, 10)
            if len(parts) >= 11:
                processes.append({
                    'user': parts[0],
                    'pid': int(parts[1]),
                    'cpu': float(parts[2]),
                    'mem': float(parts[3]),
                    'vsz': int(parts[4]),
                    'rss': int(parts[5]),
                    'tty': parts[6],
                    'stat': parts[7],
                    'start': parts[8],
                    'time': parts[9],
                    'command': parts[10]
                })
        
        return processes
    
    def collect_port_info(self) -> List[Dict[str, Any]]:
        """
        采集端口信息
        
        Returns:
            端口监听信息列表
        """
        ports = []
        
        _, ss_output, _ = self._client.execute(
            "ss -tlnp 2>/dev/null || netstat -tlnp"
        )
        
        for line in ss_output.strip().split('\n'):
            if not line or line.startswith('State') or line.startswith('LISTEN'):
                continue
            
            parts = line.split()
            if len(parts) >= 5:
                port_info = {
                    'protocol': parts[0].lower().replace('listen', '').strip(),
                    'local_address': parts[4] if len(parts) > 4 else '',
                }
                
                # 解析地址和端口
                addr_match = re.search(r'([\d.]+):(\d+)$', port_info['local_address'])
                if addr_match:
                    port_info['ip'] = addr_match.group(1)
                    port_info['port'] = addr_match.group(2)
                
                ports.append(port_info)
        
        return ports
    
    def collect_service_info(self) -> List[Dict[str, Any]]:
        """
        采集服务状态
        
        Returns:
            服务信息列表
        """
        services = []
        
        # 确定使用的初始化系统
        _, init_check, _ = self._client.execute('cat /proc/1/comm')
        
        if 'systemd' in init_check:
            # 使用systemd
            _, svc_output, _ = self._client.execute(
                'systemctl list-units --type=service --state=running --no-pager --no-legend'
            )
            
            for line in svc_output.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split()
                if parts:
                    services.append({
                        'name': parts[0].replace('.service', ''),
                        'active': 'active',
                        'state': parts[1] if len(parts) > 1 else ''
                    })
        else:
            # 使用SysV init
            _, svc_output, _ = self._client.execute('service --status-all 2>/dev/null')
            
            for line in svc_output.strip().split('\n'):
                if not line:
                    continue
                
                match = re.match(r'\s*\[([+-])\]\s+(.+)', line)
                if match:
                    services.append({
                        'name': match.group(2).strip(),
                        'active': 'active' if match.group(1) == '+' else 'inactive',
                        'state': match.group(1)
                    })
        
        return services
    
    def collect_users(self) -> List[Dict[str, Any]]:
        """
        采集用户信息
        
        Returns:
            用户信息列表
        """
        users = []
        
        _, who_output, _ = self._client.execute('who')
        
        for line in who_output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split()
            if parts:
                users.append({
                    'username': parts[0],
                    'terminal': parts[1] if len(parts) > 1 else '',
                    'login_time': ' '.join(parts[2:]) if len(parts) > 2 else ''
                })
        
        return users
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有系统信息
        
        Returns:
            完整的系统信息
        """
        # 检测发行版
        if not self._distro:
            self.detect_distro()
        
        data = {
            'host': self._client._config.host,
            'distro': self._distro,
            'timestamp': None,
            'system': self.collect_system_info(),
            'cpu': self.collect_cpu_info(),
            'memory': self.collect_memory_info(),
            'disks': self.collect_disk_info(),
            'network': self.collect_network_info(),
            'network_stats': self.collect_network_stats(),
            'processes': self.collect_process_info(),
            'ports': self.collect_port_info(),
            'services': self.collect_service_info(),
            'users': self.collect_users()
        }
        
        return data
