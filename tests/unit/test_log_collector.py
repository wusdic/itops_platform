"""
日志采集器综合测试
测试 file_reader.py 的实时采集、多编码支持、日志轮转检测功能
"""

import unittest
import os
import sys
import time
import tempfile
import shutil
import threading
import codecs
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class TestLogFileReader(unittest.TestCase):
    """日志文件读取器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test.log')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """测试初始化"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        reader = LogFileReader(self.test_file)
        
        self.assertEqual(reader.file_path, self.test_file)
        self.assertEqual(reader.encoding, 'utf-8')
        self.assertIsNone(reader._file)
        self.assertEqual(reader._position, 0)
    
    def test_initialization_with_encoding(self):
        """测试指定编码初始化"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        reader = LogFileReader(self.test_file, encoding='gbk')
        
        self.assertEqual(reader.encoding, 'gbk')
    
    def test_initialization_with_encoding_detection(self):
        """测试编码自动检测"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        reader = LogFileReader(self.test_file, encoding='auto')
        
        self.assertEqual(reader.encoding, 'utf-8')
    
    def test_open_and_close(self):
        """测试打开和关闭文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('test content\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        self.assertIsNotNone(reader._file)
        self.assertTrue(reader._file.readable())
        
        reader.close()
        
        self.assertIsNone(reader._file)
    
    def test_context_manager(self):
        """测试上下文管理器"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('test content\n')
        
        with LogFileReader(self.test_file) as reader:
            lines = reader.read_lines()
            self.assertEqual(len(lines), 1)
        
        self.assertIsNone(reader._file)
    
    def test_read_new_lines(self):
        """测试读取新行"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        # First read
        new_lines = reader.read_new_lines()
        self.assertEqual(len(new_lines), 1)
        self.assertEqual(new_lines[0].strip(), 'line1')
        
        # Add more content
        with open(self.test_file, 'a', encoding='utf-8') as f:
            f.write('line2\nline3\n')
        
        # Second read - should get new lines only
        new_lines = reader.read_new_lines()
        self.assertEqual(len(new_lines), 2)
        self.assertEqual(new_lines[0].strip(), 'line2')
        self.assertEqual(new_lines[1].strip(), 'line3')
        
        reader.close()
    
    def test_read_all_lines(self):
        """测试读取所有行"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        all_lines = reader.read_lines()
        
        self.assertEqual(len(all_lines), 3)
        self.assertEqual(all_lines[0].strip(), 'line1')
        self.assertEqual(all_lines[1].strip(), 'line2')
        self.assertEqual(all_lines[2].strip(), 'line3')
        
        reader.close()
    
    def test_tell_position(self):
        """测试位置追踪"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        reader.read_lines()
        position = reader.tell()
        
        self.assertGreater(position, 0)
        
        reader.close()


class TestEncodingSupport(unittest.TestCase):
    """编码支持测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_utf8_encoding(self):
        """测试UTF-8编码"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'utf8.log')
        
        with codecs.open(test_file, 'w', encoding='utf-8') as f:
            f.write('中文测试\nUTF-8编码\nこんにちは\n')
        
        reader = LogFileReader(test_file, encoding='utf-8')
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 3)
        self.assertIn('中文测试', lines[0])
        self.assertIn('UTF-8编码', lines[1])
        
        reader.close()
    
    def test_gbk_encoding(self):
        """测试GBK编码"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'gbk.log')
        
        with codecs.open(test_file, 'w', encoding='gbk') as f:
            f.write('中文测试\nGBK编码\n')
        
        reader = LogFileReader(test_file, encoding='gbk')
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 2)
        self.assertIn('中文测试', lines[0])
        
        reader.close()
    
    def test_latin1_encoding(self):
        """测试Latin-1编码"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'latin1.log')
        
        with codecs.open(test_file, 'w', encoding='latin-1') as f:
            f.write('Latin-1 test\nSpecial chars: \xe9\xe8\xe0\n')
        
        reader = LogFileReader(test_file, encoding='latin-1')
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 2)
        
        reader.close()
    
    def test_auto_encoding_detection(self):
        """测试自动编码检测"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'auto.log')
        
        with codecs.open(test_file, 'w', encoding='utf-8') as f:
            f.write('Auto detect test\n')
        
        reader = LogFileReader(test_file, encoding='auto')
        
        self.assertEqual(reader.encoding, 'utf-8')


class TestLogRotation(unittest.TestCase):
    """日志轮转检测测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'app.log')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_detect_file_truncated(self):
        """测试文件截断检测"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        reader.read_lines()
        
        initial_position = reader.tell()
        
        # Simulate log rotation by truncating file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('new line1\n')
        
        reader._file.seek(0, 2)  # Go to end
        current_size = reader._file.tell()
        
        is_rotated = reader.detect_rotation()
        
        self.assertTrue(is_rotated)
        
        reader.close()
    
    def test_detect_file_recreated(self):
        """测试文件重新创建检测"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('original content\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        reader.read_lines()
        
        initial_inode = os.stat(self.test_file).st_ino
        
        # Remove and recreate file (simulating rotation)
        time.sleep(0.1)  # Ensure different timestamp
        os.remove(self.test_file)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('rotated content\n')
        
        new_inode = os.stat(self.test_file).st_ino
        
        # Detect rotation
        is_rotated = reader.detect_rotation()
        
        self.assertTrue(is_rotated)
    
    def test_no_rotation_detected(self):
        """测试无轮转情况"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        reader.read_lines()
        
        # Add content without rotation
        with open(self.test_file, 'a', encoding='utf-8') as f:
            f.write('line3\n')
        
        is_rotated = reader.detect_rotation()
        
        self.assertFalse(is_rotated)
        
        reader.close()
    
    def test_rotation_with_inode_change(self):
        """测试inode变化检测"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('initial\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        reader.read_lines()
        
        initial_stat = reader._file.fileno()
        
        # Simulate file recreation
        os.remove(self.test_file)
        time.sleep(0.1)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('after rotation\n')
        
        is_rotated = reader.check_inode_change()
        
        self.assertTrue(is_rotated)


class TestRealTimeTail(unittest.TestCase):
    """实时Tail功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'tail_test.log')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_tail_new_lines(self):
        """测试Tail新行"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        # Initial read
        lines = reader.tail_new_lines(timeout=1)
        self.assertEqual(len(lines), 1)
        
        reader.close()
    
    def test_tail_with_callback(self):
        """测试带回调的Tail"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        received_lines = []
        
        def callback(line):
            received_lines.append(line)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        # Add some lines
        with open(self.test_file, 'a', encoding='utf-8') as f:
            f.write('line2\n')
        
        time.sleep(0.5)
        
        new_lines = reader.read_new_lines()
        for line in new_lines:
            callback(line)
        
        self.assertEqual(len(received_lines), 1)
        self.assertIn('line2', received_lines[0])
        
        reader.close()
    
    def test_tail_with_timeout(self):
        """测试带超时的Tail"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('initial\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        # This should timeout and return empty
        start = time.time()
        lines = reader.tail_new_lines(timeout=2)
        elapsed = time.time() - start
        
        self.assertGreaterEqual(elapsed, 1.9)
        self.assertEqual(len(lines), 0)
        
        reader.close()


class TestLogPatterns(unittest.TestCase):
    """日志模式匹配测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'patterns.log')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_read_lines_matching_pattern(self):
        """测试读取匹配模式的行"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('INFO: Application started\n')
            f.write('ERROR: Connection failed\n')
            f.write('DEBUG: Processing request\n')
            f.write('ERROR: Timeout occurred\n')
            f.write('INFO: Request completed\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        all_lines = reader.read_lines()
        error_lines = [l for l in all_lines if 'ERROR' in l]
        
        self.assertEqual(len(error_lines), 2)
        self.assertTrue(all('ERROR' in line for line in error_lines))
        
        reader.close()
    
    def test_read_json_logs(self):
        """测试读取JSON格式日志"""
        from modules.collection.log_collector.file_reader import LogFileReader
        import json
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'level': 'INFO', 'message': 'test1'}) + '\n')
            f.write(json.dumps({'level': 'ERROR', 'message': 'test2'}) + '\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 2)
        
        # Parse JSON
        for line in lines:
            log_entry = json.loads(line)
            self.assertIn('level', log_entry)
        
        reader.close()


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_empty_file(self):
        """测试空文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'empty.log')
        
        # Create empty file
        with open(test_file, 'w', encoding='utf-8') as f:
            pass
        
        reader = LogFileReader(test_file)
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 0)
        
        reader.close()
    
    def test_file_with_only_newlines(self):
        """测试只包含换行符的文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'newlines.log')
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('\n\n\n')
        
        reader = LogFileReader(test_file)
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 3)
        
        reader.close()
    
    def test_file_with_special_characters(self):
        """测试包含特殊字符的文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'special.log')
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('Normal text\n')
            f.write('Special: !@#$%^&*()\n')
            f.write('Unicode: 你好世界\n')
            f.write('Emoji: 🎉🎊\n')
            f.write('Null byte test\x00\n')
        
        reader = LogFileReader(test_file)
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 5)
        self.assertIn('Normal text', lines[0])
        self.assertIn('你', lines[2])
        
        reader.close()
    
    def test_binary_file_handling(self):
        """测试二进制文件处理"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'binary.log')
        
        with open(test_file, 'wb') as f:
            f.write(b'Normal text\n')
            f.write(b'Binary: \x00\x01\x02\x03\n')
        
        reader = LogFileReader(test_file, encoding='utf-8')
        reader.open()
        
        # Should handle gracefully
        try:
            lines = reader.read_lines()
            # May have encoding errors but shouldn't crash
        except UnicodeDecodeError:
            pass  # Expected for binary content
        
        reader.close()
    
    def test_large_file(self):
        """测试大文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'large.log')
        
        # Create file with many lines
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(10000):
                f.write(f'Line {i} with some content\n')
        
        reader = LogFileReader(test_file)
        reader.open()
        
        lines = reader.read_lines()
        
        self.assertEqual(len(lines), 10000)
        
        reader.close()
    
    def test_nonexistent_file(self):
        """测试不存在的文件"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        test_file = os.path.join(self.test_dir, 'nonexistent.log')
        
        reader = LogFileReader(test_file)
        
        # Opening should fail
        with self.assertRaises(FileNotFoundError):
            reader.open()


class TestConcurrentAccess(unittest.TestCase):
    """并发访问测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'concurrent.log')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_concurrent_reads(self):
        """测试并发读取"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            for i in range(100):
                f.write(f'Line {i}\n')
        
        errors = []
        
        def read_task(task_id):
            try:
                reader = LogFileReader(self.test_file)
                reader.open()
                
                for _ in range(5):
                    lines = reader.read_lines()
                    time.sleep(0.01)
                
                reader.close()
            except Exception as e:
                errors.append((task_id, str(e)))
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=read_task, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
    
    def test_concurrent_read_and_append(self):
        """测试并发读取和追加"""
        from modules.collection.log_collector.file_reader import LogFileReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('Initial line\n')
        
        reader = LogFileReader(self.test_file)
        reader.open()
        
        # Read initial
        initial_lines = reader.read_lines()
        self.assertEqual(len(initial_lines), 1)
        
        # Append in separate thread
        def append_task():
            for i in range(10):
                with open(self.test_file, 'a', encoding='utf-8') as f:
                    f.write(f'Appended line {i}\n')
                time.sleep(0.05)
        
        append_thread = threading.Thread(target=append_task)
        append_thread.start()
        
        # Continue reading
        for _ in range(10):
            time.sleep(0.06)
            new_lines = reader.read_new_lines()
            # Just verify it doesn't crash
        
        append_thread.join()
        reader.close()


if __name__ == '__main__':
    unittest.main()
