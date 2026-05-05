"""文件日志读取器 - 支持文件尾部追踪、日志轮转检测、断点续读"""
import os
import re
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread, Lock
from enum import Enum

logger = logging.getLogger(__name__)


class Encoding(Enum):
    UTF8 = 'utf-8'
    GBK = 'gbk'
    GB2312 = 'gb2312'
    ASCII = 'ascii'


@dataclass
class FilePosition:
    """文件读取位置记录"""
    file_path: str
    inode: int
    line_number: int
    byte_offset: int
    last_modified: float
    checksum: str = ""


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: Optional[datetime]
    level: Optional[str]
    message: str
    source_file: str
    line_number: int
    raw: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileLogReader:
    """
    文件日志读取器
    支持功能:
    - 文件尾部追踪 (tail -f)
    - 日志文件轮转检测
    - 多编码支持 (UTF-8/GBK)
    - 正则解析
    - 行号断点续读
    """
    
    # 默认支持的编码列表，按优先级
    DEFAULT_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'ascii']
    
    # 日志轮转常见模式
    ROTATION_PATTERNS = [
        r'\.log\.\d{8}',
        r'\.log\.\d{6}',
        r'\.log\.\d{1,3}',
        r'\.log\.old',
        r'\.log\.bak',
        r'\.log\.rotation',
        r'\.log\.\d{4}-\d{2}-\d{2}',
        r'\.log\.gz$',
        r'\.log\.zip$',
    ]
    
    def __init__(
        self,
        file_path: str,
        encodings: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        position_file: Optional[str] = None,
        callback: Optional[Callable[[LogEntry], None]] = None,
    ):
        """
        初始化文件日志读取器
        
        Args:
            file_path: 日志文件路径
            encodings: 编码列表，按优先级尝试
            patterns: 正则匹配模式列表
            position_file: 位置记录文件路径
            callback: 日志条目回调函数
        """
        self.file_path = Path(file_path)
        self.encodings = encodings or self.DEFAULT_ENCODINGS
        self.patterns = patterns or []
        self.position_file = position_file
        self.callback = callback
        
        self._position: Optional[FilePosition] = None
        self._lock = Lock()
        self._running = False
        self._watcher_thread: Optional[Thread] = None
        self._last_inode: Optional[int] = None
        
        # 编译正则模式
        self._compiled_patterns: List[re.Pattern] = []
        for pattern in self.patterns:
            try:
                self._compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
    
    def _get_file_info(self, file_path: Path) -> tuple:
        """获取文件信息"""
        stat = file_path.stat()
        return stat.st_ino, stat.st_size, stat.st_mtime
    
    def _detect_encoding(self, file_path: Path) -> str:
        """检测文件编码"""
        for encoding in self.encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        return 'utf-8'
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()
    
    def _detect_rotation(self) -> bool:
        """检测日志文件是否轮转"""
        if not self.file_path.exists():
            return True
        
        current_inode, _, current_mtime = self._get_file_info(self.file_path)
        
        # 检查inode是否变化
        if self._last_inode and current_inode != self._last_inode:
            logger.info(f"File rotation detected: {self.file_path}")
            return True
        
        # 检查文件大小是否重置（变小）
        if self._position and self._position.byte_offset > 0:
            current_size = self.file_path.stat().st_size
            if current_size < self._position.byte_offset * 0.5:  # 明显变小
                logger.info(f"File size reset detected: {self.file_path}")
                return True
        
        # 检查时间戳是否回退
        if self._position and current_mtime < self._position.last_modified:
            logger.info(f"File modification time regressed: {self.file_path}")
            return True
        
        return False
    
    def _parse_line(self, line: str, line_number: int) -> LogEntry:
        """解析日志行"""
        timestamp = None
        level = None
        message = line.strip()
        
        # 尝试从模式中提取信息
        for pattern in self._compiled_patterns:
            match = pattern.match(line)
            if match:
                groups = match.groupdict()
                if 'timestamp' in groups and groups['timestamp']:
                    try:
                        timestamp = datetime.fromisoformat(groups['timestamp'])
                    except ValueError:
                        pass
                if 'level' in groups and groups['level']:
                    level = groups['level'].upper()
                if 'message' in groups:
                    message = groups['message']
                break
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source_file=str(self.file_path),
            line_number=line_number,
            raw=line,
        )
    
    def _detect_encoding_from_content(self, content: bytes) -> str:
        """从内容检测编码"""
        for encoding in self.encodings:
            try:
                content.decode(encoding)
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        return 'utf-8'
    
    def _read_file(self, start_position: int = 0) -> List[LogEntry]:
        """读取文件内容"""
        if not self.file_path.exists():
            return []
        
        entries = []
        encoding = self._detect_encoding(self.file_path)
        
        with self._lock:
            with open(self.file_path, 'r', encoding=encoding, errors='replace') as f:
                if start_position > 0:
                    f.seek(start_position)
                
                line_number = self._position.line_number if self._position else 0
                
                for line in f:
                    line_number += 1
                    if line.strip():
                        entry = self._parse_line(line, line_number)
                        entries.append(entry)
                        
                        if self.callback:
                            self.callback(entry)
                
                # 更新位置
                _, size, mtime = self._get_file_info(self.file_path)
                self._position = FilePosition(
                    file_path=str(self.file_path),
                    inode=self._get_file_info(self.file_path)[0],
                    line_number=line_number,
                    byte_offset=f.tell(),
                    last_modified=mtime,
                )
        
        return entries
    
    def read(self) -> List[LogEntry]:
        """读取文件内容（从当前位置继续）"""
        start_pos = self._position.byte_offset if self._position else 0
        return self._read_file(start_pos)
    
    def read_from_start(self) -> List[LogEntry]:
        """从文件开头读取"""
        self._position = None
        return self._read_file(0)
    
    def read_tail(self, lines: int = 100) -> List[LogEntry]:
        """读取文件最后N行"""
        if not self.file_path.exists():
            return []
        
        encoding = self._detect_encoding(self.file_path)
        entries = []
        
        with self._lock:
            with open(self.file_path, 'r', encoding=encoding, errors='replace') as f:
                # 使用tail方式读取
                f.seek(0, 2)
                file_size = f.tell()
                
                if file_size > 0:
                    # 估计行数，往回搜索
                    block_size = 8192
                    position = file_size
                    line_count = 0
                    
                    while position > 0 and line_count < lines:
                        position = max(0, position - block_size)
                        f.seek(position)
                        chunk = f.read(block_size)
                        line_count += chunk.count('\n')
                    
                    f.seek(position)
                    remaining_lines = chunk.split('\n')
                    
                    # 取最后lines行
                    if len(remaining_lines) > lines:
                        remaining_lines = remaining_lines[-lines:]
                    
                    line_number = self._position.line_number if self._position else 0
                    
                    for line in remaining_lines:
                        line_number += 1
                        if line.strip():
                            entry = self._parse_line(line, line_number)
                            entries.append(entry)
        
        return entries
    
    def start_watching(self, interval: float = 1.0):
        """启动文件监控"""
        if self._running:
            return
        
        self._running = True
        
        # 初始化位置
        if not self._position:
            self._load_position()
        
        self._watcher_thread = Thread(target=self._watch_loop, args=(interval,), daemon=True)
        self._watcher_thread.start()
        logger.info(f"Started watching file: {self.file_path}")
    
    def stop_watching(self):
        """停止文件监控"""
        self._running = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=5)
        self._save_position()
        logger.info(f"Stopped watching file: {self.file_path}")
    
    def _watch_loop(self, interval: float):
        """监控循环"""
        while self._running:
            try:
                if self._detect_rotation():
                    # 文件轮转，从头开始读
                    self._position = None
                    self._read_file(0)
                else:
                    # 继续读取新内容
                    start_pos = self._position.byte_offset if self._position else 0
                    self._read_file(start_pos)
            except Exception as e:
                logger.error(f"Error watching file {self.file_path}: {e}")
            
            time.sleep(interval)
    
    def _get_position_path(self) -> Path:
        """获取位置文件路径"""
        if self.position_file:
            return Path(self.position_file)
        
        # 默认位置：~/.itops/positions/
        home = Path.home()
        pos_dir = home / '.itops' / 'positions'
        pos_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用文件路径的hash作为文件名
        file_hash = hashlib.md5(str(self.file_path.absolute()).encode()).hexdigest()
        return pos_dir / f"{file_hash}.pos"
    
    def _load_position(self):
        """加载位置信息"""
        pos_file = self._get_position_path()
        
        if pos_file.exists():
            try:
                import json
                with open(pos_file, 'r') as f:
                    data = json.load(f)
                
                self._position = FilePosition(
                    file_path=data['file_path'],
                    inode=data['inode'],
                    line_number=data['line_number'],
                    byte_offset=data['byte_offset'],
                    last_modified=data['last_modified'],
                    checksum=data.get('checksum', ''),
                )
                logger.info(f"Loaded position from {pos_file}")
            except Exception as e:
                logger.warning(f"Failed to load position: {e}")
    
    def _save_position(self):
        """保存位置信息"""
        if not self._position:
            return
        
        pos_file = self._get_position_path()
        
        try:
            import json
            with open(pos_file, 'w') as f:
                json.dump({
                    'file_path': self._position.file_path,
                    'inode': self._position.inode,
                    'line_number': self._position.line_number,
                    'byte_offset': self._position.byte_offset,
                    'last_modified': self._position.last_modified,
                    'checksum': self._position.checksum,
                }, f)
            logger.info(f"Saved position to {pos_file}")
        except Exception as e:
            logger.error(f"Failed to save position: {e}")
    
    def get_position(self) -> Optional[FilePosition]:
        """获取当前位置"""
        return self._position
    
    def set_position(self, line_number: int = 0, byte_offset: int = 0):
        """设置位置"""
        with self._lock:
            _, _, mtime = self._get_file_info(self.file_path)
            self._position = FilePosition(
                file_path=str(self.file_path),
                inode=self._get_file_info(self.file_path)[0],
                line_number=line_number,
                byte_offset=byte_offset,
                last_modified=mtime,
            )


class MultiFileLogReader:
    """多文件日志读取器"""
    
    def __init__(
        self,
        patterns: List[str],
        encodings: Optional[List[str]] = None,
        callback: Optional[Callable[[LogEntry], None]] = None,
    ):
        """
        初始化多文件日志读取器
        
        Args:
            patterns: 文件路径模式列表 (glob或regex)
            encodings: 编码列表
            callback: 日志条目回调函数
        """
        self.patterns = patterns
        self.encodings = encodings or FileLogReader.DEFAULT_ENCODINGS
        self.callback = callback
        
        self._readers: Dict[str, FileLogReader] = {}
    
    def discover_files(self) -> List[Path]:
        """发现匹配的文件"""
        files = []
        
        for pattern in self.patterns:
            # 支持glob模式
            if '*' in pattern or '?' in pattern:
                for path in Path('/').glob(pattern):
                    if path.is_file() and str(path) not in files:
                        files.append(path)
            else:
                path = Path(pattern)
                if path.exists() and path.is_file() and str(path) not in files:
                    files.append(path)
        
        return files
    
    def read_all(self) -> List[LogEntry]:
        """读取所有文件"""
        entries = []
        files = self.discover_files()
        
        for file_path in files:
            str_path = str(file_path)
            
            if str_path not in self._readers:
                self._readers[str_path] = FileLogReader(
                    file_path=str_path,
                    encodings=self.encodings,
                    callback=self.callback,
                )
            
            reader_entries = self._readers[str_path].read()
            entries.extend(reader_entries)
        
        return entries
    
    def start_watching_all(self, interval: float = 1.0):
        """启动所有文件监控"""
        files = self.discover_files()
        
        for file_path in files:
            str_path = str(file_path)
            
            if str_path not in self._readers:
                self._readers[str_path] = FileLogReader(
                    file_path=str_path,
                    encodings=self.encodings,
                    callback=self.callback,
                )
            
            self._readers[str_path].start_watching(interval)
    
    def stop_watching_all(self):
        """停止所有文件监控"""
        for reader in self._readers.values():
            reader.stop_watching()
