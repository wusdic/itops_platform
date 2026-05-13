"""
AUTO-023 执行失败自动回滚 - 单元测试

测试 RollbackManager、快照保存和自动回滚功能
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.automation.script_executor.rollback import (
    RollbackManager,
    RollbackStatus,
    RollbackResult,
    Snapshot,
    SnapshotType,
    get_rollback_manager,
)
from modules.automation.script_executor.executor import (
    ScriptExecutor,
    Script,
    ScriptType,
    ExecutionStatus,
)


class TestRollbackManager(unittest.TestCase):
    """测试回滚管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp(prefix="rollback_test_")
        self.manager = RollbackManager(storage_path=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_checkpoint(self):
        """测试保存检查点"""
        execution_id = "test_exec_001"
        
        snapshot = self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
            data={'test': 'data', 'value': 123},
            metadata={'author': 'test'},
        )
        
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.execution_id, execution_id)
        self.assertEqual(snapshot.snapshot_type, SnapshotType.SCRIPT_OUTPUT)
        self.assertEqual(snapshot.data['test'], 'data')
        self.assertEqual(snapshot.data['value'], 123)
        self.assertEqual(snapshot.metadata['author'], 'test')
        self.assertTrue(len(snapshot.checksum) > 0)
    
    def test_save_checkpoint_with_creator(self):
        """测试使用注册的创建器保存检查点"""
        execution_id = "test_exec_002"
        
        # 注册一个创建器
        self.manager.register_snapshot_creator(
            SnapshotType.DEVICE_CONFIG,
            lambda exec_id: {
                'exec_id': exec_id,
                'configs': [{'hostname': 'test-router', 'running_config': 'sample'}]
            }
        )
        
        # 不提供data，使用创建器生成
        snapshot = self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.DEVICE_CONFIG,
        )
        
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.data['exec_id'], execution_id)
        self.assertEqual(snapshot.data['configs'][0]['hostname'], 'test-router')
    
    def test_get_snapshot(self):
        """测试获取快照"""
        execution_id = "test_exec_003"
        
        # 保存快照
        saved = self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
            data={'key': 'value'},
        )
        
        # 获取快照
        retrieved = self.manager.get_snapshot(execution_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, saved.id)
        self.assertEqual(retrieved.execution_id, execution_id)
        self.assertEqual(retrieved.data['key'], 'value')
    
    def test_get_snapshot_not_found(self):
        """测试获取不存在的快照"""
        result = self.manager.get_snapshot("nonexistent_exec")
        self.assertIsNone(result)
    
    def test_execute_rollback_with_script(self):
        """测试执行回滚（带脚本）"""
        execution_id = "test_exec_004"
        
        # 保存快照
        self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
            data={'original': 'state'},
        )
        
        # 注册回滚脚本执行器
        def mock_executor(script, params):
            return {
                'script': script[:50] if script else '',
                'params': params,
                'executed': True,
            }
        self.manager.register_rollback_script_executor(mock_executor)
        
        # 执行回滚
        result = self.manager.execute_rollback(
            execution_id=execution_id,
            rollback_script='echo "Rolling back..."',
            rollback_params={'reason': 'test failure'},
        )
        
        self.assertEqual(result.status, RollbackStatus.SUCCESS)
        self.assertIsNotNone(result.snapshot_id)
        self.assertIn('executed', result.rollback_script_result)
        self.assertTrue(result.rollback_script_result['executed'])
    
    def test_execute_rollback_without_script(self):
        """测试执行回滚（不带脚本）"""
        execution_id = "test_exec_005"
        
        # 保存快照
        self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
        )
        
        # 执行回滚（不提供脚本）
        result = self.manager.execute_rollback(execution_id=execution_id)
        
        self.assertEqual(result.status, RollbackStatus.SUCCESS)
        self.assertIsNotNone(result.snapshot_id)
    
    def test_execute_rollback_not_found(self):
        """测试执行回滚（快照不存在）"""
        result = self.manager.execute_rollback(execution_id="nonexistent")
        
        self.assertEqual(result.status, RollbackStatus.NOT_FOUND)
        self.assertIn("No snapshot found", result.message)
    
    def test_delete_snapshot(self):
        """测试删除快照"""
        execution_id = "test_exec_006"
        
        # 保存快照
        self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
        )
        
        # 验证存在
        self.assertIsNotNone(self.manager.get_snapshot(execution_id))
        
        # 删除
        deleted = self.manager.delete_snapshot(execution_id)
        self.assertTrue(deleted)
        
        # 验证不存在
        self.assertIsNone(self.manager.get_snapshot(execution_id))
    
    def test_list_snapshots(self):
        """测试列出快照"""
        # 保存多个快照
        for i in range(5):
            self.manager.save_checkpoint(
                execution_id=f"test_exec_{i}",
                snapshot_type=SnapshotType.SCRIPT_OUTPUT,
                data={'index': i},
            )
        
        snapshots = self.manager.list_snapshots(limit=10)
        self.assertEqual(len(snapshots), 5)
    
    def test_get_rollback_history(self):
        """测试获取回滚历史"""
        execution_id = "test_exec_history"
        
        # 保存快照
        self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
        )
        
        # 执行回滚
        self.manager.execute_rollback(execution_id=execution_id)
        
        # 获取历史
        history = self.manager.get_rollback_history(limit=10)
        self.assertGreaterEqual(len(history), 1)
        
        # 按execution_id过滤
        filtered = self.manager.get_rollback_history(execution_id=execution_id)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].execution_id, execution_id)
    
    def test_cleanup_old_snapshots(self):
        """测试清理旧快照"""
        # 保存一个快照
        execution_id = "test_exec_cleanup"
        self.manager.save_checkpoint(
            execution_id=execution_id,
            snapshot_type=SnapshotType.SCRIPT_OUTPUT,
        )
        
        # 清理（1小时后 - 应该不会删除）
        deleted = self.manager.cleanup_old_snapshots(max_age_hours=1)
        self.assertEqual(deleted, 0)
        
        # 清理（0小时前 - 应该删除）
        deleted = self.manager.cleanup_old_snapshots(max_age_hours=0)
        self.assertEqual(deleted, 1)


class TestSnapshotType(unittest.TestCase):
    """测试快照类型枚举"""
    
    def test_snapshot_types(self):
        """验证快照类型"""
        self.assertEqual(SnapshotType.DEVICE_CONFIG.value, "device_config")
        self.assertEqual(SnapshotType.DATABASE_STATE.value, "database_state")
        self.assertEqual(SnapshotType.SCRIPT_OUTPUT.value, "script_output")
        self.assertEqual(SnapshotType.FULL_SYSTEM.value, "full_system")


class TestRollbackStatus(unittest.TestCase):
    """测试回滚状态枚举"""
    
    def test_rollback_statuses(self):
        """验证回滚状态"""
        self.assertEqual(RollbackStatus.PENDING.value, "pending")
        self.assertEqual(RollbackStatus.RUNNING.value, "running")
        self.assertEqual(RollbackStatus.SUCCESS.value, "success")
        self.assertEqual(RollbackStatus.FAILED.value, "failed")
        self.assertEqual(RollbackStatus.NOT_FOUND.value, "not_found")


class TestScriptExecutorRollback(unittest.TestCase):
    """测试 ScriptExecutor 的回滚功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp(prefix="executor_rollback_test_")
        self.executor = ScriptExecutor()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_checkpoint_via_executor(self):
        """测试通过执行器保存检查点"""
        execution_id = "executor_test_001"
        
        snapshot = self.executor.save_checkpoint(
            execution_id=execution_id,
            snapshot_type="device_config",
            data={'config': 'test'},
            metadata={'author': 'tester'},
        )
        
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.execution_id, execution_id)
    
    def test_get_snapshot_via_executor(self):
        """测试通过执行器获取快照"""
        execution_id = "executor_test_002"
        
        # 保存
        self.executor.save_checkpoint(
            execution_id=execution_id,
            snapshot_type="script_output",
            data={'output': 'test'},
        )
        
        # 获取
        retrieved = self.executor.get_snapshot(execution_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.execution_id, execution_id)
    
    def test_script_with_rollback(self):
        """测试带回滚功能的脚本"""
        # 创建一个会失败的脚本，但启用了自动回滚
        script = Script(
            name="rollback_test_script",
            script_type=ScriptType.SHELL,
            content="exit 1",  # 失败
            rollback_script='echo "Rolling back..."',
            enable_auto_rollback=True,
        )
        
        result = self.executor.execute(script=script)
        
        # 验证执行失败
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        
        # 验证快照被保存
        snapshot = self.executor.get_snapshot(result.task_id)
        self.assertIsNotNone(snapshot)
    
    def test_script_without_rollback(self):
        """测试不带回滚功能的脚本"""
        # 创建失败的脚本，但没有启用自动回滚
        script = Script(
            name="no_rollback_script",
            script_type=ScriptType.SHELL,
            content="exit 1",
            enable_auto_rollback=False,
        )
        
        result = self.executor.execute(script=script)
        
        # 验证执行失败
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        
        # 验证没有触发回滚（因为没有启用）
        # 快照仍会保存（失败时总是保存）
        snapshot = self.executor.get_snapshot(result.task_id)
        # 注意：即使没有enable_auto_rollback，快照也会保存用于后续手动回滚
        self.assertIsNotNone(snapshot)
    
    def test_successful_script_no_rollback(self):
        """测试成功的脚本不触发回滚"""
        script = Script(
            name="success_script",
            script_type=ScriptType.SHELL,
            content="echo 'Success'",
            rollback_script='echo "Should not run"',
            enable_auto_rollback=True,
        )
        
        result = self.executor.execute(script=script)
        
        # 验证执行成功
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        
        # 验证没有回滚标记
        self.assertNotIn("Auto-rollback", result.error_message or "")


class TestRollbackResult(unittest.TestCase):
    """测试回滚结果数据类"""
    
    def test_rollback_result_to_dict(self):
        """测试回滚结果转换为字典"""
        result = RollbackResult(
            execution_id="test_exec",
            status=RollbackStatus.SUCCESS,
            snapshot_id="snapshot_123",
            rollback_script_result={'executed': True},
            message="Success",
            duration=1.5,
        )
        
        data = result.to_dict()
        
        self.assertEqual(data['execution_id'], "test_exec")
        self.assertEqual(data['status'], "success")
        self.assertEqual(data['snapshot_id'], "snapshot_123")
        self.assertEqual(data['rollback_script_result']['executed'], True)
        self.assertEqual(data['message'], "Success")
        self.assertEqual(data['duration'], 1.5)


class TestSnapshot(unittest.TestCase):
    """测试快照数据类"""
    
    def test_snapshot_to_dict(self):
        """测试快照转换为字典"""
        snapshot = Snapshot(
            id="snapshot_001",
            execution_id="exec_001",
            snapshot_type=SnapshotType.DEVICE_CONFIG,
            data={'key': 'value'},
            metadata={'author': 'test'},
            checksum="abc123",
        )
        
        data = snapshot.to_dict()
        
        self.assertEqual(data['id'], "snapshot_001")
        self.assertEqual(data['execution_id'], "exec_001")
        self.assertEqual(data['snapshot_type'], "device_config")
        self.assertEqual(data['data']['key'], 'value')
        self.assertEqual(data['metadata']['author'], 'test')
        self.assertEqual(data['checksum'], "abc123")


class TestGlobalRollbackManager(unittest.TestCase):
    """测试全局回滚管理器"""
    
    def test_get_rollback_manager_singleton(self):
        """测试全局管理器单例"""
        manager1 = get_rollback_manager()
        manager2 = get_rollback_manager()
        
        self.assertIs(manager1, manager2)


if __name__ == '__main__':
    unittest.main()
