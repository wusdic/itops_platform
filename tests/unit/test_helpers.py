# -*- coding: utf-8 -*-
"""
ITOps Platform - 通用工具模块单元测试
"""
import os
import time
import signal
import pytest
import threading
from unittest.mock import Mock, patch, MagicMock


# 测试路径设置
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.utils.helpers import (
    singleton, retry, timeout, cached,
    RateLimiter, CircuitBreaker, LazyProperty,
    Validator, hash_password, verify_password, generate_token,
    deep_merge, to_snake_case, to_camel_case,
    parse_duration, format_duration
)


# ==================== Singleton 装饰器测试 ====================

class TestSingleton:
    """@singleton 装饰器测试"""
    
    def test_singleton_returns_same_instance(self):
        """测试单例装饰器返回相同实例"""
        @singleton
        class MyClass:
            def __init__(self, value):
                self.value = value
        
        obj1 = MyClass(10)
        obj2 = MyClass(20)
        
        assert obj1 is obj2
        assert obj1.value == 10  # 首次初始化值
        assert obj2.value == 10  # 返回同一实例
    
    def test_singleton_with_args(self):
        """测试带参数的单例"""
        @singleton
        class Container:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        
        c1 = Container(1, 2)
        c2 = Container(3, 4)
        
        assert c1 is c2
        assert c1.x == 1
        assert c1.y == 2
    
    def test_singleton_thread_safety(self):
        """测试线程安全"""
        @singleton
        class ThreadTest:
            def __init__(self):
                self.counter = 0
        
        results = []
        
        def create_instance():
            results.append(ThreadTest())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有线程应该获得同一实例
        assert all(r is results[0] for r in results)


# ==================== Retry 装饰器测试 ====================

class TestRetry:
    """@retry 装饰器测试"""
    
    def test_retry_success_first_try(self):
        """测试首次成功不重试"""
        call_count = 0
        
        @retry(max_attempts=3)
        def succeed_once():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeed_once()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"
        
        result = fail_twice()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """测试重试耗尽"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")
        
        with pytest.raises(ValueError, match="always fails"):
            always_fail()
        assert call_count == 3
    
    def test_retry_with_on_retry_callback(self):
        """测试带回调的重试"""
        call_count = 0
        retry_info = []
        
        def on_retry_handler(attempt, exception):
            retry_info.append((attempt, str(exception)))
        
        @retry(max_attempts=3, delay=0.01, on_retry=on_retry_handler)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("retry error")
            return "success"
        
        result = fail_twice()
        assert result == "success"
        assert len(retry_info) == 2
        assert retry_info[0] == (1, "retry error")
        assert retry_info[1] == (2, "retry error")
    
    def test_retry_with_backoff(self):
        """测试指数退避"""
        start_time = time.time()
        call_times = []
        
        @retry(max_attempts=3, delay=0.1, backoff=2.0)
        def fail_twice():
            call_times.append(time.time() - start_time)
            if len(call_times) < 3:
                raise ValueError("fail")
            return "success"
        
        fail_twice()
        
        # 第一次重试延迟 ~0.1s, 第二次 ~0.2s
        assert call_times[1] - call_times[0] >= 0.09
        assert call_times[2] - call_times[1] >= 0.19
    
    def test_retry_with_specific_exception(self):
        """测试只重试特定异常"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retried")
        
        with pytest.raises(TypeError):
            raise_type_error()
        assert call_count == 1  # 立即失败，不重试


# ==================== Timeout 装饰器测试 ====================

class TestTimeout:
    """@timeout 装饰器测试"""
    
    @pytest.mark.skipif(os.name == 'nt', reason="SIGALRM not supported on Windows")
    def test_timeout_success(self):
        """测试正常完成不超时"""
        @timeout(seconds=5)
        def quick_task():
            return "done"
        
        result = quick_task()
        assert result == "done"
    
    @pytest.mark.skipif(os.name == 'nt', reason="SIGALRM not supported on Windows")
    @pytest.mark.skip(reason="SIGALRM may not work in container/CI environments")
    def test_timeout_expires(self):
        """测试超时触发 - 在CI环境中可能跳过"""
        @timeout(seconds=0.05)
        def long_task():
            time.sleep(10)
            return "done"
        
        start = time.time()
        with pytest.raises(TimeoutError, match="timed out"):
            long_task()
        elapsed = time.time() - start
        # 应该很快失败而不是等待10秒
        assert elapsed < 1
    
    @pytest.mark.skipif(os.name == 'nt', reason="SIGALRM not supported on Windows")
    def test_timeout_cleans_up_signal(self):
        """测试信号清理"""
        @timeout(seconds=1)
        def task():
            return "result"
        
        # 连续执行确保信号正确清理
        for _ in range(3):
            result = task()
            assert result == "result"


# ==================== Cached 装饰器测试 ====================

class TestCached:
    """@cached 装饰器测试"""
    
    def test_cached_miss_then_hit(self):
        """测试缓存未命中后命中"""
        call_count = 0
        
        @cached(ttl=60)
        def get_value(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        assert get_value(5) == 10
        assert call_count == 1
        
        # 相同参数应从缓存获取
        assert get_value(5) == 10
        assert call_count == 1
        
        # 不同参数应重新计算
        assert get_value(3) == 6
        assert call_count == 2
    
    def test_cached_ttl_expires(self):
        """测试缓存过期"""
        call_count = 0
        
        @cached(ttl=1)
        def get_value(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        assert get_value(5) == 10
        assert call_count == 1
        
        # 短时间内相同参数从缓存
        assert get_value(5) == 10
        assert call_count == 1
        
        # 等待过期
        time.sleep(1.1)
        
        # 过期后应重新计算
        assert get_value(5) == 10
        assert call_count == 2
    
    def test_cached_with_custom_key_func(self):
        """测试自定义缓存键"""
        call_count = 0
        
        def key_func(a, b):
            return f"{a}_{b}"
        
        @cached(ttl=60, key_func=key_func)
        def compute(a, b):
            nonlocal call_count
            call_count += 1
            return a + b
        
        assert compute(1, 2) == 3
        assert call_count == 1
        assert compute(1, 2) == 3
        assert call_count == 1
    
    def test_cached_clear(self):
        """测试清除缓存"""
        call_count = 0
        
        @cached(ttl=300)
        def get_value(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        get_value(5)
        assert call_count == 1
        get_value(5)
        assert call_count == 1
        
        get_value.clear_cache()
        
        get_value(5)
        assert call_count == 2


# ==================== RateLimiter 测试 ====================

class TestRateLimiter:
    """RateLimiter 限流器测试"""
    
    def test_rate_limiter_allows_within_limit(self):
        """测试限流器允许限制内的调用"""
        call_count = 0
        
        limiter = RateLimiter(max_calls=3, period=1.0)
        
        @limiter
        def task():
            nonlocal call_count
            call_count += 1
            return "done"
        
        for _ in range(3):
            result = task()
        
        assert call_count == 3
    
    def test_rate_limiter_blocks_excess(self):
        """测试超限时阻塞"""
        start_time = time.time()
        call_count = 0
        
        limiter = RateLimiter(max_calls=2, period=0.5)
        
        @limiter
        def task():
            nonlocal call_count
            call_count += 1
            return "done"
        
        task()
        task()
        task()  # 这应该被阻塞
        
        elapsed = time.time() - start_time
        assert call_count == 3
        assert elapsed >= 0.4  # 至少等待了一个周期
    
    def test_rate_limiter_window_slides(self):
        """测试时间窗口滑动"""
        limiter = RateLimiter(max_calls=2, period=0.3)
        
        @limiter
        def task():
            return "done"
        
        # 前两次立即通过
        task()
        task()
        
        # 等待窗口过期
        time.sleep(0.35)
        
        # 应该能再次调用
        start = time.time()
        task()
        elapsed = time.time() - start
        
        assert elapsed < 0.1  # 不应该被阻塞


# ==================== CircuitBreaker 测试 ====================

class TestCircuitBreaker:
    """CircuitBreaker 熔断器测试"""
    
    def test_circuit_breaker_closed_on_success(self):
        """测试成功时保持关闭状态"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        def success():
            return "ok"
        
        result = breaker.call(success)
        assert result == "ok"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_opens_on_failures(self):
        """测试失败达到阈值时打开"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        def fail():
            raise ValueError("error")
        
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(fail)
        
        assert breaker.state == "open"
        assert breaker.failure_count >= 3
    
    def test_circuit_breaker_open_blocks_calls(self):
        """测试打开状态拒绝调用 - 注意：阈值后的调用在达到恢复超时前会失败"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
        
        def fail():
            raise ValueError("error")
        
        # 前两次调用失败，达到阈值，熔断器打开
        with pytest.raises(ValueError):
            breaker.call(fail)
        with pytest.raises(ValueError):
            breaker.call(fail)
        
        assert breaker.state == "open"
        
        # 第三次调用在恢复超时前应该被拒绝
        with pytest.raises(Exception, match="Circuit breaker is open"):
            breaker.call(lambda: "not called")
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """测试超时后进入半开状态并成功恢复"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
        
        def fail():
            raise ValueError("error")
        
        # 触发熔断
        with pytest.raises(ValueError):
            breaker.call(fail)
        with pytest.raises(ValueError):
            breaker.call(fail)
        assert breaker.state == "open"
        
        # 等待恢复超时
        time.sleep(0.25)
        
        # 半开状态调用成功的函数，熔断器应关闭
        def success():
            return "recovered"
        
        result = breaker.call(success)
        assert result == "recovered"
        assert breaker.state == "closed"


# ==================== LazyProperty 测试 ====================

class TestLazyProperty:
    """LazyProperty 延迟属性测试"""
    
    def test_lazy_property_evaluated_once(self):
        """测试延迟属性只计算一次"""
        class MyClass:
            def __init__(self):
                self.eval_count = 0
            
            @LazyProperty
            def expensive_value(self):
                self.eval_count += 1
                return 42
        
        obj = MyClass()
        assert obj.eval_count == 0
        
        val1 = obj.expensive_value
        assert val1 == 42
        assert obj.eval_count == 1
        
        val2 = obj.expensive_value
        assert val2 == 42
        assert obj.eval_count == 1  # 不应再次计算
    
    def test_lazy_property_not_evaluated_until_accessed(self):
        """测试延迟属性首次访问才计算"""
        class MyClass:
            def __init__(self):
                self.initialized = False
            
            @LazyProperty
            def value(self):
                self.initialized = True
                return "computed"
        
        obj = MyClass()
        assert not obj.initialized
        
        _ = obj.value
        assert obj.initialized
    
    def test_lazy_property_with_arguments(self):
        """测试带参数的延迟属性"""
        class MyClass:
            def __init__(self, multiplier):
                self.multiplier = multiplier
                self.calc_count = 0
            
            @LazyProperty
            def computed(self):
                self.calc_count += 1
                return 10 * self.multiplier
        
        obj1 = MyClass(2)
        obj2 = MyClass(3)
        
        assert obj1.computed == 20
        assert obj1.calc_count == 1
        assert obj2.computed == 30
        assert obj2.calc_count == 1


# ==================== Validator 测试 ====================

class TestValidator:
    """Validator 验证器测试"""
    
    # required 验证
    def test_required_valid(self):
        assert Validator.required("hello", "name") == "hello"
        assert Validator.required(123, "number") == 123
    
    def test_required_none(self):
        with pytest.raises(ValueError, match="name is required"):
            Validator.required(None, "name")
    
    def test_required_empty_string(self):
        with pytest.raises(ValueError, match="name is required"):
            Validator.required("", "name")
    
    # min_length 验证
    def test_min_length_valid(self):
        assert Validator.min_length("hello", 3, "name") == "hello"
        assert Validator.min_length("hi", 2, "name") == "hi"
    
    def test_min_length_invalid(self):
        with pytest.raises(ValueError, match="name length must be at least 5"):
            Validator.min_length("hi", 5, "name")
    
    # max_length 验证
    def test_max_length_valid(self):
        assert Validator.max_length("hi", 5, "name") == "hi"
        assert Validator.max_length("hello", 10, "name") == "hello"
    
    def test_max_length_invalid(self):
        with pytest.raises(ValueError, match="name length must not exceed 3"):
            Validator.max_length("hello", 3, "name")
    
    # email 验证
    def test_email_valid(self):
        assert Validator.email("test@example.com") == "test@example.com"
        assert Validator.email("user.name@domain.co.uk") == "user.name@domain.co.uk"
    
    def test_email_invalid(self):
        with pytest.raises(ValueError, match="not a valid email"):
            Validator.email("invalid")
        with pytest.raises(ValueError, match="not a valid email"):
            Validator.email("test@")
        with pytest.raises(ValueError, match="not a valid email"):
            Validator.email("@domain.com")
    
    # url 验证
    def test_url_valid(self):
        assert Validator.url("http://example.com") == "http://example.com"
        assert Validator.url("https://domain.org/path") == "https://domain.org/path"
    
    def test_url_invalid(self):
        with pytest.raises(ValueError, match="not a valid URL"):
            Validator.url("not a url")
        with pytest.raises(ValueError, match="not a valid URL"):
            Validator.url("ftp://example.com")
    
    # ip 验证
    def test_ip_valid(self):
        assert Validator.ip("192.168.1.1") == "192.168.1.1"
        assert Validator.ip("0.0.0.0") == "0.0.0.0"
        assert Validator.ip("255.255.255.255") == "255.255.255.255"
    
    def test_ip_invalid_format(self):
        """测试IP格式无效"""
        with pytest.raises(ValueError, match="not a valid IP"):
            Validator.ip("not.an.ip")
        with pytest.raises(ValueError, match="not a valid IP"):
            Validator.ip("abc.def.ghi.jkl")
    
    # port 验证
    def test_port_valid(self):
        assert Validator.port(80) == 80
        assert Validator.port(1) == 1
        assert Validator.port(65535) == 65535
    
    def test_port_invalid(self):
        with pytest.raises(ValueError, match="not a valid port"):
            Validator.port(0)
        with pytest.raises(ValueError, match="not a valid port"):
            Validator.port(65536)
        with pytest.raises(ValueError, match="not a valid port"):
            Validator.port(-1)
    
    # in_range 验证
    def test_in_range_valid(self):
        assert Validator.in_range(5, 1, 10, "num") == 5
        assert Validator.in_range(1.0, 0.0, 2.0, "num") == 1.0
    
    def test_in_range_invalid(self):
        with pytest.raises(ValueError, match="must be between"):
            Validator.in_range(0, 1, 10, "num")
        with pytest.raises(ValueError, match="must be between"):
            Validator.in_range(15, 1, 10, "num")


# ==================== 密码函数测试 ====================

class TestPasswordFunctions:
    """hash_password, verify_password, generate_token 测试"""
    
    def test_hash_password_generates_hash_and_salt(self):
        """测试密码哈希生成"""
        password = "mysecretpassword"
        hashed, salt = hash_password(password)
        
        assert hashed is not None
        assert salt is not None
        assert len(hashed) > 0
        assert len(salt) > 0
    
    def test_hash_password_different_salts(self):
        """测试不同盐值生成不同哈希"""
        password = "samepassword"
        hash1, salt1 = hash_password(password)
        hash2, salt2 = hash_password(password)
        
        assert salt1 != salt2  # 随机盐
        assert hash1 != hash2  # 不同哈希
    
    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "correctpassword"
        hashed, salt = hash_password(password)
        
        assert verify_password(password, hashed, salt) is True
    
    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "correctpassword"
        hashed, salt = hash_password(password)
        
        assert verify_password("wrongpassword", hashed, salt) is False
    
    def test_verify_password_with_provided_salt(self):
        """测试使用提供的盐验证"""
        password = "testpassword"
        salt = os.urandom(32)
        hashed, _ = hash_password(password, salt)
        
        assert verify_password(password, hashed, _) is True
    
    def test_generate_token_length(self):
        """测试令牌长度"""
        token1 = generate_token(16)
        token2 = generate_token(32)
        
        # token_urlsafe 产生的字符串长度约为请求长度的 4/3
        assert len(token1) >= 16
        assert len(token2) >= 32
    
    def test_generate_token_uniqueness(self):
        """测试令牌唯一性"""
        tokens = [generate_token() for _ in range(100)]
        assert len(set(tokens)) == 100  # 全部唯一


# ==================== 工具函数测试 ====================

class TestUtilityFunctions:
    """deep_merge, to_snake_case, to_camel_case 测试"""
    
    # deep_merge
    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        
        result = deep_merge(base, override)
        
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_deep_merge_nested(self):
        """测试嵌套字典深度合并"""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 4}}
        
        result = deep_merge(base, override)
        
        assert result == {"a": {"x": 1, "y": 99, "z": 4}, "b": 3}
    
    def test_deep_merge_override_non_dict(self):
        """测试非字典值覆盖"""
        base = {"a": {"nested": 1}, "b": "string"}
        override = {"a": "replaced", "c": 3}
        
        result = deep_merge(base, override)
        
        assert result == {"a": "replaced", "b": "string", "c": 3}
    
    def test_deep_merge_empty_dicts(self):
        """测试空字典"""
        assert deep_merge({}, {}) == {}
        assert deep_merge({"a": 1}, {}) == {"a": 1}
        assert deep_merge({}, {"b": 2}) == {"b": 2}
    
    # to_snake_case
    def test_snake_case_simple(self):
        """测试简单驼峰转蛇形"""
        assert to_snake_case("helloWorld") == "hello_world"
        assert to_snake_case("HelloWorld") == "hello_world"
    
    def test_snake_case_already_snake(self):
        """测试已经是蛇形的保持不变"""
        assert to_snake_case("hello_world") == "hello_world"
        assert to_snake_case("hello") == "hello"
    
    def test_snake_case_with_numbers(self):
        """测试带数字的转换"""
        assert to_snake_case("user123Name") == "user123_name"
        assert to_snake_case("HTTPResponseCode") == "http_response_code"
    
    def test_snake_case_empty(self):
        """测试空字符串"""
        assert to_snake_case("") == ""
    
    # to_camel_case
    def test_camel_case_simple(self):
        """测试简单蛇形转驼峰"""
        assert to_camel_case("hello_world") == "helloWorld"
        assert to_camel_case("a_b_c") == "aBC"
    
    def test_camel_case_already_camel(self):
        """测试已经是驼峰的保持第一个词"""
        assert to_camel_case("helloWorld") == "helloWorld"
        assert to_camel_case("hello") == "hello"
    
    def test_camel_case_with_numbers(self):
        """测试带数字的转换"""
        assert to_camel_case("user123_name") == "user123Name"
    
    def test_camel_case_empty(self):
        """测试空字符串"""
        assert to_camel_case("") == ""


# ==================== Duration 函数测试 ====================

class TestDurationFunctions:
    """parse_duration, format_duration 测试"""
    
    # parse_duration
    def test_parse_seconds(self):
        """测试秒解析"""
        assert parse_duration("30") == 30.0
        assert parse_duration("0") == 0.0
    
    def test_parse_minutes(self):
        """测试分钟解析"""
        assert parse_duration("5m") == 300.0
        assert parse_duration("1m") == 60.0
    
    def test_parse_hours(self):
        """测试小时解析"""
        assert parse_duration("2h") == 7200.0
        assert parse_duration("1h") == 3600.0
    
    def test_parse_days(self):
        """测试天解析"""
        assert parse_duration("1d") == 86400.0
        assert parse_duration("3d") == 259200.0
    
    def test_parse_weeks(self):
        """测试周解析"""
        assert parse_duration("1w") == 604800.0
        assert parse_duration("2w") == 1209600.0
    
    def test_parse_duration_whitespace(self):
        """测试空白字符处理"""
        assert parse_duration("  30s  ") == 30.0
        assert parse_duration("5m ") == 300.0
    
    def test_parse_duration_invalid(self):
        """测试无效格式"""
        with pytest.raises(ValueError):
            parse_duration("invalid")
    
    # format_duration
    def test_format_seconds(self):
        """测试秒格式化"""
        assert format_duration(30) == "30.0s"
        assert format_duration(5.5) == "5.5s"
    
    def test_format_minutes(self):
        """测试分钟格式化"""
        assert format_duration(60) == "1.0m"
        assert format_duration(150) == "2.5m"
    
    def test_format_hours(self):
        """测试小时格式化"""
        assert format_duration(3600) == "1.0h"
        assert format_duration(7200) == "2.0h"
        assert format_duration(5400) == "1.5h"
    
    def test_format_days(self):
        """测试天格式化"""
        assert format_duration(86400) == "1.0d"
        assert format_duration(172800) == "2.0d"
    
    def test_format_zero(self):
        """测试零值"""
        assert format_duration(0) == "0.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
