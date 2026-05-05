"""
MIB解析器模块
负责MIB文件解析、OID注册表、OID解析等功能
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MIBType(Enum):
    """MIB数据类型"""
    INTEGER = "INTEGER"
    STRING = "STRING"
    OID = "OBJECT IDENTIFIER"
    IPADDRESS = "IpAddress"
    COUNTER = "Counter32"
    GAUGE = "Gauge32"
    TIMETICKS = "TimeTicks"
    OPAQUE = "Opaque"
    COUNTER64 = "Counter64"


@dataclass
class MIBNode:
    """MIB节点"""
    oid: str
    name: str
    mib_name: str
    syntax: str
    status: str = "current"
    description: str = ""
    access: str = "read-only"
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    
    def is_table(self) -> bool:
        """是否为表"""
        return bool(self.indexes)
    
    def is_columnar(self) -> bool:
        """是否为列对象"""
        return bool(self.indexes) and self.oid.endswith(".0") is False


@dataclass 
class MIBTable:
    """MIB表"""
    name: str
    oid: str
    mib_name: str
    columns: Dict[str, MIBNode] = field(default_factory=dict)
    row_index: Optional[MIBNode] = None
    
    def get_column_names(self) -> List[str]:
        """获取列名"""
        return list(self.columns.keys())


class MIBParser:
    """MIB文件解析器"""
    
    # 标准MIB对象
    STANDARD_OIDS = {
        "1.3.6.1.2.1.1.1": ("sysDescr", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.2": ("sysObjectID", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.3": ("sysUpTime", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.4": ("sysContact", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.5": ("sysName", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.6": ("sysLocation", "SNMPv2-MIB"),
        "1.3.6.1.2.1.1.7": ("sysServices", "SNMPv2-MIB"),
        "1.3.6.1.2.1.2.1": ("ifNumber", "IF-MIB"),
        "1.3.6.1.2.1.2.2": ("ifTable", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1": ("ifEntry", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.1": ("ifIndex", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.2": ("ifDescr", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.3": ("ifType", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.4": ("ifMtu", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.5": ("ifSpeed", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.8": ("ifOperStatus", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.10": ("ifInOctets", "IF-MIB"),
        "1.3.6.1.2.1.2.2.1.16": ("ifOutOctets", "IF-MIB"),
    }
    
    def __init__(self):
        self.nodes: Dict[str, MIBNode] = {}
        self.name_to_oid: Dict[str, str] = {}
        self.tables: Dict[str, MIBTable] = {}
        self._load_standard_mibs()
    
    def _load_standard_mibs(self):
        """加载标准MIB定义"""
        for oid, (name, mib) in self.STANDARD_OIDS.items():
            node = MIBNode(
                oid=oid,
                name=name,
                mib_name=mib,
                syntax="ObjectName",
                description=f"Standard {name} from {mib}"
            )
            self.nodes[oid] = node
            self.name_to_oid[name] = oid
    
    def parse_mib_file(self, file_path: str, mib_name: str) -> int:
        """解析MIB文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.parse_mib_text(content, mib_name)
        except Exception as e:
            logger.error(f"Failed to parse MIB file {file_path}: {e}")
            return 0
    
    def parse_mib_text(self, content: str, mib_name: str) -> int:
        """解析MIB文本"""
        count = 0
        # 简单解析 - 提取OBJECT IDENTIFIER定义
        pattern = r'(\w+)\s+OBJECT\s+IDENTIFIER\s*::=\s*\{\s*([^\}]+)\}'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for name, oid_str in matches:
            try:
                oid = self._parse_oid_value(oid_str)
                if oid:
                    node = MIBNode(
                        oid=oid,
                        name=name,
                        mib_name=mib_name,
                        syntax="ObjectName"
                    )
                    self.nodes[oid] = node
                    self.name_to_oid[name] = oid
                    count += 1
            except Exception as e:
                logger.debug(f"Failed to parse {name}: {e}")
        
        return count
    
    def _parse_oid_value(self, oid_str: str) -> Optional[str]:
        """解析OID值"""
        oid_str = oid_str.strip().strip('.')
        parts = oid_str.split()
        if not parts:
            return None
        return ".".join(parts)
    
    def register_node(self, oid: str, name: str, mib_name: str = "CUSTOM",
                     syntax: str = "ObjectName", description: str = "") -> MIBNode:
        """注册节点"""
        node = MIBNode(
            oid=oid,
            name=name,
            mib_name=mib_name,
            syntax=syntax,
            description=description
        )
        self.nodes[oid] = node
        self.name_to_oid[name] = oid
        return node
    
    def resolve_oid(self, oid: str) -> Optional[str]:
        """解析OID为名称"""
        # 精确匹配
        if oid in self.nodes:
            return self.nodes[oid].name
        
        # 最长前缀匹配
        best_match = None
        best_len = 0
        for node_oid in self.nodes:
            if oid.startswith(node_oid) and len(node_oid) > best_len:
                best_match = node_oid
                best_len = len(node_oid)
        
        if best_match:
            return self.nodes[best_match].name
        return None
    
    def resolve_name(self, name: str) -> Optional[str]:
        """解析名称为OID"""
        return self.name_to_oid.get(name)
    
    def get_node(self, oid: str) -> Optional[MIBNode]:
        """获取节点"""
        return self.nodes.get(oid)
    
    def get_table_columns(self, table_oid: str) -> List[MIBNode]:
        """获取表的列"""
        table = self.tables.get(table_oid)
        if table:
            return list(table.columns.values())
        return []
    
    def walk_oid_tree(self, root_oid: str) -> List[Tuple[str, MIBNode]]:
        """遍历OID树"""
        results = []
        for oid in sorted(self.nodes.keys()):
            if oid.startswith(root_oid):
                results.append((oid, self.nodes[oid]))
        return results


class MIBRegistry:
    """MIB注册表"""
    
    def __init__(self):
        self.parsers: Dict[str, MIBParser] = {}
        self._default_parser = MIBParser()
    
    def register_mib(self, mib_name: str, parser: MIBParser):
        """注册MIB解析器"""
        self.parsers[mib_name] = parser
    
    def resolve(self, oid: str, mib_name: str = None) -> Optional[str]:
        """解析OID"""
        if mib_name and mib_name in self.parsers:
            return self.parsers[mib_name].resolve_oid(oid)
        return self._default_parser.resolve_oid(oid)
    
    def resolve_name(self, name: str, mib_name: str = None) -> Optional[str]:
        """解析名称"""
        if mib_name and mib_name in self.parsers:
            return self.parsers[mib_name].resolve_name(name)
        return self._default_parser.resolve_name(name)


class OIDResolver:
    """OID解析器"""
    
    def __init__(self, registry: MIBRegistry = None):
        self.registry = registry or MIBRegistry()
        self.cache: Dict[str, Optional[str]] = {}
    
    def resolve(self, oid: str, use_cache: bool = True) -> str:
        """解析OID"""
        if use_cache and oid in self.cache:
            return self.cache[oid]
        
        name = self.registry.resolve(oid)
        result = name or oid
        self.cache[oid] = result
        return result
    
    def resolve_value(self, oid: str, value: Any, use_cache: bool = True) -> Any:
        """解析值"""
        node = self.registry._default_parser.get_node(oid)
        if not node:
            return value
        
        # 枚举值处理
        if node.syntax in ("INTEGER", "Integer32") and isinstance(value, int):
            return value  # 可以添加枚举映射
        
        return value
    
    def format_oid(self, oid: str, separator: str = ".") -> str:
        """格式化OID"""
        return oid.replace(".", separator)
    
    def parse_oid(self, oid_str: str, separator: str = ".") -> str:
        """解析OID字符串"""
        return oid_str.replace(separator, ".")
    
    def is_oid(self, value: str) -> bool:
        """判断是否为OID"""
        parts = value.split('.')
        return all(p.isdigit() for p in parts if p)
