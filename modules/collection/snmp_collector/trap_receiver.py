"""
SNMP Trap接收器模块
负责接收和处理SNMP Trap消息
"""

import socket
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import struct

logger = logging.getLogger(__name__)


class TrapType(Enum):
    """Trap类型"""
    SNMPv1_TRAP = 0
    SNMPv2_TRAP = 1
    SNMPv2_INFORM = 2
    SNMPv3_TRAP = 3


@dataclass
class TrapMessage:
    """Trap消息"""
    trap_type: TrapType
    source_ip: str
    source_port: int
    community: str
    enterprise_oid: str
    generic_trap: int
    specific_trap: int
    timestamp: datetime
    variables: Dict[str, Any] = field(default_factory=dict)
    raw_data: bytes = field(default_factory=b'')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trap_type": self.trap_type.name,
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "community": self.community,
            "enterprise_oid": self.enterprise_oid,
            "generic_trap": self.generic_trap,
            "specific_trap": self.specific_trap,
            "timestamp": self.timestamp.isoformat(),
            "variables": self.variables
        }


class TrapHandler:
    """Trap处理器基类"""
    
    def handle(self, trap: TrapMessage) -> bool:
        """处理Trap"""
        logger.info(f"Received trap from {trap.source_ip}: {trap.enterprise_oid}")
        return True


class TrapReceiver:
    """SNMP Trap接收器"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 162,
                 handler: TrapHandler = None):
        self.host = host
        self.port = port
        self.handler = handler or TrapHandler()
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.callbacks: List[Callable[[TrapMessage], None]] = []
    
    def start(self):
        """启动接收器"""
        if self.running:
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)
            self.running = True
            logger.info(f"Trap receiver started on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start trap receiver: {e}")
            raise
    
    def stop(self):
        """停止接收器"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        logger.info("Trap receiver stopped")
    
    def receive(self, timeout: float = 1.0) -> Optional[TrapMessage]:
        """接收Trap"""
        if not self.socket:
            return None
        
        try:
            self.socket.settimeout(timeout)
            data, addr = self.socket.recvfrom(4096)
            trap = self._parse_trap(data, addr)
            return trap
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Error receiving trap: {e}")
            return None
    
    def _parse_trap(self, data: bytes, addr: tuple) -> TrapMessage:
        """解析Trap数据"""
        # 简化实现 - 实际需要完整的SNMP协议解析
        trap = TrapMessage(
            trap_type=TrapType.SNMPv2_TRAP,
            source_ip=addr[0],
            source_port=addr[1],
            community="public",
            enterprise_oid="1.3.6.1.4.1",
            generic_trap=6,
            specific_trap=1,
            timestamp=datetime.now(),
            raw_data=data
        )
        return trap
    
    def add_callback(self, callback: Callable[[TrapMessage], None]):
        """添加回调"""
        self.callbacks.append(callback)
    
    def run(self):
        """运行接收循环"""
        self.start()
        try:
            while self.running:
                trap = self.receive(timeout=1.0)
                if trap:
                    self.handler.handle(trap)
                    for callback in self.callbacks:
                        try:
                            callback(trap)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
        finally:
            self.stop()
