# -*- coding: utf-8 -*-
"""
ITOps Platform - Base Collector
采集器基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio


@dataclass
class CollectorConfig:
    """采集器配置"""
    name: str
    enabled: bool = True
    interval: int = 60  # 秒
    timeout: int = 30
    retry: int = 3
    retry_delay: float = 5.0


class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, config: CollectorConfig):
        self.config = config
        self._running = False
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[Dict] = None
    
    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """执行采集"""
        raise NotImplementedError
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        raise NotImplementedError
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def last_result(self) -> Optional[Dict]:
        return self._last_result
    
    async def run_once(self) -> Dict[str, Any]:
        """执行一次采集"""
        self._running = True
        try:
            self._last_result = await self.collect()
            self._last_run = datetime.now()
            return self._last_result
        finally:
            self._running = False
    
    async def run_periodic(self):
        """周期性执行采集"""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                print(f"采集异常: {e}")
            
            await asyncio.sleep(self.config.interval)
    
    def start(self):
        """启动采集"""
        self._running = True
        asyncio.create_task(self.run_periodic())
    
    def stop(self):
        """停止采集"""
        self._running = False
