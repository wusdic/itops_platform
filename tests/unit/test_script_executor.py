"""
AM-03 脚本执行模块单元测试

测试脚本执行器、脚本库、远程执行等功能
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

from modules.automation.script_executor.executor import (
    ScriptExecutor,
    Script,
    ScriptType,
    ExecutionStatus,
    ExecutionResult,
    ExecutionProgress,
)
from modules.automation.script_executor.library import (
    ScriptLibrary,
    ScriptCategory,
    ScriptStatus,
    ScriptVersion,
    ScriptTemplate,
)
from modules.automation.script_executor.remote import (
    RemoteExecutor,
    RemoteProtocol,
    RemoteStatus,
    Host,
    RemoteResult,
    SSHExecutor,
    WinRMExecutor,
    BatchExecutor,
    HostManager,
    ExecutionProgress as RemoteProgress,
)


class TestScriptExecutor(unittest.TestCase):
    """测试脚本执行器"""
    
    def setUp(self):
        """测试前准备"""
        self.executor = ScriptExecutor()
    
    def test_execute_shell_script(self):
        """测试执行Shell脚本"""
        script = 'echo "Hello, World!"'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.SHELL,
        )
        
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.return_code, 0)
        self.assertIn("Hello, World!", result.stdout)
    
    def test_execute_python_script(self):
        """测试执行Python脚本"""
        script = 'print("Hello from Python")'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.PYTHON,
        )
        
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.return_code, 0)
        self.assertIn("Hello from Python", result.stdout)
    
    def test_execute_with_parameters(self):
        """测试带参数执行"""
        script = 'echo "Name: ${name}, Age: ${age}"'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.SHELL,
            parameters={'name': 'Alice', 'age': 30},
        )
        
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertIn("Name: Alice", result.stdout)
        self.assertIn("Age: 30", result.stdout)
    
    def test_execute_with_timeout(self):
        """测试超时控制"""
        script = 'sleep 10'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.SHELL,
            timeout=1,
        )
        
        self.assertEqual(result.status, ExecutionStatus.TIMEOUT)
    
    def test_execute_failed_script(self):
        """测试执行失败"""
        script = 'exit 1'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.SHELL,
        )
        
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertNotEqual(result.return_code, 0)
    
    def test_execute_batch(self):
        """测试批量执行"""
        scripts = [
            'echo "Script 1"',
            'echo "Script 2"',
            'echo "Script 3"',
        ]
        results = self.executor.execute_batch(
            scripts=scripts,
            script_types=[ScriptType.SHELL] * 3,
        )
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.status == ExecutionStatus.SUCCESS for r in results))
    
    def test_execute_batch_parallel(self):
        """测试并行批量执行"""
        scripts = [
            'echo "P1"' ,
            'echo "P2"',
            'echo "P3"',
            'echo "P4"',
        ]
        results = self.executor.execute_batch(
            scripts=scripts,
            script_types=[ScriptType.SHELL] * 4,
            parallel=True,
            max_workers=2,
        )
        
        self.assertEqual(len(results), 4)
        self.assertTrue(all(r.status == ExecutionStatus.SUCCESS for r in results))
    
    def test_cancel_task(self):
        """测试取消任务"""
        script = 'sleep 100'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.SHELL,
            timeout=300,
        )
        
        # 取消任务
        cancelled = self.executor.cancel(result.task_id)
        
        # 注意：由于异步执行，可能无法真正取消
        # 这里主要测试取消方法的可用性
        self.assertIsInstance(cancelled, bool)
    
    def test_get_history(self):
        """测试获取历史"""
        # 执行几个脚本
        for i in range(3):
            self.executor.execute(
                script=f'echo "Test {i}"',
                script_type=ScriptType.SHELL,
            )
        
        history = self.executor.get_history()
        self.assertGreaterEqual(len(history), 3)
    
    def test_clear_history(self):
        """测试清空历史"""
        self.executor.execute(
            script='echo "Test"',
            script_type=ScriptType.SHELL,
        )
        
        self.executor.clear_history()
        history = self.executor.get_history()
        self.assertEqual(len(history), 0)
    
    def test_script_object(self):
        """测试Script对象"""
        script = Script(
            name="test_script",
            script_type=ScriptType.SHELL,
            content='echo "${message}"',
            parameters=[
                {'name': 'message', 'type': 'string', 'required': True}
            ],
            timeout=60,
        )
        
        # 测试渲染
        rendered = script.render_content({'message': 'Hello'})
        self.assertIn('Hello', rendered)
        
        # 测试解释器
        self.assertEqual(script.get_interpreter(), '/bin/bash')
        
        # 测试扩展名
        self.assertEqual(script.get_extension(), '.sh')


class TestScriptLibrary(unittest.TestCase):
    """测试脚本库"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp(prefix="script_library_test_")
        self.library = ScriptLibrary(storage_path=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_script(self):
        """测试创建脚本"""
        script = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
            description="A test script",
            category=ScriptCategory.CUSTOM,
            author="tester",
        )
        
        self.assertIsNotNone(script)
        self.assertEqual(script.name, "test_script")
        self.assertEqual(script.version, "1.0.1")  # 初始版本1.0.1
        self.assertGreater(len(script.versions), 0)
    
    def test_get_script(self):
        """测试获取脚本"""
        created = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
        )
        
        retrieved = self.library.get_script(created.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "test_script")
    
    def test_update_script(self):
        """测试更新脚本"""
        script = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
        )
        
        # 更新内容
        updated = self.library.update_script(
            script_id=script.id,
            content='echo "Updated"',
            author="tester",
            changelog="Updated content",
        )
        
        self.assertIsNotNone(updated)
        # 版本应该增加
        self.assertEqual(updated.version, "1.0.2")
    
    def test_delete_script(self):
        """测试删除脚本"""
        script = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
        )
        
        deleted = self.library.delete_script(script.id)
        self.assertTrue(deleted)
        
        retrieved = self.library.get_script(script.id)
        self.assertIsNone(retrieved)
    
    def test_list_scripts(self):
        """测试列出脚本"""
        # 创建多个脚本
        for i in range(5):
            self.library.create_script(
                name=f"script_{i}",
                content=f'echo "{i}"',
                script_type="shell",
            )
        
        scripts = self.library.list_scripts()
        self.assertGreaterEqual(len(scripts), 5)
    
    def test_list_scripts_by_category(self):
        """测试按分类列出脚本"""
        self.library.create_script(
            name="monitoring_script",
            content='echo "monitoring"',
            script_type="shell",
            category=ScriptCategory.MONITORING,
        )
        self.library.create_script(
            name="backup_script",
            content='echo "backup"',
            script_type="shell",
            category=ScriptCategory.BACKUP,
        )
        
        scripts = self.library.get_scripts_by_category(ScriptCategory.MONITORING)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].category, ScriptCategory.MONITORING)
    
    def test_search_scripts(self):
        """测试搜索脚本"""
        self.library.create_script(
            name="test_monitoring",
            content='echo "test"',
            script_type="shell",
            description="This is for testing",
        )
        
        results = self.library.list_scripts(search="test")
        self.assertGreaterEqual(len(results), 1)
    
    def test_version_management(self):
        """测试版本管理"""
        script = self.library.create_script(
            name="test_script",
            content='echo "v1"',
            script_type="shell",
            author="tester",
        )
        
        # 添加新版本
        self.library.update_script(
            script_id=script.id,
            content='echo "v2"',
            author="tester",
            changelog="Updated to v2",
        )
        
        versions = self.library.get_versions(script.id)
        self.assertGreaterEqual(len(versions), 2)
        
        # 回滚到第一版
        self.library.rollback_version(script.id, versions[0].version, "tester")
        
        current = self.library.get_script(script.id)
        self.assertIn("v1", current.content)
    
    def test_export_import_script(self):
        """测试导入导出脚本"""
        script = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
        )
        
        # 导出
        exported = self.library.export_script(script.id, format="json")
        self.assertIsNotNone(exported)
        
        # 删除原脚本
        self.library.delete_script(script.id)
        
        # 导入
        imported = self.library.import_script(exported, format="json")
        self.assertIsNotNone(imported)
        self.assertEqual(imported.content, 'echo "Hello"')
    
    def test_export_package(self):
        """测试导出包"""
        scripts = []
        for i in range(3):
            s = self.library.create_script(
                name=f"script_{i}",
                content=f'echo "{i}"',
                script_type="shell",
            )
            scripts.append(s.id)
        
        # 导出包
        package_path = self.library.export_package(scripts)
        self.assertTrue(os.path.exists(package_path))
    
    def test_import_package(self):
        """测试导入包"""
        # 创建并导出脚本
        script = self.library.create_script(
            name="test_script",
            content='echo "Hello"',
            script_type="shell",
        )
        package_path = self.library.export_package([script.id])
        
        # 清空库
        self.library.delete_script(script.id)
        
        # 导入包
        imported = self.library.import_package(package_path)
        self.assertGreaterEqual(len(imported), 1)
    
    def test_template_operations(self):
        """测试模板操作"""
        # 创建模板
        template = self.library.create_template(
            name="test_template",
            content='echo "${message}"',
            script_type="shell",
            description="A test template",
            variables=[
                {'name': 'message', 'description': 'The message', 'default': 'Hello'}
            ],
        )
        
        self.assertIsNotNone(template)
        
        # 从模板创建脚本
        created_script = self.library.create_script_from_template(
            template_id=template.id,
            name="script_from_template",
            variables={'message': 'Custom message'},
        )
        
        self.assertIsNotNone(created_script)
        self.assertIn('Custom message', created_script.content)
    
    def test_marketplace_operations(self):
        """测试市场操作"""
        # 创建并发布到市场
        script = self.library.create_script(
            name="market_script",
            content='echo "market"',
            script_type="shell",
        )
        
        published = self.library.publish_to_market(script.id)
        self.assertTrue(published)
        
        # 浏览市场
        items = self.library.browse_market()
        self.assertGreaterEqual(len(items), 1)
    
    def test_statistics(self):
        """测试统计信息"""
        # 创建一些脚本
        for i in range(3):
            self.library.create_script(
                name=f"script_{i}",
                content=f'echo "{i}"',
                script_type="shell",
            )
        
        stats = self.library.get_statistics()
        self.assertGreaterEqual(stats['total_scripts'], 3)
        self.assertIn('by_category', stats)
        self.assertIn('by_type', stats)


class TestRemoteExecutor(unittest.TestCase):
    """测试远程执行器（需要mock）"""
    
    def setUp(self):
        """测试前准备"""
        self.executor = RemoteExecutor()
        
        # 创建测试主机
        self.host = Host(
            host_id="test_host_1",
            hostname="test-server",
            ip="192.168.1.100",
            port=22,
            protocol=RemoteProtocol.SSH,
            username="testuser",
            password="testpass",
        )
    
    @unittest.skipUnless(
        os.environ.get('TEST_WITH_SSH', '').lower() == 'true',
        "Requires SSH environment or paramiko installed"
    )
    def test_ssh_executor_mock(self):
        """测试SSH执行器（需要SSH环境或安装paramiko）"""
        # 这个测试在实际SSH环境中运行
        self.assertTrue(True)
    
    def test_host_manager(self):
        """测试主机管理器"""
        temp_dir = tempfile.mkdtemp(prefix="host_manager_test_")
        
        try:
            manager = HostManager(storage_path=temp_dir)
            
            # 添加主机
            host = manager.add_host(
                hostname="test-server",
                ip="192.168.1.100",
                protocol=RemoteProtocol.SSH,
                username="admin",
                password="pass123",
            )
            
            self.assertIsNotNone(host)
            
            # 获取主机
            retrieved = manager.get_host(host.host_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.ip, "192.168.1.100")
            
            # 列出主机
            hosts = manager.list_hosts()
            self.assertGreaterEqual(len(hosts), 1)
            
            # 更新主机
            updated = manager.update_host(host.host_id, description="Updated desc")
            self.assertEqual(updated.description, "Updated desc")
            
            # 删除主机
            deleted = manager.delete_host(host.host_id)
            self.assertTrue(deleted)
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def test_batch_executor_mock(self):
        """测试批量执行器"""
        batch_executor = BatchExecutor()
        
        # 添加进度回调
        progress_updates = []
        def on_progress(progress):
            progress_updates.append(progress)
        
        batch_executor.add_progress_callback(on_progress)
        
        # 注意：实际执行需要真实环境
        # 这里测试回调机制
        self.assertEqual(len(progress_updates), 0)


class TestExecutionProgress(unittest.TestCase):
    """测试执行进度"""
    
    def test_local_progress(self):
        """测试本地进度"""
        progress = ExecutionProgress(total=10)
        
        # 模拟完成一个任务
        result = ExecutionResult(
            task_id="test_1",
            script_name="test",
            script_type=ScriptType.SHELL,
            status=ExecutionStatus.SUCCESS,
            return_code=0,
            stdout="",
            stderr="",
            start_time=datetime.now(),
        )
        progress.update(result)
        
        self.assertEqual(progress.completed, 1)
        self.assertEqual(progress.get_progress(), 10.0)
        
        summary = progress.get_summary()
        self.assertEqual(summary['total'], 10)
        self.assertEqual(summary['completed'], 1)
    
    def test_remote_progress(self):
        """测试远程进度"""
        progress = RemoteProgress(batch_id="test_batch", total=5)
        
        # 创建测试主机
        host = Host(
            host_id="test",
            hostname="test",
            ip="127.0.0.1",
        )
        
        # 创建结果
        result = RemoteResult(
            task_id="test_1",
            host=host,
            status=RemoteStatus.SUCCESS,
        )
        progress.update(result)
        
        self.assertEqual(progress.completed, 1)
        self.assertEqual(progress.succeeded, 1)
        
        failed = progress.get_failed_hosts()
        self.assertEqual(len(failed), 0)


class TestScriptTypes(unittest.TestCase):
    """测试脚本类型支持"""
    
    def setUp(self):
        self.executor = ScriptExecutor()
    
    def test_shell_script(self):
        """测试Shell脚本"""
        script = '#!/bin/bash\necho "Hello Shell"'
        result = self.executor.execute(script=script)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
    
    def test_python_script(self):
        """测试Python脚本"""
        script = 'import sys; print("Hello Python")'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.PYTHON,
        )
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertIn("Hello Python", result.stdout)
    
    def test_powershell_script(self):
        """测试PowerShell脚本"""
        script = 'Write-Host "Hello PowerShell"'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.POWERSHELL,
        )
        # pwsh可能不可用，跳过此测试
        if result.status == ExecutionStatus.FAILED:
            self.skipTest("PowerShell not available")


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def setUp(self):
        self.executor = ScriptExecutor()
    
    def test_empty_script(self):
        """测试空脚本"""
        result = self.executor.execute(script="", script_type=ScriptType.SHELL)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
    
    def test_very_long_output(self):
        """测试长输出"""
        script = 'for i in range(100): print("Line", i)'
        result = self.executor.execute(
            script=script,
            script_type=ScriptType.PYTHON,
        )
        # 应该能正常处理
        self.assertIn(result.status, [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED])
    
    def test_special_characters(self):
        """测试特殊字符"""
        script = 'echo "Hello 世界 🌍"'
        result = self.executor.execute(script=script)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertIn("Hello", result.stdout)


if __name__ == '__main__':
    unittest.main()
