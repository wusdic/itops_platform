"""
FM-04 权限管理模块 - LDAP集成模块
包含LDAP用户同步、LDAP认证、组织架构同步
"""

import ssl
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LDAPAuthMethod(Enum):
    """LDAP认证方式"""
    SIMPLE = "simple"
    SASL_DIGEST_MD5 = "sasl_digest_md5"
    SASL_GSSAPI = "sasl_gssapi"


class LDAPScope(Enum):
    """LDAP搜索范围"""
    BASE = "base"
    ONE_LEVEL = "one_level"
    SUBTREE = "subtree"


@dataclass
class LDAPUser:
    """LDAP用户对象"""
    dn: str                    # Distinguished Name
    username: str              # 用户名 (sAMAccountName or uid)
    email: str                 # 邮箱 (mail)
    display_name: str          # 显示名称 (displayName)
    first_name: str = ""       # 名
    last_name: str = ""        # 姓
    groups: List[str] = None   # 所属组
    enabled: bool = True       # 账户是否启用
    raw_attributes: Dict[str, Any] = None  # 原始属性
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.raw_attributes is None:
            self.raw_attributes = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dn": self.dn,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "groups": self.groups,
            "enabled": self.enabled
        }


@dataclass
class LDAPGroup:
    """LDAP组对象"""
    dn: str
    name: str
    description: str = ""
    members: List[str] = None  # 成员DN列表
    parent_group: str = ""     # 父组DN
    
    def __post_init__(self):
        if self.members is None:
            self.members = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dn": self.dn,
            "name": self.name,
            "description": self.description,
            "members": self.members,
            "parent_group": self.parent_group
        }


@dataclass
class LDAPConfig:
    """LDAP配置"""
    server: str                # LDAP服务器地址
    port: int = 389            # 端口
    use_ssl: bool = False      # 是否使用SSL
    start_tls: bool = False    # 是否使用STARTTLS
    bind_dn: str = ""          # 绑定DN
    bind_password: str = ""    # 绑定密码
    base_dn: str = ""          # 基础DN
    user_filter: str = "(objectClass=user)"      # 用户过滤器
    group_filter: str = "(objectClass=group)"     # 组过滤器
    user_search_base: str = ""                   # 用户搜索路径
    group_search_base: str = ""                  # 组搜索路径
    username_attr: str = "sAMAccountName"        # 用户名属性 (AD: sAMAccountName, OpenLDAP: uid)
    email_attr: str = "mail"                      # 邮箱属性
    display_name_attr: str = "displayName"       # 显示名称属性
    group_member_attr: str = "member"            #组成员属性
    sync_interval: int = 3600                     # 同步间隔(秒)
    timeout: int = 30                            # 超时时间(秒)
    page_size: int = 1000                         # 分页大小


class LDAPConnection:
    """LDAP连接包装类"""

    def __init__(self, config: LDAPConfig):
        self.config = config
        self._conn = None
        self._connected = False

    def connect(self) -> bool:
        """建立LDAP连接"""
        try:
            # 尝试使用ldap3库
            import ldap3
            from ldap3 import Server, Connection, ALL, SUBTREE
            
            server_url = f"{'ldaps' if self.config.use_ssl else 'ldap'}://{self.config.server}:{self.config.port}"
            server = Server(server_url, get_info=ALL)
            
            if self.config.bind_dn and self.config.bind_password:
                self._conn = Connection(
                    server,
                    user=self.config.bind_dn,
                    password=self.config.bind_password,
                    auto_bind=True
                )
            else:
                self._conn = Connection(server, auto_bind=True)
            
            self._connected = True
            return True
        except ImportError:
            # ldap3未安装，使用模拟模式
            self._connected = True
            return True
        except Exception as e:
            print(f"LDAP连接失败: {e}")
            return False

    def disconnect(self):
        """断开LDAP连接"""
        if self._conn:
            try:
                self._conn.unbind()
            except:
                pass
        self._connected = False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    def search(self, search_base: str, search_filter: str,
               scope: LDAPScope = LDAPScope.SUBTREE,
               attributes: List[str] = None) -> List[Dict[str, Any]]:
        """搜索LDAP条目"""
        if not self._connected:
            return []

        try:
            import ldap3
            from ldap3 import SUBTREE, LEVEL, BASE
            
            scope_map = {
                LDAPScope.BASE: BASE,
                LDAPScope.ONE_LEVEL: LEVEL,
                LDAPScope.SUBTREE: SUBTREE
            }
            
            if self._conn:
                self._conn.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    search_scope=scope_map[scope],
                    attributes=attributes or ['*']
                )
                return [entry.entry_to_dict() for entry in self._conn.entries]
        except ImportError:
            # 模拟模式
            return []
        except Exception as e:
            print(f"LDAP搜索失败: {e}")
            return []
        
        return []

    def authenticate(self, user_dn: str, password: str) -> bool:
        """LDAP用户认证"""
        try:
            import ldap3
            from ldap3 import Server, Connection
            
            server_url = f"{'ldaps' if self.config.use_ssl else 'ldap'}://{self.config.server}:{self.config.port}"
            server = Server(server_url)
            conn = Connection(server, user=user_dn, password=password)
            
            return conn.bind()
        except:
            return False


class LDAPClient:
    """LDAP客户端"""

    def __init__(self, config: LDAPConfig):
        self.config = config
        self.connection = LDAPConnection(config)
        self._last_sync: Optional[datetime] = None
        self._sync_callbacks: List[Callable] = []

    def connect(self) -> bool:
        """连接LDAP服务器"""
        return self.connection.connect()

    def disconnect(self):
        """断开LDAP连接"""
        self.connection.disconnect()

    def authenticate(self, username: str, password: str) -> tuple[bool, str, Optional[LDAPUser]]:
        """
        LDAP用户认证
        返回: (是否成功, 消息, 用户对象)
        """
        if not self.connection.is_connected():
            if not self.connect():
                return False, "LDAP服务器连接失败", None

        # 搜索用户
        search_base = self.config.user_search_base or self.config.base_dn
        search_filter = f"(&{self.config.user_filter}({self.config.username_attr}={username}))"
        
        results = self.connection.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=[
                self.config.username_attr,
                self.config.email_attr,
                self.config.display_name_attr,
                'givenName',
                'sn',
                'memberOf',
                'userAccountControl'
            ]
        )

        if not results:
            return False, "用户不存在", None

        user_entry = results[0]
        user_dn = user_entry.get('dn', '')
        
        # 检查用户是否启用 (对于AD)
        if 'userAccountControl' in user_entry:
            # bit 2 = account disabled
            uac = int(user_entry['userAccountControl'][0])
            if uac & 0x2:
                return False, "账户已禁用", None

        # 尝试绑定认证
        if self.connection.authenticate(user_dn, password):
            ldap_user = self._parse_user_entry(user_entry, user_dn)
            return True, "认证成功", ldap_user
        
        return False, "密码错误", None

    def _parse_user_entry(self, entry: Dict[str, Any], dn: str) -> LDAPUser:
        """解析LDAP用户条目"""
        attrs = entry.get('attributes', {})
        
        username = self._get_attr(attrs, self.config.username_attr, dn.split(',')[0].split('=')[1])
        email = self._get_attr(attrs, self.config.email_attr, '')
        display_name = self._get_attr(attrs, self.config.display_name_attr, username)
        first_name = self._get_attr(attrs, 'givenName', '')
        last_name = self._get_attr(attrs, 'sn', '')
        groups = attrs.get(self.config.group_member_attr, [])
        
        return LDAPUser(
            dn=dn,
            username=username,
            email=email,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            groups=[g.split(',')[0].split('=')[1] if '=' in g else g for g in groups],
            enabled=True,
            raw_attributes=attrs
        )

    def _get_attr(self, attrs: Dict, key: str, default: str = '') -> str:
        """安全获取属性值"""
        value = attrs.get(key, [default])
        return value[0] if isinstance(value, list) and value else default

    def sync_users(self, callback: Callable[[LDAPUser], None] = None) -> List[LDAPUser]:
        """
        同步LDAP用户
        callback: 同步每个用户时的回调函数
        """
        if not self.connection.is_connected():
            if not self.connect():
                return []

        search_base = self.config.user_search_base or self.config.base_dn
        results = self.connection.search(
            search_base=search_base,
            search_filter=self.config.user_filter,
            attributes=[
                self.config.username_attr,
                self.config.email_attr,
                self.config.display_name_attr,
                'givenName',
                'sn',
                'memberOf',
                'userAccountControl'
            ]
        )

        users = []
        for entry in results:
            dn = entry.get('dn', '')
            ldap_user = self._parse_user_entry(entry, dn)
            users.append(ldap_user)
            
            if callback:
                callback(ldap_user)
        
        self._last_sync = datetime.utcnow()
        return users

    def sync_groups(self, callback: Callable[[LDAPGroup], None] = None) -> List[LDAPGroup]:
        """
        同步LDAP组/组织架构
        """
        if not self.connection.is_connected():
            if not self.connect():
                return []

        search_base = self.config.group_search_base or self.config.base_dn
        results = self.connection.search(
            search_base=search_base,
            search_filter=self.config.group_filter,
            attributes=['cn', 'description', 'member', 'memberOf']
        )

        groups = []
        for entry in results:
            dn = entry.get('dn', '')
            attrs = entry.get('attributes', {})
            
            group = LDAPGroup(
                dn=dn,
                name=attrs.get('cn', [''])[0] if attrs.get('cn') else '',
                description=attrs.get('description', [''])[0] if attrs.get('description') else '',
                members=attrs.get(self.config.group_member_attr, []),
                parent_group=''
            )
            groups.append(group)
            
            if callback:
                callback(group)
        
        return groups

    def get_user_groups(self, username: str) -> List[str]:
        """获取用户所属的组"""
        search_base = self.config.user_search_base or self.config.base_dn
        search_filter = f"(&{self.config.user_filter}({self.config.username_attr}={username}))"
        
        results = self.connection.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=['memberOf']
        )

        if results:
            attrs = results[0].get('attributes', {})
            groups = attrs.get('memberOf', [])
            return [g.split(',')[0].split('=')[1] if '=' in g else g for g in groups]
        
        return []

    def search_users(self, filter_str: str, limit: int = 100) -> List[LDAPUser]:
        """搜索用户"""
        if not self.connection.is_connected():
            if not self.connect():
                return []

        search_base = self.config.user_search_base or self.config.base_dn
        search_filter = f"(&{self.config.user_filter}{filter_str})"
        
        results = self.connection.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=['*']
        )

        return [self._parse_user_entry(entry, entry.get('dn', '')) for entry in results[:limit]]

    def get_organization_tree(self) -> Dict[str, Any]:
        """获取组织架构树"""
        groups = self.sync_groups()
        
        # 构建树结构
        group_map = {g.dn: g for g in groups}
        root_groups = []
        
        for group in groups:
            if group.parent_group and group.parent_group in group_map:
                continue
            root_groups.append(group)
        
        def build_tree(group: LDAPGroup) -> Dict[str, Any]:
            children = [g for g in groups if g.parent_group == group.dn]
            return {
                "name": group.name,
                "dn": group.dn,
                "description": group.description,
                "members": len(group.members),
                "children": [build_tree(c) for c in children]
            }
        
        return {
            "name": "Organization",
            "children": [build_tree(g) for g in root_groups]
        }

    def add_sync_callback(self, callback: Callable):
        """添加同步回调"""
        self._sync_callbacks.append(callback)

    def remove_sync_callback(self, callback: Callable):
        """移除同步回调"""
        if callback in self._sync_callbacks:
            self._sync_callbacks.remove(callback)

    def get_last_sync_time(self) -> Optional[datetime]:
        """获取上次同步时间"""
        return self._last_sync


class LDAPSyncManager:
    """LDAP同步管理器"""

    def __init__(self, ldap_client: LDAPClient):
        self.ldap_client = ldap_client
        self.synced_users: Dict[str, LDAPUser] = {}
        self.synced_groups: Dict[str, LDAPGroup] = {}
        self.sync_history: List[Dict[str, Any]] = []

    def full_sync(self, user_handler: Callable[[LDAPUser], None] = None,
                  group_handler: Callable[[LDAPGroup], None] = None) -> Dict[str, Any]:
        """全量同步"""
        start_time = datetime.utcnow()
        
        # 同步用户
        users = self.ldap_client.sync_users(user_handler)
        self.synced_users = {u.username: u for u in users}
        
        # 同步组
        groups = self.ldap_client.sync_groups(group_handler)
        self.synced_groups = {g.name: g for g in groups}
        
        end_time = datetime.utcnow()
        
        result = {
            "start_time": start_time,
            "end_time": end_time,
            "users_synced": len(users),
            "groups_synced": len(groups),
            "status": "success"
        }
        
        self.sync_history.append(result)
        return result

    def incremental_sync(self) -> Dict[str, Any]:
        """增量同步"""
        # 在生产环境中，这里应该检查LDAP的usnChanged等属性
        return self.full_sync()

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        last_sync = self.ldap_client.get_last_sync_time()
        return {
            "last_sync": last_sync,
            "total_users": len(self.synced_users),
            "total_groups": len(self.synced_groups),
            "sync_count": len(self.sync_history)
        }

    def map_ldap_groups_to_roles(self, mapping: Dict[str, str]) -> Dict[str, str]:
        """
        将LDAP组映射到系统角色
        mapping: {"LDAP_Group_Name": "system_role_name", ...}
        """
        role_mapping = {}
        for ldap_group, system_role in mapping.items():
            if ldap_group in self.synced_groups:
                role_mapping[ldap_group] = system_role
        return role_mapping

    def get_user_role_from_ldap_groups(self, ldap_user: LDAPUser, 
                                        mapping: Dict[str, str]) -> List[str]:
        """根据LDAP组获取对应的系统角色"""
        roles = []
        for group in ldap_user.groups:
            if group in mapping:
                roles.append(mapping[group])
        return roles
