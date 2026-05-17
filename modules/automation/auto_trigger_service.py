"""
自动化触发服务
将设备指标数据接入触发引擎，实现真正的自动触发
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# 全局触发服务实例
_trigger_service: Optional['_AutomationTriggerService'] = None


class _AutomationTriggerService:
    """自动化触发服务"""

    def __init__(self):
        self._enabled = True
        self._trigger_engine = None
        self._evaluation_interval = 60  # 批量评估间隔（秒）
        self._pending_metrics = {}  # 待评估的指标数据
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def _init_trigger_engine(self):
        """使用API路由的触发引擎实例（共享规则）"""
        if self._trigger_engine is None:
            from modules.automation.alert_trigger.trigger import AlertTriggerEngine
            from api.routes.automation import _trigger_engine as api_engine
            # 使用API路由的engine（规则在此注册）
            self._trigger_engine = api_engine
            logger.info("Using API route's trigger engine for automation service")

    def on_device_metrics(self, metrics) -> None:
        """
        DeviceManager 采集回调 - 每个设备采集完都会触发
        将指标数据加入待评估队列
        """
        if not self._enabled:
            return

        try:
            device_name = metrics.device_name
            self._pending_metrics[device_name] = {
                'device_id': getattr(metrics, 'device_id', 0),
                'device_name': device_name,
                'device_ip': getattr(metrics, 'ip_address', ''),
                'metrics': {},
                'timestamp': metrics.timestamp,
            }

            # 提取指标数据
            if hasattr(metrics, 'cpu_usage'):
                self._pending_metrics[device_name]['metrics']['cpu_usage'] = metrics.cpu_usage
            if hasattr(metrics, 'memory_usage'):
                self._pending_metrics[device_name]['metrics']['memory_usage'] = metrics.memory_usage
            if hasattr(metrics, 'disk_usage'):
                self._pending_metrics[device_name]['metrics']['disk_usage'] = metrics.disk_usage
            if hasattr(metrics, 'network_in') and hasattr(metrics, 'network_out'):
                self._pending_metrics[device_name]['metrics']['network_in'] = metrics.network_in
                self._pending_metrics[device_name]['metrics']['network_out'] = metrics.network_out

            # 其他自定义指标（从 metrics dict 中获取）
            if hasattr(metrics, 'metrics') and isinstance(metrics.metrics, dict):
                self._pending_metrics[device_name]['metrics'].update(metrics.metrics)

        except Exception as e:
            logger.error(f"处理设备指标回调失败: {e}")

    async def _evaluation_loop(self) -> None:
        """
        批量评估循环 - 每隔一段时间对所有待评估指标进行触发评估
        """
        self._running = True
        logger.info("Automation trigger evaluation loop started")

        while self._running:
            try:
                await asyncio.sleep(self._evaluation_interval)
                await self._evaluate_pending_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"评估循环异常: {e}")

        logger.info("Automation trigger evaluation loop stopped")

    async def _evaluate_pending_metrics(self) -> None:
        """对所有待评估指标执行触发评估"""
        if not self._pending_metrics:
            return

        self._init_trigger_engine()

        triggered_count = 0
        for device_name, data in list(self._pending_metrics.items()):
            try:
                for metric_name, value in data['metrics'].items():
                    if not isinstance(value, (int, float)):
                        continue

                    # 调用触发引擎评估
                    triggered_events = await self._trigger_engine.evaluate_and_trigger(
                        metric_name=metric_name,
                        value=float(value),
                        device_id=data.get('device_id', 0),
                        device_name=data['device_name'],
                        device_ip=data.get('device_ip', ''),
                    )

                    if triggered_events:
                        triggered_count += len(triggered_events)
                        for event in triggered_events:
                            logger.info(
                                f"Automation triggered: rule={event.rule_name}, "
                                f"device={data['device_name']}, metric={metric_name}, value={value}"
                            )

            except Exception as e:
                logger.error(f"评估设备 {device_name} 指标时出错: {e}")

        # 清空已评估的指标
        if triggered_count > 0:
            logger.info(f"本次评估共触发 {triggered_count} 个事件")

        self._pending_metrics.clear()

    async def start(self) -> None:
        """启动触发服务"""
        self._task = asyncio.create_task(self._evaluation_loop())
        logger.info("Automation trigger service started")

    def get_events(self) -> List:
        """获取所有触发事件（从engine内部存储读取）"""
        self._init_trigger_engine()
        if self._trigger_engine is not None and hasattr(self._trigger_engine, '_events'):
            return list(self._trigger_engine._events.values())
        return []

    async def stop(self) -> None:
        """停止触发服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Automation trigger service stopped")


def get_trigger_service() -> _AutomationTriggerService:
    """获取触发服务单例"""
    global _trigger_service
    if _trigger_service is None:
        _trigger_service = _AutomationTriggerService()
    return _trigger_service
