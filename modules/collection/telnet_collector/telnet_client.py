"""
Telnet Collector - 使用 socket 实现 Telnet 协议采集设备数据
"""
import socket
import time
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


@dataclass
class TelnetConfig:
    """Telnet 配置"""
    host: str
    port: int = 23
    username: str = ""
    password: str = ""
    timeout: int = 10
    terminal_type: str = "vt100"


class TelnetCollector:
    """Telnet 采集器，使用原生 socket 实现"""

    # Telnet 协议常用命令
    IAC = bytes([255])  # Interpret As Command
    DONT = bytes([254])
    DO = bytes([253])
    WONT = bytes([252])
    WILL = bytes([251])
    SB = bytes([250])   # Sub-negotiation Begin
    SE = bytes([240])   # Sub-negotiation End
    ECHO = bytes([1])
    SGA = bytes([3])    # Suppress Go Ahead
    NAWS = bytes([31])  # Window Size
    TSPEED = bytes([32])
    ENVIRON = bytes([36])
    LINEMODE = bytes([34])

    # 命令提示符正则
    PROMPT_PATTERNS = [
        rb'[\r\n][\w\-\.]+[>#]',
        rb'[\r\n][\w\-\.]+\$',
        rb'>$',
        rb'#$',
    ]

    def __init__(self, config: TelnetConfig):
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.buffer = b''
        self.connected = False
        self.logged_in = False

    def connect(self) -> bool:
        """
        建立 socket 连接
        Returns:
            bool: 连接是否成功
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))
            self.connected = True
            
            # 等待初始连接响应
            time.sleep(0.5)
            self._read_until(b'login:', timeout=2)
            
            return True
        except socket.timeout:
            self._close()
            raise TimeoutError(f"连接 {self.config.host}:{self.config.port} 超时")
        except socket.error as e:
            self._close()
            raise ConnectionError(f"连接 {self.config.host}:{self.config.port} 失败: {e}")

    def login(self) -> bool:
        """
        登录设备
        Returns:
            bool: 登录是否成功
        """
        if not self.connected:
            raise ConnectionError("未连接设备，请先调用 connect()")

        try:
            # 发送用户名
            if self.config.username:
                self._send_command(self.config.username)
                time.sleep(0.3)
                self._read_until(b'password:', timeout=3)

            # 发送密码
            if self.config.password:
                self._send_command(self.config.password)
                time.sleep(0.5)

            # 检查是否登录成功（等待提示符）
            self._read_until(self._get_prompt_pattern(), timeout=5)
            self.logged_in = True
            return True

        except Exception as e:
            raise RuntimeError(f"登录失败: {e}")

    def _send_command(self, cmd: str):
        """发送命令（不带回车）"""
        if self.socket:
            self.socket.sendall(cmd.encode('ascii'))

    def _send_line(self, cmd: str):
        """发送命令并回车"""
        self._send_command(cmd + '\r\n')

    def _read_until(self, pattern: bytes, timeout: Optional[int] = None) -> bytes:
        """
        读取数据直到匹配到 pattern 或超时
        """
        if timeout is None:
            timeout = self.config.timeout

        self.socket.settimeout(timeout)
        data = b''

        while True:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if pattern in data:
                    break
            except socket.timeout:
                break

        return data

    def _get_prompt_pattern(self) -> bytes:
        """获取命令提示符模式"""
        return rb'[\r\n][\w\-\./:]+[>#]'

    def _process_telnet_options(self, data: bytes) -> bytes:
        """
        处理 Telnet 选项协商
        """
        result = b''
        i = 0
        while i < len(data):
            if data[i] == 255 and i + 1 < len(data):  # IAC
                cmd = data[i + 1]
                if cmd in (251, 252, 253, 254):  # WILL, WONT, DO, DONT
                    if i + 2 < len(data):
                        option = data[i + 2]
                        # 对于大多数选项，回复 DONT/WONT
                        if cmd == 251:  # WILL
                            result += b'\xff\xfe' + bytes([option])  # DONT
                        elif cmd == 253:  # DO
                            result += b'\xff\xfc' + bytes([option])  # WONT
                        i += 3
                        continue
                elif cmd == 250:  # SB (sub-negotiation)
                    # 跳过子选项直到 SE
                    j = i + 2
                    while j < len(data) and not (data[j] == 255 and j + 1 < len(data) and data[j + 1] == 240):
                        j += 1
                    i = j + 2 if j + 1 < len(data) else len(data)
                    continue
            else:
                result += bytes([data[i]])
            i += 1

        return result

    def execute(self, cmd: str, timeout: Optional[int] = None) -> str:
        """
        执行命令并返回输出
        """
        if not self.logged_in:
            raise RuntimeError("未登录设备，请先调用 login()")

        # 发送命令
        self._send_line(cmd)
        
        # 等待命令执行完成
        time.sleep(0.3)
        if timeout is None:
            timeout = self.config.timeout

        # 读取输出，直到出现提示符
        output = b''
        prompt_pattern = self._get_prompt_pattern()
        
        self.socket.settimeout(timeout)
        max_reads = 100
        reads = 0
        
        while reads < max_reads:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                output += chunk
                
                # 检查是否收到提示符（命令执行完成）
                if re.search(prompt_pattern, output):
                    break
                reads += 1
            except socket.timeout:
                # 超时也退出，可能已经收到全部数据
                break

        # 处理 Telnet 选项
        output = self._process_telnet_options(output)
        
        # 清理输出，移除命令回显和提示符
        lines = output.decode('ascii', errors='ignore').split('\r\n')
        
        # 移除空行和命令本身
        cleaned_lines = []
        skip_next = False
        for line in lines:
            if skip_next:
                skip_next = False
                continue
            if line.strip() == '':
                continue
            if cmd in line and not line.strip().endswith(':') and not line.strip().endswith('?'):
                skip_next = True  # 跳过命令回显
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def collect(self) -> Dict[str, Any]:
        """
        采集设备数据
        Returns:
            dict: 采集到的数据，包含设备型号/版本、接口状态、CPU/内存
        """
        if not self.logged_in:
            raise RuntimeError("未登录设备，请先调用 login()")

        result = {
            'device_info': {},
            'interfaces': [],
            'cpu_usage': None,
            'memory_usage': None,
            'raw_data': {}
        }

        try:
            # 采集 show version
            version_output = self.execute('show version', timeout=15)
            result['raw_data']['show_version'] = version_output
            result['device_info'] = self._parse_version(version_output)

            # 采集 show interfaces
            interfaces_output = self.execute('show interfaces', timeout=15)
            result['raw_data']['show_interfaces'] = interfaces_output
            result['interfaces'] = self._parse_interfaces(interfaces_output)

            # 采集 show cpu
            cpu_output = self.execute('show cpu', timeout=10)
            result['raw_data']['show_cpu'] = cpu_output
            result['cpu_usage'] = self._parse_cpu(cpu_output)

            # 采集 show memory
            memory_output = self.execute('show memory', timeout=10)
            result['raw_data']['show_memory'] = memory_output
            result['memory_usage'] = self._parse_memory(memory_output)

        except Exception as e:
            result['error'] = str(e)

        return result

    def _parse_version(self, output: str) -> Dict[str, str]:
        """解析 show version 输出"""
        info = {}
        
        patterns = {
            'model': r'(?:Model|CPU|Device)[:\s]+([^\r\n]+)',
            'version': r'(?:Version|Software|IOS)[-:\s]+([^\r\n]+)',
            'serial': r'Serial Number[:\s]+([^\r\n]+)',
            'uptime': r'(?:Uptime|System up time)[:\s]+([^\r\n]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                info[key] = match.group(1).strip()
        
        return info

    def _parse_interfaces(self, output: str) -> List[Dict[str, str]]:
        """解析 show interfaces 输出"""
        interfaces = []
        
        # 简单的接口解析，按空行分割
        blocks = output.split('\n\n')
        for block in blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            iface = {'name': '', 'status': 'unknown', 'description': ''}
            
            # 第一行通常是接口名
            first_line = lines[0].strip()
            if first_line:
                iface['name'] = first_line.split()[0] if first_line.split() else first_line
            
            # 查找状态信息
            for line in lines:
                line_lower = line.lower()
                if 'up' in line_lower and 'line protocol' in line_lower:
                    iface['status'] = 'up'
                elif 'down' in line_lower:
                    iface['status'] = 'down'
                if 'description:' in line_lower:
                    parts = line.split('description:', 1)
                    if len(parts) > 1:
                        iface['description'] = parts[1].strip()
            
            if iface['name']:
                interfaces.append(iface)
        
        return interfaces

    def _parse_cpu(self, output: str) -> Optional[Dict[str, Any]]:
        """解析 show cpu 输出"""
        cpu_info = {}
        
        patterns = {
            'usage': r'(\d+)%\s*(?:CPU|processor|util)',
            'five_sec': r'5\s*seconds:\s*(\d+)%',
            'one_min': r'1\s*minute:\s*(\d+)%',
            'five_min': r'5\s*minutes:\s*(\d+)%',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                cpu_info[key] = match.group(1)
        
        return cpu_info if cpu_info else None

    def _parse_memory(self, output: str) -> Optional[Dict[str, Any]]:
        """解析 show memory 输出"""
        mem_info = {}
        
        patterns = {
            'total': r'Total:\s*(\d+)',
            'used': r'Used:\s*(\d+)',
            'free': r'Free:\s*(\d+)',
            'usage_percent': r'(\d+)%\s*(?:used|utilization)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                mem_info[key] = match.group(1)
        
        return mem_info if mem_info else None

    def close(self):
        """关闭连接"""
        self._close()

    def _close(self):
        """内部关闭方法"""
        self.connected = False
        self.logged_in = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self._close()


# 预设采集命令
PRESET_COMMANDS = {
    'show_version': 'show version',
    'show_interfaces': 'show interfaces',
    'show_cpu': 'show cpu',
    'show_memory': 'show memory',
}


if __name__ == '__main__':
    # 测试示例
    config = TelnetConfig(
        host='192.168.1.1',
        port=23,
        username='admin',
        password='admin',
        timeout=10
    )
    
    with TelnetCollector(config) as collector:
        try:
            collector.connect()
            collector.login()
            
            # 单条命令执行
            output = collector.execute('show version')
            print("Show Version Output:")
            print(output)
            print("-" * 50)
            
            # 采集所有数据
            data = collector.collect()
            print("Collected Data:")
            print(data)
            
        except Exception as e:
            print(f"Error: {e}")
