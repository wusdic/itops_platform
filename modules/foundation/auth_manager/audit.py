"""
FM-04 权限管理模块 - 操作审计模块
包含审计日志模型、操作记录装饰器、审计查询接口
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
import threading


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(Enum):
    """审计操作类型"""
    # 认证相关
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # 用户管理
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_PASSWORD_CHANGE = "user_password_change"
    USER_ROLE_ASSIGN = "user_role_assign"
    USER_ROLE_REVOKE = "user_role_revoke"
    
    # 角色管理
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"
    ROLE_DELETE = "role_delete"
    ROLE_PERMISSION_ADD = "role_permission_add"
    ROLE_PERMISSION_REMOVE = "role_permission_remove"
    
    # 资源配置
    CONFIG_VIEW = "config_view"
    CONFIG_UPDATE = "config_update"
    CONFIG_DELETE = "config_delete"
    
    # 系统操作
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    SYSTEM_UPDATE = "system_update"
    
    # 资源操作
    RESOURCE_CREATE = "resource_create"
    RESOURCE_READ = "resource_read"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"


@dataclass
class AuditLog:
    """审计日志模型"""
    id: str
    timestamp: datetime
    user_id: str
    username: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    status: str  # success, failed
    level: AuditLevel
    request_method: str = ""
    request_path: str = ""
    request_body: Optional[Dict[str, Any]] = None
    response_status: int = 0
    error_message: str = ""
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "level": self.level.value,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLog':
        """从字典创建"""
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if isinstance(data.get('level'), str):
            data['level'] = AuditLevel(data['level'])
        return cls(**data)


class AuditQuery:
    """审计日志查询条件"""
    
    def __init__(self):
        self.filters: List[Dict[str, Any]] = []
        self.sort_field: str = "timestamp"
        self.sort_order: str = "desc"
        self.limit: int = 100
        self.offset: int = 0

    def by_user(self, user_id: str) -> 'AuditQuery':
        self.filters.append({"field": "user_id", "op": "eq", "value": user_id})
        return self

    def by_username(self, username: str) -> 'AuditQuery':
        self.filters.append({"field": "username", "op": "eq", "value": username})
        return self

    def by_action(self, action: str) -> 'AuditQuery':
        self.filters.append({"field": "action", "op": "eq", "value": action})
        return self

    def by_actions(self, actions: List[str]) -> 'AuditQuery':
        self.filters.append({"field": "action", "op": "in", "value": actions})
        return self

    def by_resource(self, resource_type: str, resource_id: str = None) -> 'AuditQuery':
        self.filters.append({"field": "resource_type", "op": "eq", "value": resource_type})
        if resource_id:
            self.filters.append({"field": "resource_id", "op": "eq", "value": resource_id})
        return self

    def by_status(self, status: str) -> 'AuditQuery':
        self.filters.append({"field": "status", "op": "eq", "value": status})
        return self

    def by_level(self, level: AuditLevel) -> 'AuditQuery':
        self.filters.append({"field": "level", "op": "eq", "value": level.value})
        return self

    def by_time_range(self, start: datetime, end: datetime = None) -> 'AuditQuery':
        self.filters.append({"field": "timestamp", "op": "gte", "value": start})
        if end:
            self.filters.append({"field": "timestamp", "op": "lte", "value": end})
        return self

    def by_ip(self, ip_address: str) -> 'AuditQuery':
        self.filters.append({"field": "ip_address", "op": "eq", "value": ip_address})
        return self

    def by_keyword(self, keyword: str) -> 'AuditQuery':
        self.filters.append({"field": "keyword", "op": "contains", "value": keyword})
        return self

    def order_by(self, field: str, desc: bool = True) -> 'AuditQuery':
        self.sort_field = field
        self.sort_order = "desc" if desc else "asc"
        return self

    def paginate(self, limit: int, offset: int = 0) -> 'AuditQuery':
        self.limit = limit
        self.offset = offset
        return self


class AuditLogger:
    """审计日志管理器"""

    def __init__(self, retention_days: int = 90):
        self.logs: List[AuditLog] = []
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[AuditLog], None]] = []

    def log(self, user_id: str, username: str, action: str,
            resource_type: str = "", resource_id: str = "",
            ip_address: str = "", user_agent: str = "",
            status: str = "success", level: AuditLevel = AuditLevel.INFO,
            request_method: str = "", request_path: str = "",
            request_body: Dict[str, Any] = None,
            response_status: int = 200, error_message: str = "",
            duration_ms: int = 0, metadata: Dict[str, Any] = None) -> AuditLog:
        """记录审计日志"""
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            level=level,
            request_method=request_method,
            request_path=request_path,
            request_body=request_body,
            response_status=response_status,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )

        with self._lock:
            self.logs.append(audit_log)
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(audit_log)
            except:
                pass
        
        return audit_log

    def query(self, query: AuditQuery) -> List[AuditLog]:
        """查询审计日志"""
        with self._lock:
            results = list(self.logs)
        
        for f in query.filters:
            field = f["field"]
            op = f["op"]
            value = f["value"]
            
            filtered = []
            for log in results:
                if field == "keyword":
                    # 关键字搜索
                    log_str = json.dumps(log.to_dict(), ensure_ascii=False)
                    if op == "contains" and value.lower() in log_str.lower():
                        filtered.append(log)
                elif field == "timestamp":
                    log_time = getattr(log, field)
                    if op == "gte":
                        if isinstance(value, datetime) and log_time >= value:
                            filtered.append(log)
                        elif isinstance(value, timedelta):
                            if datetime.utcnow() - log_time <= value:
                                filtered.append(log)
                    elif op == "lte" and log_time <= value:
                        filtered.append(log)
                else:
                    log_value = getattr(log, field, None)
                    if op == "eq" and log_value == value:
                        filtered.append(log)
                    elif op == "in" and log_value in value:
                        filtered.append(log)
            
            results = filtered
        
        # 排序
        results.sort(
            key=lambda x: getattr(x, query.sort_field),
            reverse=(query.sort_order == "desc")
        )
        
        # 分页
        return results[query.offset:query.offset + query.limit]

    def count(self, query: AuditQuery) -> int:
        """统计审计日志数量"""
        return len(self.query(AuditQuery()))

    def get_by_id(self, log_id: str) -> Optional[AuditLog]:
        """通过ID获取审计日志"""
        with self._lock:
            for log in self.logs:
                if log.id == log_id:
                    return log
        return None

    def get_user_activity(self, user_id: str, days: int = 30) -> List[AuditLog]:
        """获取用户活动记录"""
        start_time = datetime.utcnow() - timedelta(days=days)
        query = (AuditQuery()
                .by_user(user_id)
                .by_time_range(start_time)
                .order_by("timestamp"))
        return self.query(query)

    def get_failed_logins(self, hours: int = 24) -> List[AuditLog]:
        """获取失败登录记录"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query = (AuditQuery()
                .by_actions([AuditAction.LOGIN_FAILED.value, AuditAction.LOGIN.value])
                .by_time_range(start_time)
                .by_status("failed")
                .order_by("timestamp"))
        return self.query(query)

    def get_recent_activity(self, limit: int = 50) -> List[AuditLog]:
        """获取最近活动"""
        query = AuditQuery().order_by("timestamp").paginate(limit)
        return self.query(query)

    def cleanup_old_logs(self) -> int:
        """清理过期日志"""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        with self._lock:
            original_count = len(self.logs)
            self.logs = [log for log in self.logs if log.timestamp >= cutoff]
            removed = original_count - len(self.logs)
        return removed

    def add_callback(self, callback: Callable[[AuditLog], None]):
        """添加日志回调"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[AuditLog], None]):
        """移除日志回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def export_logs(self, query: AuditQuery, format: str = "json") -> str:
        """导出日志"""
        logs = self.query(query)
        if format == "json":
            return json.dumps([log.to_dict() for log in logs], ensure_ascii=False, indent=2)
        elif format == "csv":
            return self._to_csv(logs)
        return ""

    def _to_csv(self, logs: List[AuditLog]) -> str:
        """转换为CSV格式"""
        if not logs:
            return ""
        
        headers = ["id", "timestamp", "user_id", "username", "action", 
                   "resource_type", "resource_id", "status", "ip_address"]
        
        lines = [",".join(headers)]
        for log in logs:
            row = [str(getattr(log, h, "")) for h in headers]
            lines.append(",".join(row))
        
        return "\n".join(lines)


def audit_log(action: str, resource_type: str = "", level: AuditLevel = AuditLevel.INFO):
    """
    审计日志装饰器
    用于自动记录操作审计
    
    用法:
    @audit_log(AuditAction.USER_CREATE, "user")
    def create_user(user_data):
        ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从上下文中获取用户信息
            user_id = kwargs.get('user_id', 'system')
            username = kwargs.get('username', 'system')
            ip_address = kwargs.get('ip_address', '')
            user_agent = kwargs.get('user_agent', '')
            
            # 记录开始时间
            start_time = datetime.utcnow()
            
            # 获取request_body
            request_body = kwargs.get('request_body')
            
            try:
                result = func(*args, **kwargs)
                status = "success"
                error_message = ""
                response_status = 200
                
                # 从结果中提取resource_id
                resource_id = ""
                if isinstance(result, dict) and 'id' in result:
                    resource_id = result['id']
                
                return result
                
            except Exception as e:
                status = "failed"
                error_message = str(e)
                response_status = 500
                resource_id = ""
                raise
                
            finally:
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # 获取审计logger实例
                audit_logger = kwargs.get('_audit_logger')
                if audit_logger:
                    audit_logger.log(
                        user_id=user_id,
                        username=username,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status=status,
                        level=level,
                        request_method=kwargs.get('request_method', ''),
                        request_path=kwargs.get('request_path', ''),
                        request_body=request_body,
                        response_status=response_status,
                        error_message=error_message,
                        duration_ms=duration_ms
                    )
        
        return wrapper
    return decorator


class AuditContext:
    """审计上下文"""
    
    _instance = None
    _local = threading.local()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_context(cls, user_id: str, username: str, 
                   ip_address: str = "", user_agent: str = ""):
        """设置审计上下文"""
        cls._local.user_id = user_id
        cls._local.username = username
        cls._local.ip_address = ip_address
        cls._local.user_agent = user_agent
    
    @classmethod
    def get_context(cls) -> Dict[str, str]:
        """获取审计上下文"""
        return {
            "user_id": getattr(cls._local, 'user_id', 'system'),
            "username": getattr(cls._local, 'username', 'system'),
            "ip_address": getattr(cls._local, 'ip_address', ''),
            "user_agent": getattr(cls._local, 'user_agent', '')
        }
    
    @classmethod
    def clear_context(cls):
        """清除审计上下文"""
        cls._local.user_id = 'system'
        cls._local.username = 'system'
        cls._local.ip_address = ''
        cls._local.user_agent = ''


class AuditReport:
    """审计报表生成器"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    def generate_user_activity_report(self, user_id: str, 
                                       start_date: datetime,
                                       end_date: datetime = None) -> Dict[str, Any]:
        """生成用户活动报表"""
        end_date = end_date or datetime.utcnow()
        
        query = (AuditQuery()
                .by_user(user_id)
                .by_time_range(start_date, end_date))
        logs = self.audit_logger.query(query)
        
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        return {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_actions": len(logs),
            "action_breakdown": action_counts,
            "success_count": sum(1 for l in logs if l.status == "success"),
            "failed_count": sum(1 for l in logs if l.status == "failed")
        }

    def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成安全报表"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        failed_logins = self.audit_logger.get_failed_logins(hours)
        suspicious_ips = {}
        
        for log in failed_logins:
            ip = log.ip_address
            if ip:
                suspicious_ips[ip] = suspicious_ips.get(ip, 0) + 1
        
        return {
            "period_hours": hours,
            "failed_login_count": len(failed_logins),
            "suspicious_ips": suspicious_ips,
            "critical_events": self.audit_logger.query(
                AuditQuery()
                .by_level(AuditLevel.CRITICAL)
                .by_time_range(start_time)
            )
        }
