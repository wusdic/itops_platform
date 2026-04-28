"""
配置验证器
验证配置项是否符合要求
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigValidator:
    """
    配置验证器
    
    功能特性：
    1. 内置常用验证规则
    2. 支持自定义验证函数
    3. 验证错误详细信息
    4. 支持条件验证
    
    使用示例：
    >>> validator = ConfigValidator()
    >>> validator.required('database.host')
    >>> validator.range('app.port', 1, 65535)
    >>> validator.pattern('redis.host', r'^[\w.-]+$')
    >>> validator.custom('ai.model', lambda v: v.startswith('gpt') or v.startswith('qwen'))
    >>> validator.validate(config)
    """
    
    def __init__(self):
        self._rules: List[Tuple[str, Callable, str]] = []
        self._errors: List[str] = []
    
    def required(self, key: str, message: Optional[str] = None) -> 'ConfigValidator':
        """
        必填验证
        
        Args:
            key: 配置键
            message: 错误消息
        
        Returns:
            self
        """
        def validate(value):
            if value is None or value == '':
                raise ValidationError(message or f"配置项 {key} 是必填项")
        
        self._rules.append((key, validate, message or f"必填: {key}"))
        return self
    
    def type_check(self, key: str, expected_type: type, message: Optional[str] = None) -> 'ConfigValidator':
        """
        类型验证
        
        Args:
            key: 配置键
            expected_type: 期望的类型
            message: 错误消息
        
        Returns:
            self
        """
        def validate(value):
            if value is not None and not isinstance(value, expected_type):
                raise ValidationError(
                    message or f"配置项 {key} 应该是 {expected_type.__name__} 类型"
                )
        
        self._rules.append((key, validate, message or f"类型检查: {key}"))
        return self
    
    def range(self, key: str, min_val: Optional[Union[int, float]] = None,
              max_val: Optional[Union[int, float]] = None,
              message: Optional[str] = None) -> 'ConfigValidator':
        """
        范围验证
        
        Args:
            key: 配置键
            min_val: 最小值
            max_val: 最大值
            message: 错误消息
        
        Returns:
            self
        """
        def validate(value):
            if value is None:
                return
            if not isinstance(value, (int, float)):
                raise ValidationError(f"配置项 {key} 必须是数字")
            if min_val is not None and value < min_val:
                raise ValidationError(
                    message or f"配置项 {key} 不能小于 {min_val}"
                )
            if max_val is not None and value > max_val:
                raise ValidationError(
                    message or f"配置项 {key} 不能大于 {max_val}"
                )
        
        self._rules.append((key, validate, message or f"范围检查: {key}"))
        return self
    
    def pattern(self, key: str, regex: str, message: Optional[str] = None) -> 'ConfigValidator':
        """
        正则验证
        
        Args:
            key: 配置键
            regex: 正则表达式
            message: 错误消息
        
        Returns:
            self
        """
        import re
        
        def validate(value):
            if value is None:
                return
            if not re.match(regex, str(value)):
                raise ValidationError(
                    message or f"配置项 {key} 格式不正确"
                )
        
        self._rules.append((key, validate, message or f"正则检查: {key}"))
        return self
    
    def in_list(self, key: str, values: List[Any], message: Optional[str] = None) -> 'ConfigValidator':
        """
        枚举验证
        
        Args:
            key: 配置键
            values: 允许的值列表
            message: 错误消息
        
        Returns:
            self
        """
        def validate(value):
            if value is not None and value not in values:
                raise ValidationError(
                    message or f"配置项 {key} 必须是以下值之一: {values}"
                )
        
        self._rules.append((key, validate, message or f"枚举检查: {key}"))
        return self
    
    def custom(self, key: str, validator_fn: Callable[[Any], None],
               message: Optional[str] = None) -> 'ConfigValidator':
        """
        自定义验证函数
        
        Args:
            key: 配置键
            validator_fn: 验证函数，抛出异常表示验证失败
            message: 错误消息
        
        Returns:
            self
        """
        def wrapped_validate(value):
            try:
                validator_fn(value)
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(
                    message or f"配置项 {key} 验证失败: {e}"
                )
        
        self._rules.append((key, wrapped_validate, message or f"自定义验证: {key}"))
        return self
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        执行验证
        
        Args:
            config: 配置字典
        
        Returns:
            验证是否通过
        
        Raises:
            ValidationError: 验证失败
        """
        self._errors = []
        
        for key, validator_fn, error_msg in self._rules:
            try:
                value = self._get_nested_value(config, key)
                validator_fn(value)
            except ValidationError as e:
                self._errors.append(str(e))
                logger.warning(f"配置验证失败 [{key}]: {e}")
        
        if self._errors:
            error_summary = "\n".join(f"  - {e}" for e in self._errors)
            raise ValidationError(f"配置验证失败:\n{error_summary}")
        
        logger.info("配置验证通过")
        return True
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
    
    def get_errors(self) -> List[str]:
        """获取验证错误列表"""
        return self._errors.copy()


# 预定义的验证器
class DatabaseValidator(ConfigValidator):
    """数据库配置验证器"""
    
    def __init__(self):
        super().__init__()
        self.required('host', '数据库主机必填')
        self.range('port', 1, 65535, '数据库端口必须在1-65535范围内')
        self.required('database', '数据库名称必填')


class RedisValidator(ConfigValidator):
    """Redis配置验证器"""
    
    def __init__(self):
        super().__init__()
        self.required('host', 'Redis主机必填')
        self.range('port', 1, 65535, 'Redis端口必须在1-65535范围内')


class AppValidator(ConfigValidator):
    """应用配置验证器"""
    
    def __init__(self):
        super().__init__()
        self.required('host', '应用主机必填')
        self.range('port', 1, 65535, '应用端口必须在1-65535范围内')
        self.in_list('log_level', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])


class MonitorValidator(ConfigValidator):
    """监控配置验证器"""
    
    def __init__(self):
        super().__init__()
        self.range('snmp_timeout', 1, 60, 'SNMP超时时间在1-60秒之间')
        self.range('agent_port', 1, 65535, 'Agent端口必须在1-65535范围内')
        self.range('collection_interval', 10, 3600, '采集间隔在10-3600秒之间')


class AIValidator(ConfigValidator):
    """AI配置验证器"""
    
    def __init__(self):
        super().__init__()
        self.in_list('provider', ['ollama', 'openai', 'azure', 'local'])
        self.required('model', 'AI模型必填')
        self.range('temperature', 0, 1, 'temperature必须在0-1之间')
        self.range('max_tokens', 100, 128000, 'max_tokens超出合理范围')