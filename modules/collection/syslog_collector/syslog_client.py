"""
Syslog Collector - BSD syslog (RFC 3164) collector using socket
"""

import socket
import struct
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import IntEnum

logger = logging.getLogger(__name__)


class SyslogLevel(IntEnum):
    """Syslog severity level (RFC 3164)"""
    EMERG = 0   # System is unusable
    ALERT = 1   # Action must be taken immediately
    CRIT = 2    # Critical conditions
    ERR = 3     # Error conditions
    WARNING = 4 # Warning conditions
    NOTICE = 5  # Normal but significant condition
    INFO = 6    # Informational
    DEBUG = 7   # Debug-level messages


class SyslogFacility(IntEnum):
    """Syslog facility (RFC 3164)"""
    KERN = 0
    USER = 1
    MAIL = 2
    DAEMON = 3
    AUTH = 4
    SYSLOG = 5
    LPR = 6
    NEWS = 7
    UUCP = 8
    CRON = 9
    AUTHPRIV = 10
    FTP = 11
    NTP = 12
    AUDIT = 13
    ALERT = 14
    LOCAL0 = 16
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


@dataclass
class SyslogConfig:
    """Syslog collector configuration"""
    host: str = "localhost"
    port: int = 514
    protocol: str = "UDP"  # UDP or TCP
    timeout: float = 5.0
    buffer_size: int = 4096


@dataclass
class SyslogMessage:
    """Parsed syslog message (BSD format, RFC 3164)"""
    raw: str
    timestamp: Optional[str] = None
    hostname: Optional[str] = None
    tag: Optional[str] = None
    content: Optional[str] = None
    level: Optional[int] = None
    facility: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "timestamp": self.timestamp,
            "hostname": self.hostname,
            "tag": self.tag,
            "content": self.content,
            "level": self.level,
            "facility": self.facility,
        }


class SyslogCollector:
    """
    Syslog collector using socket connection.
    Supports BSD syslog format (RFC 3164).
    """
    
    # BSD syslog format pattern (RFC 3164)
    # <priority> is optional and not always present in BSD format
    # Format: <month> <day> <time> <hostname> <tag>: <message>
    BSD_PATTERN = r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?):\s*(.*)$'
    
    def __init__(self, config: Optional[SyslogConfig] = None):
        self.config = config or SyslogConfig()
        self._socket: Optional[socket.socket] = None
        self._connected: bool = False
    
    def connect(self) -> bool:
        """Establish connection to syslog server"""
        if self._connected:
            logger.warning("Already connected")
            return True
        
        try:
            if self.config.protocol.upper() == "UDP":
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            self._socket.settimeout(self.config.timeout)
            
            if self.config.protocol.upper() == "TCP":
                self._socket.connect((self.config.host, self.config.port))
            
            self._connected = True
            logger.info(f"Connected to {self.config.host}:{self.config.port} ({self.config.protocol})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.host}:{self.config.port}: {e}")
            self._connected = False
            return False
    
    def close(self):
        """Close the connection"""
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            finally:
                self._socket = None
                self._connected = False
        logger.info("Syslog collector closed")
    
    def _parse_bsd_syslog(self, raw_message: str) -> SyslogMessage:
        """
        Parse BSD syslog format (RFC 3164).
        Format: <month> <day> <time> <hostname> <tag>: <message>
        Example: Jan 15 10:30:45 server01 sshd[1234]: Connection refused
        """
        import re
        
        msg = SyslogMessage(raw=raw_message)
        
        # Try to match BSD format
        match = re.match(self.BSD_PATTERN, raw_message)
        if match:
            msg.timestamp = match.group(1)
            msg.hostname = match.group(2)
            msg.tag = match.group(3)
            msg.content = match.group(4)
        else:
            # Fallback: try simpler parsing
            parts = raw_message.split(None, 4)
            if len(parts) >= 4:
                msg.timestamp = parts[0] + " " + parts[1] + " " + parts[2]
                msg.hostname = parts[3]
                if ":" in parts[4]:
                    tag_content = parts[4].split(":", 1)
                    msg.tag = tag_content[0]
                    msg.content = tag_content[1] if len(tag_content) > 1 else ""
                else:
                    msg.content = parts[4]
            else:
                msg.content = raw_message
        
        return msg
    
    def _parse_priority(self, raw: str) -> tuple:
        """Parse priority value from raw syslog message if present"""
        import re
        match = re.match(r'^<(\d+)>', raw)
        if match:
            priority = int(match.group(1))
            facility = priority >> 3
            level = priority & 0x07
            return facility, level
        return None, None
    
    def _apply_filters(self, messages: List[SyslogMessage], 
                       level_filter: Optional[List[int]] = None,
                       facility_filter: Optional[List[int]] = None,
                       message_contains: Optional[str] = None) -> List[SyslogMessage]:
        """Apply filters to syslog messages"""
        filtered = []
        
        for msg in messages:
            # Parse priority if available
            if msg.level is None:
                facility, level = self._parse_priority(msg.raw)
                msg.facility = facility
                msg.level = level
            
            # Level filter
            if level_filter and msg.level is not None:
                if msg.level not in level_filter:
                    continue
            
            # Facility filter
            if facility_filter and msg.facility is not None:
                if msg.facility not in facility_filter:
                    continue
            
            # Message contains filter
            if message_contains and message_contains.lower() not in msg.content.lower():
                continue
            
            filtered.append(msg)
        
        return filtered
    
    def tail_logs(self, count: int = 10,
                  level_filter: Optional[List[int]] = None,
                  facility_filter: Optional[List[int]] = None,
                  message_contains: Optional[str] = None) -> List[SyslogMessage]:
        """
        Tail recent syslog messages (receive latest N messages).
        
        Args:
            count: Number of recent messages to collect
            level_filter: Filter by syslog level (e.g., [SyslogLevel.ERR, SyslogLevel.WARNING, SyslogLevel.CRIT])
            facility_filter: Filter by facility
            message_contains: Filter messages containing this string (case-insensitive)
        
        Returns:
            List of SyslogMessage objects
        """
        if not self._connected:
            if not self.connect():
                return []
        
        messages = []
        
        try:
            # For UDP, we continuously receive until we have enough messages
            # or timeout occurs
            if self.config.protocol.upper() == "UDP":
                end_time = time.time() + self.config.timeout
                while len(messages) < count * 2:  # Receive more to filter
                    if time.time() > end_time:
                        break
                    try:
                        self._socket.setblocking(False)
                        try:
                            data, _ = self._socket.recvfrom(self.config.buffer_size)
                            raw = data.decode('utf-8', errors='replace').strip()
                            if raw:
                                msg = self._parse_bsd_syslog(raw)
                                messages.append(msg)
                        except BlockingIOError:
                            break
                    except Exception:
                        break
            else:
                # TCP mode
                self._socket.setblocking(False)
                try:
                    data = self._socket.recv(self.config.buffer_size * count)
                    raw = data.decode('utf-8', errors='replace').strip()
                    for line in raw.split('\n'):
                        if line.strip():
                            msg = self._parse_bsd_syslog(line)
                            messages.append(msg)
                except BlockingIOError:
                    pass
                    
        except Exception as e:
            logger.error(f"Error receiving logs: {e}")
        
        # Apply filters
        filtered = self._apply_filters(messages, level_filter, facility_filter, message_contains)
        
        # Return most recent messages up to count
        return filtered[-count:] if len(filtered) > count else filtered
    
    def collect_logs(self, recent_count: int = 100,
                     level_filter: Optional[List[int]] = None,
                     facility_filter: Optional[List[int]] = None,
                     message_contains: Optional[str] = None) -> List[SyslogMessage]:
        """
        Collect recent syslog messages with filtering.
        Gets recent N messages and returns filtered subset.
        
        Args:
            recent_count: Number of recent messages to fetch for analysis
            level_filter: Filter by syslog level (e.g., [ERR, WARNING, CRIT])
            facility_filter: Filter by facility
            message_contains: Filter messages containing this string
        
        Returns:
            List of filtered SyslogMessage objects
        """
        messages = self.tail_logs(
            count=recent_count,
            level_filter=level_filter,
            facility_filter=facility_filter,
            message_contains=message_contains
        )
        
        logger.info(f"Collected {len(messages)} filtered syslog messages")
        return messages
    
    def collect_error_logs(self, recent_count: int = 50,
                           levels: Optional[List[int]] = None) -> List[SyslogMessage]:
        """
        Convenience method to collect error/warning/critical logs.
        
        Args:
            recent_count: Number of recent messages to analyze
            levels: Custom level list, defaults to [CRIT, ERR, WARNING]
        
        Returns:
            List of SyslogMessage objects
        """
        if levels is None:
            levels = [SyslogLevel.CRIT, SyslogLevel.ERR, SyslogLevel.WARNING]
        
        return self.collect_logs(
            recent_count=recent_count,
            level_filter=levels
        )
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
