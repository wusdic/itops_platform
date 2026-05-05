# -*- coding: utf-8 -*-
"""
ITOps Platform - 通用工具模块
单例装饰器、重试装饰器、验证器等
"""
import time
import functools
import threading
from typing import Any, Callable, Optional, TypeVar, List, Dict
from datetime import datetime, timedelta
import hashlib
import json

T = TypeVar('T')


def singleton(cls: T) -> T:
    """单例装饰器"""
    instances = {}
    lock = threading.Lock()
    
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable = None
):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        raise
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def timeout(seconds: float):
    """超时装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
            
            # 设置超时信号
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))
            
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            
            return result
        
        return wrapper
    return decorator


def cached(ttl: int = 300, key_func: Callable = None):
    """缓存装饰器"""
    cache: Dict[str, tuple] = {}
    lock = threading.Lock()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # 检查缓存
            current_time = time.time()
            with lock:
                if cache_key in cache:
                    result, expiry = cache[cache_key]
                    if current_time < expiry:
                        return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 更新缓存
            with lock:
                cache[cache_key] = (result, current_time + ttl)
                # 清理过期缓存
                expired_keys = [k for k, (_, exp) in cache.items() if current_time >= exp]
                for k in expired_keys:
                    del cache[k]
            
            return result
        
        # 添加清除缓存方法
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    
    return decorator


class RateLimiter:
    """限流器"""
    
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []
        self.lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                current_time = time.time()
                # 清理超出时间窗口的调用
                self.calls = [t for t in self.calls if current_time - t < self.period]
                
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.period - (current_time - self.calls[0])
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        current_time = time.time()
                        self.calls = [t for t in self.calls if current_time - t < self.period]
                
                self.calls.append(current_time)
            
            return func(*args, **kwargs)
        
        return wrapper


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.failure_count = 0
                self.state = "closed"
            return result
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
            
            raise e


class LazyProperty:
    """延迟属性 - 首次访问时计算，之后缓存"""
    
    def __init__(self, func: Callable):
        self.func = func
        self.attr_name = None
    
    def __call__(self):
        raise AttributeError("Cannot call LazyProperty directly")
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        # 获取属性名
        if self.attr_name is None:
            # 从调用栈中获取属性名（简化实现）
            self.attr_name = f"_{self.func.__name__}_cached"
        
        # 检查是否已计算
        if not hasattr(obj, self.attr_name):
            # 计算并缓存
            value = self.func(obj)
            setattr(obj, self.attr_name, value)
        
        return getattr(obj, self.attr_name)


# 通用验证器
class Validator:
    """通用验证器"""
    
    @staticmethod
    def required(value: Any, name: str = "value") -> Any:
        """必填验证"""
        if value is None or value == "":
            raise ValueError(f"{name} is required")
        return value
    
    @staticmethod
    def min_length(value: str, length: int, name: str = "value") -> str:
        """最小长度"""
        if len(str(value)) < length:
            raise ValueError(f"{name} length must be at least {length}")
        return value
    
    @staticmethod
    def max_length(value: str, length: int, name: str = "value") -> str:
        """最大长度"""
        if len(str(value)) > length:
            raise ValueError(f"{name} length must not exceed {length}")
        return value
    
    @staticmethod
    def email(value: str) -> str:
        """邮箱格式"""
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, value):
            raise ValueError(f"{value} is not a valid email address")
        return value
    
    @staticmethod
    def url(value: str) -> str:
        """URL格式"""
        import re
        pattern = r'^https?://[\w\.-]+\.\w+'
        if not re.match(pattern, value):
            raise ValueError(f"{value} is not a valid URL")
        return value
    
    @staticmethod
    def ip(value: str) -> str:
        """IP地址格式"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, value):
            raise ValueError(f"{value} is not a valid IP address")
        return value
    
    @staticmethod
    def port(value: int) -> int:
        """端口范围"""
        if not (1 <= value <= 65535):
            raise ValueError(f"{value} is not a valid port number")
        return value
    
    @staticmethod
    def in_range(value: float, min_val: float, max_val: float, name: str = "value") -> float:
        """数值范围"""
        if value < min_val or value > max_val:
            raise ValueError(f"{name} must be between {min_val} and {max_val}")
        return value


def hash_password(password: str, salt: bytes = None) -> tuple:
    """密码哈希"""
    import hashlib
    import base64
    
    if salt is None:
        salt = base64.b64encode(os.urandom(32))
    
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return base64.b64encode(pwd_hash).decode(), base64.b64encode(salt).decode()


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码"""
    import base64
    
    salt_bytes = base64.b64decode(salt.encode())
    new_hash, _ = hash_password(password, salt_bytes)
    return new_hash == hashed


def generate_token(length: int = 32) -> str:
    """生成随机令牌"""
    import secrets
    return secrets.token_urlsafe(length)


def deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def to_snake_case(name: str) -> str:
    """驼峰转蛇形"""
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def to_camel_case(name: str) -> str:
    """蛇形转驼峰"""
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def parse_duration(duration_str: str) -> float:
    """解析时间字符串为秒数"""
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
    }
    
    duration_str = duration_str.strip().lower()
    
    if duration_str[-1] in units:
        return float(duration_str[:-1]) * units[duration_str[-1]]
    
    return float(duration_str)


def format_duration(seconds: float) -> str:
    """格式化秒数为可读字符串"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"
