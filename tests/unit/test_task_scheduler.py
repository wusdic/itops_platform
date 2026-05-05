"""AM-01 任务调度模块单元测试"""
import os
import sys
import asyncio
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor

import pytest

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestTaskScheduler:
    """任务调度器测试"""
    
    @pytest.fixture
    def scheduler(self):
        """创建调度器"""
        from modules.automation.task_scheduler.scheduler import TaskScheduler
        
        sched = TaskScheduler(timezone="Asia/Shanghai")
        yield sched
        if sched.is_running():
            sched.stop()
    
    def test_scheduler_init(self, scheduler):
        """测试调度器初始化"""
        assert scheduler.timezone == "Asia/Shanghai"
        assert scheduler._running is False
    
    def test_scheduler_start_stop(self, scheduler):
        """测试调度器启停"""
        scheduler.start()
        assert scheduler.is_running() is True
        
        scheduler.stop()
        assert scheduler.is_running() is False
    
    def test_add_cron_job(self, scheduler):
        """测试添加Cron任务"""
        scheduler.start()
        
        def dummy_job():
            return "executed"
        
        job_id = scheduler.add_cron_job(
            func=dummy_job,
            cron="*/5 * * * *",
            name="Test Cron Job"
        )
        
        assert job_id is not None
        
        jobs = scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]['name'] == "Test Cron Job"
        assert jobs[0]['trigger_type'] == 'cron'
    
    def test_add_interval_job(self, scheduler):
        """测试添加间隔任务"""
        scheduler.start()
        
        job_count = [0]
        
        def counter_job():
            job_count[0] += 1
        
        job_id = scheduler.add_interval_job(
            func=counter_job,
            interval=1,
            unit="seconds",
            name="Counter Job"
        )
        
        assert job_id is not None
        
        jobs = scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]['trigger_type'] == 'interval'
    
    def test_add_once_job(self, scheduler):
        """测试添加一次性任务"""
        scheduler.start()
        
        result = []
        
        def one_time_job():
            result.append("executed")
        
        job_id = scheduler.add_once_job(
            func=one_time_job,
            run_date=datetime.now() + timedelta(seconds=1),
            name="One Time Job"
        )
        
        assert job_id is not None
        
        job = scheduler.get_job(job_id)
        assert job is not None
        assert job.trigger_type.value == 'once'
    
    def test_pause_resume_job(self, scheduler):
        """测试暂停恢复任务"""
        scheduler.start()
        
        def dummy_job():
            pass
        
        job_id = scheduler.add_interval_job(
            func=dummy_job,
            interval=60,
            name="Pause Test Job"
        )
        
        scheduler.pause_job(job_id)
        job = scheduler.get_job(job_id)
        assert job.status == "paused"
        
        scheduler.resume_job(job_id)
        job = scheduler.get_job(job_id)
        assert job.status == "pending"
    
    def test_remove_job(self, scheduler):
        """测试移除任务"""
        scheduler.start()
        
        def dummy_job():
            pass
        
        job_id = scheduler.add_interval_job(
            func=dummy_job,
            interval=60,
            name="Remove Test Job"
        )
        
        assert len(scheduler.list_jobs()) == 1
        
        scheduler.remove_job(job_id)
        assert len(scheduler.list_jobs()) == 0
        assert scheduler.get_job(job_id) is None
    
    def test_cron_expression_parsing(self, scheduler):
        """测试Cron表达式解析"""
        cron_expr = "0 */5 * * *"
        result = scheduler._parse_cron(cron_expr)
        
        assert result['minute'] == '0'
        assert result['hour'] == '*/5'
        assert result['day'] == '*'
        assert result['month'] == '*'


class TestTask:
    """任务测试"""
    
    def test_task_base_init(self):
        """测试任务基类初始化"""
        from modules.automation.task_scheduler.task import Task, TaskStatus
        
        task = Task(
            task_id="test-001",
            name="Test Task",
            description="A test task"
        )
        
        assert task.task_id == "test-001"
        assert task.name == "Test Task"
        assert task.description == "A test task"
        assert task.validate() is True
    
    def test_collection_task(self):
        """测试采集任务"""
        from modules.automation.task_scheduler.task import CollectionTask
        
        task = CollectionTask(
            task_id="collect-001",
            name="Data Collection",
            collector_type="snmp",
            target="192.168.1.1",
            interval=300
        )
        
        assert task.collector_type == "snmp"
        assert task.target == "192.168.1.1"
        assert task.interval == 300
    
    @pytest.mark.asyncio
    async def test_collection_task_execute(self):
        """测试采集任务执行"""
        from modules.automation.task_scheduler.task import CollectionTask
        
        task = CollectionTask(
            task_id="collect-002",
            name="Test Collection",
            collector_type="log",
            target="/var/log/test.log"
        )
        
        result = await task.execute({})
        
        assert result.success is True
        assert result.data is not None
    
    def test_report_task(self):
        """测试报告任务"""
        from modules.automation.task_scheduler.task import ReportTask
        
        task = ReportTask(
            task_id="report-001",
            name="Daily Report",
            report_type="daily",
            recipients=["admin@example.com"],
            output_format="pdf"
        )
        
        assert task.report_type == "daily"
        assert "admin@example.com" in task.recipients
        assert task.output_format == "pdf"
    
    def test_script_task(self):
        """测试脚本任务"""
        from modules.automation.task_scheduler.task import ScriptTask
        
        task = ScriptTask(
            task_id="script-001",
            name="Shell Script",
            script_type="shell",
            script_content="echo 'Hello'"
        )
        
        assert task.script_type == "shell"
        assert task.script_content == "echo 'Hello'"
    
    def test_workflow_task(self):
        """测试工作流任务"""
        from modules.automation.task_scheduler.task import WorkflowTask
        
        task = WorkflowTask(
            task_id="workflow-001",
            name="Test Workflow",
            steps=[
                {"name": "Step 1", "type": "delay", "config": {"seconds": 1}},
                {"name": "Step 2", "type": "condition", "config": {"condition": "True"}},
            ],
            continue_on_error=False
        )
        
        assert len(task.steps) == 2
        assert task.continue_on_error is False
    
    @pytest.mark.asyncio
    async def test_workflow_execute(self):
        """测试工作流执行"""
        from modules.automation.task_scheduler.task import WorkflowTask
        
        task = WorkflowTask(
            task_id="workflow-002",
            name="Simple Workflow",
            steps=[
                {"name": "Delay", "type": "delay", "config": {"seconds": 0}},
            ]
        )
        
        result = await task.execute({})
        
        assert result.success is True
        assert result.data['total_steps'] == 1


class TestTaskExecutor:
    """任务执行器测试"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器"""
        from modules.automation.task_scheduler.executor import TaskExecutor
        
        exec = TaskExecutor(
            max_workers=4,
            default_timeout=10,
            default_retry_count=1
        )
        yield exec
        exec.shutdown()
    
    def test_executor_init(self, executor):
        """测试执行器初始化"""
        assert executor.max_workers == 4
        assert executor.default_timeout == 10
        assert executor.default_retry_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_simple_task(self, executor):
        """测试执行简单任务"""
        from modules.automation.task_scheduler.task import Task, TaskStatus, TaskResult
        
        class SimpleTask(Task):
            async def execute(self, context):
                await asyncio.sleep(0.1)
                return TaskResult(success=True, data={"status": "done"})
        
        task = SimpleTask(task_id="simple-001", name="Simple Task")
        result = await executor.execute(task)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        """测试超时执行"""
        from modules.automation.task_scheduler.task import Task
        
        class SlowTask(Task):
            async def execute(self, context):
                await asyncio.sleep(10)  # 10秒
                return TaskResult(success=True)
        
        task = SlowTask(task_id="slow-001", name="Slow Task")
        result = await executor.execute(task, timeout=1)
        
        assert result.success is False
        assert "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_with_retry(self, executor):
        """测试重试机制"""
        from modules.automation.task_scheduler.task import Task
        
        class FailingTask(Task):
            attempt = 0
            
            async def execute(self, context):
                FailingTask.attempt += 1
                if FailingTask.attempt < 3:
                    raise Exception("Temporary failure")
                return TaskResult(success=True)
        
        FailingTask.attempt = 0
        
        task = FailingTask(
            task_id="fail-001",
            name="Failing Task",
            retry_count=3,
            retry_delay=0
        )
        
        result = await executor.execute(task)
        
        assert result.success is True
        assert FailingTask.attempt == 3
    
    @pytest.mark.asyncio
    async def test_batch_execution(self, executor):
        """测试批量执行"""
        from modules.automation.task_scheduler.task import Task
        
        class BatchTask(Task):
            async def execute(self, context):
                return TaskResult(success=True)
        
        tasks = [
            BatchTask(task_id=f"batch-{i}", name=f"Batch Task {i}")
            for i in range(5)
        ]
        
        results = await executor.execute_batch(tasks, max_concurrent=3)
        
        assert len(results) == 5
        assert all(r.success for r in results)


class TestTaskMonitor:
    """任务监控测试"""
    
    @pytest.fixture
    def monitor(self):
        """创建监控器"""
        from modules.automation.task_scheduler.monitor import TaskMonitor
        
        mon = TaskMonitor(
            alert_threshold={
                'failure_rate': 0.5,
                'consecutive_failures': 2,
            }
        )
        return mon
    
    def test_monitor_init(self, monitor):
        """测试监控器初始化"""
        assert monitor.alert_threshold['failure_rate'] == 0.5
        assert monitor.alert_threshold['consecutive_failures'] == 2
    
    def test_record_task_start(self, monitor):
        """测试记录任务开始"""
        from modules.automation.task_scheduler.task import Task, TaskExecution
        from modules.automation.task_scheduler.task import TaskStatus
        
        task = Task(task_id="monitor-001", name="Monitor Test")
        execution = TaskExecution(
            execution_id="exec-001",
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now()
        )
        
        monitor.record_task_start(task, execution)
        
        metrics = monitor.get_metrics()
        assert metrics['performance']['total_tasks'] == 1
        assert metrics['performance']['running_tasks'] == 1
    
    def test_record_task_complete(self, monitor):
        """测试记录任务完成"""
        from modules.automation.task_scheduler.task import Task, TaskExecution, TaskResult
        from modules.automation.task_scheduler.task import TaskStatus
        
        task = Task(task_id="monitor-002", name="Monitor Test 2")
        execution = TaskExecution(
            execution_id="exec-002",
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            start_time=datetime.now()
        )
        execution.mark_success(data={"result": "ok"})
        
        monitor.record_task_complete(task, execution)
        
        metrics = monitor.get_metrics()
        assert metrics['performance']['completed_tasks'] == 1
        assert metrics['performance']['running_tasks'] == 0
    
    def test_alert_triggering(self, monitor):
        """测试告警触发"""
        from modules.automation.task_scheduler.task import Task, TaskExecution
        from modules.automation.task_scheduler.task import TaskStatus
        
        # 记录多次失败
        for i in range(3):
            task = Task(task_id=f"fail-{i}", name=f"Failed Task {i}")
            execution = TaskExecution(
                execution_id=f"exec-fail-{i}",
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                start_time=datetime.now()
            )
            execution.mark_failed("Test error")
            
            monitor.record_task_complete(task, execution)
        
        alerts = monitor.get_alerts(resolved=False)
        assert len(alerts) > 0
    
    def test_performance_metrics(self, monitor):
        """测试性能指标"""
        perf = monitor.get_performance()
        
        data = perf.to_dict()
        
        assert 'total_tasks' in data
        assert 'success_rate' in data
        assert 'avg_duration' in data


class TestDistributedScheduler:
    """分布式调度器测试"""
    
    def test_distributed_scheduler_init(self):
        """测试分布式调度器初始化"""
        from modules.automation.task_scheduler.distributed import DistributedScheduler
        
        scheduler = DistributedScheduler(
            node_id="test-node-1",
            host="localhost",
            port=8765
        )
        
        assert scheduler.node_id == "test-node-1"
        assert scheduler.is_leader is False
        assert scheduler.role.value == "follower"
    
    def test_cluster_status(self):
        """测试集群状态"""
        from modules.automation.task_scheduler.distributed import DistributedScheduler
        
        scheduler = DistributedScheduler(
            node_id="test-node-1",
            host="localhost",
            port=8765,
            cluster_nodes=[
                {"node_id": "node-2", "host": "localhost", "port": 8766}
            ]
        )
        
        status = scheduler.get_cluster_status()
        
        assert status['node_id'] == "test-node-1"
        assert status['role'] == "follower"
        assert len(status['nodes']) == 2  # 包含自己和另一个节点
    
    def test_task_sharding(self):
        """测试任务分片"""
        from modules.automation.task_scheduler.distributed import DistributedScheduler
        
        scheduler = DistributedScheduler(
            node_id="test-node-1",
            host="localhost",
            port=8765
        )
        
        # 创建分片
        shards = scheduler.create_shards("test-task", 3)
        
        assert len(shards) == 3
        
        # 所有分片都分配给了本节点（单机模式）
        for shard in shards:
            assert shard.assigned_node == "test-node-1"
    
    def test_is_task_owned(self):
        """测试任务所有权"""
        from modules.automation.task_scheduler.distributed import DistributedScheduler
        
        scheduler = DistributedScheduler(
            node_id="test-node-1",
            host="localhost",
            port=8765
        )
        
        # 单机模式，所有任务都归本节点
        assert scheduler.is_task_owned("any-task") is True


class TestTaskRegistry:
    """任务注册表测试"""
    
    def test_registry_init(self):
        """测试注册表初始化"""
        from modules.automation.task_scheduler.task import TaskRegistry
        
        registry = TaskRegistry()
        
        assert len(registry.list_all()) == 0
    
    def test_register_task(self):
        """测试注册任务"""
        from modules.automation.task_scheduler.task import TaskRegistry, Task
        
        registry = TaskRegistry()
        
        task = Task(task_id="reg-001", name="Registered Task")
        registry.register(task)
        
        assert len(registry.list_all()) == 1
        assert registry.get("reg-001") is task
    
    def test_create_task(self):
        """测试创建任务"""
        from modules.automation.task_scheduler.task import TaskRegistry, CollectionTask
        
        registry = TaskRegistry()
        
        task = registry.create_task(
            'collection',
            task_id="create-001",
            name="Created Task",
            collector_type="snmp"
        )
        
        assert isinstance(task, CollectionTask)
        assert task.collector_type == "snmp"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
