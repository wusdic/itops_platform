"""
性能监控中间件
记录请求处理时间和性能指标
"""

import logging
import time
from typing import Dict, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件
    监控请求处理时间和系统性能指标
    """
    
    # 慢请求阈值（毫秒）
    SLOW_REQUEST_THRESHOLD_MS = 1000
    
    # 性能指标存储
    _metrics: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求"""
        # 记录开始时间
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # 获取请求路径模式（去除动态参数）
        path_pattern = self._get_path_pattern(request)
        
        # 更新性能指标
        self._update_metrics(path_pattern, duration_ms)
        
        # 如果是慢请求，记录警告
        if duration_ms > self.SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms"
            )
        
        # 在响应头中添加处理时间
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
    def _get_path_pattern(self, request: Request) -> str:
        """
        获取请求路径模式
        将动态参数替换为占位符，便于统计
        """
        path = request.url.path
        
        # 简单的模式提取（实际应用中可以使用更复杂的路由模式解析）
        # 例如: /api/v1/workorder/123 -> /api/v1/workorder/{id}
        segments = path.split("/")
        pattern_parts = []
        
        for i, segment in enumerate(segments):
            # 判断是否是数字ID
            if segment.isdigit():
                pattern_parts.append("{id}")
            # 判断是否是UUID
            elif self._is_uuid(segment):
                pattern_parts.append("{uuid}")
            else:
                pattern_parts.append(segment)
        
        return "/".join(pattern_parts)
    
    def _is_uuid(self, value: str) -> bool:
        """判断是否是UUID"""
        if len(value) == 36 and value.count("-") == 4:
            return True
        return False
    
    def _update_metrics(self, path_pattern: str, duration_ms: float):
        """更新性能指标"""
        if path_pattern not in self._metrics:
            self._metrics[path_pattern] = []
        
        # 保留最近1000条记录
        self._metrics[path_pattern].append(duration_ms)
        if len(self._metrics[path_pattern]) > 1000:
            self._metrics[path_pattern] = self._metrics[path_pattern][-1000:]
    
    @classmethod
    def get_metrics(cls) -> Dict[str, Dict[str, float]]:
        """获取性能指标统计"""
        result = {}
        for path, durations in cls._metrics.items():
            if durations:
                result[path] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations), 2),
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2),
                }
        return result
    
    @classmethod
    def clear_metrics(cls):
        """清空性能指标"""
        cls._metrics.clear()
