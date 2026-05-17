"""
自动化触发全链路日志记录器
每次设备指标采集后，记录完整的触发评估流程
"""
import asyncio
import time
import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("/tmp/auto_trigger_trace.log")

def log_event(step: str, data: dict):
    """追加日志到文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = json.dumps({
        "time": timestamp,
        "step": step,
        **data
    }, ensure_ascii=False)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"[TRACE {timestamp}] {step}: {json.dumps(data, ensure_ascii=False)}")


class TriggerTracer:
    """触发链路追踪器"""

    def __init__(self):
        self.step = 0
        self.trace_id = datetime.now().strftime("%H%M%S")

    def next(self, step: str, data: dict):
        self.step += 1
        prefix = f"[#{self.step:02d}]"
        log_event(f"{prefix} {step}", data)

    def marker(self, label: str):
        sep = "=" * 60
        marker = f"[TRACE MARKER] {label} @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sep + "\n")
            f.write(marker + "\n")
            f.write(sep + "\n")
        print(marker)


tracer = TriggerTracer()


def on_device_metrics(metrics: list):
    """DeviceManager 采集完成后的 callback"""
    tracer.marker(f"🔔 DEVICE_COLLECT_DONE | 收到 {len(metrics)} 条指标")
    tracer.next("设备指标原始数据", {
        "device_count": len(metrics),
        "sample": metrics[0] if metrics else None
    })

    # 模拟：送入触发服务的_pending_metrics
    from modules.automation.automation_background import get_trigger_service
    svc = get_trigger_service()

    tracer.next("送入触发服务", {
        "pending_before": len(svc._pending_metrics),
        "incoming": len(metrics)
    })

    for m in metrics:
        svc._pending_metrics.append(m)

    tracer.next("进入待评估队列", {
        "pending_after": len(svc._pending_metrics),
        "first_item": svc._pending_metrics[0] if svc._pending_metrics else None
    })

    # 立即触发一次评估（模拟定时器到期）
    tracer.marker("⏰ EVALUATE_TRIGGERED | 定时器到期，开始评估")
    asyncio.create_task(svc._evaluate_pending_metrics())


async def trace_evaluate_loop():
    """追踪评估循环"""
    from modules.automation.automation_background import get_trigger_service
    svc = get_trigger_service()

    # 注册 tracer callback
    original_cb = svc._device_metrics_callback
    svc._device_metrics_callback = on_device_metrics

    tracer.marker("🚀 TRACER_REGISTERED | callback 已注册到触发服务")
    tracer.next("注册状态", {
        "callback_registered": svc._device_metrics_callback == on_device_metrics,
        "interval_seconds": svc._check_interval
    })

    # 手动触发一次采集
    tracer.marker("🔧 MANUAL_COLLECT | 手动触发设备采集")
    from modules.devices.device_manager import device_manager
    await device_manager.collect_all()

    # 等待评估完成
    await asyncio.sleep(5)

    tracer.marker("🏁 TRACE_COMPLETE")
    return LOG_FILE


if __name__ == "__main__":
    asyncio.run(trace_evaluate_loop())
