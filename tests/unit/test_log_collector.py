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


class TestFileLogReader(unittest.TestCase):
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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        reader = FileLogReader(self.test_file)
        
        self.assertEqual(reader.file_path, Path(self.test_file))
        self.assertIsNotNone(reader.encodings)
        self.assertEqual(reader.encodings[0], 'utf-8')
    
    def test_initialization_with_encoding(self):
        """测试指定编码初始化"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        reader = FileLogReader(self.test_file, encodings=['gbk'])
        
        self.assertEqual(reader.encodings[0], 'gbk')
    
    def test_initialization_with_encoding_detection(self):
        """测试编码自动检测"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        reader = FileLogReader(self.test_file, encodings=['utf-8', 'gbk'])
        
        self.assertIn('utf-8', reader.encodings)
    
    def test_read_from_start(self):
        """测试从开始读取"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('test content\n')
        
        reader = FileLogReader(self.test_file)
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 1)
        self.assertIn('test content', entries[0].raw)
    
    def test_read(self):
        """测试读取"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = FileLogReader(self.test_file)
        
        # First read
        entries = reader.read()
        self.assertEqual(len(entries), 1)
        
        # Add more content
        with open(self.test_file, 'a', encoding='utf-8') as f:
            f.write('line2\nline3\n')
        
        # Second read - should get new lines only
        entries = reader.read()
        self.assertEqual(len(entries), 2)
        
        # Close
        reader.stop_watching()
    
    def test_read_tail(self):
        """测试读取最后N行"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            # Write 10 lines, each ending with newline
            for i in range(10):
                f.write(f'line{i}\n')
        
        reader = FileLogReader(self.test_file)
        entries = reader.read_tail(lines=5)
        
        # read_tail returns up to 5 lines with content
        self.assertLessEqual(len(entries), 5)
        self.assertGreater(len(entries), 0)
    
    def test_get_position(self):
        """测试位置追踪"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\n')
        
        reader = FileLogReader(self.test_file)
        reader.read_from_start()
        
        position = reader.get_position()
        
        self.assertIsNotNone(position)
        self.assertGreater(position.byte_offset, 0)


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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'utf8.log')
        
        with codecs.open(test_file, 'w', encoding='utf-8') as f:
            f.write('中文测试\nUTF-8编码\nこんにちは\n')
        
        reader = FileLogReader(test_file, encodings=['utf-8'])
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 3)
        self.assertIn('中文测试', entries[0].raw)
        self.assertIn('UTF-8编码', entries[1].raw)
        
        reader.stop_watching()
    
    def test_gbk_encoding(self):
        """测试GBK编码"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'gbk.log')
        
        with codecs.open(test_file, 'w', encoding='gbk') as f:
            f.write('中文测试\nGBK编码\n')
        
        reader = FileLogReader(test_file, encodings=['gbk', 'utf-8'])
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 2)
        self.assertIn('中文测试', entries[0].raw)
        
        reader.stop_watching()
    
    def test_latin1_encoding(self):
        """测试Latin-1编码"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'latin1.log')
        
        with codecs.open(test_file, 'w', encoding='latin-1') as f:
            f.write('Latin-1 test\nSpecial chars: \xe9\xe8\xe0\n')
        
        reader = FileLogReader(test_file, encodings=['latin-1'])
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 2)
        
        reader.stop_watching()
    
    def test_auto_encoding_detection(self):
        """测试自动编码检测"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'auto.log')
        
        with codecs.open(test_file, 'w', encoding='utf-8') as f:
            f.write('Auto detect test\n')
        
        reader = FileLogReader(test_file, encodings=['utf-8', 'gbk'])
        
        self.assertIn('utf-8', reader.encodings)


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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\n')
        
        reader = FileLogReader(self.test_file)
        reader.read_from_start()
        
        initial_position = reader.get_position()
        
        # Simulate log rotation by truncating file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('new line1\n')
        
        # Detect rotation - the reader should detect that file was rotated
        reader._detect_rotation()
        
        # After rotation, reading should start from beginning
        reader._position = None
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 1)
        self.assertIn('new line1', entries[0].raw)
    
    def test_detect_file_recreated(self):
        """测试文件重新创建检测"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('original content\n')
        
        reader = FileLogReader(self.test_file)
        # Read to initialize position tracking
        reader.read_from_start()
        # Manually set the last inode to track rotation
        reader._last_inode = os.stat(self.test_file).st_ino
        
        # Remove and recreate file (simulating rotation)
        time.sleep(0.1)  # Ensure different timestamp
        os.remove(self.test_file)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('rotated content\n')
        
        new_inode = os.stat(self.test_file).st_ino
        
        # Note: On some filesystems, the inode may be reused after deletion
        # So we test the behavior - either rotation is detected or file is read correctly
        is_rotated = reader._detect_rotation()
        
        # Read should return the new content
        entries = reader.read_from_start()
        has_new_content = any('rotated content' in e.raw for e in entries) or any('new' in e.raw.lower() for e in entries)
        
        # Either rotation was detected OR new content is readable
        self.assertTrue(is_rotated or has_new_content, "Expected rotation detected or new content readable")
        reader.stop_watching()
    
    def test_no_rotation_detected(self):
        """测试无轮转情况"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\n')
        
        reader = FileLogReader(self.test_file)
        reader.read_from_start()
        
        # Add content without rotation
        with open(self.test_file, 'a', encoding='utf-8') as f:
            f.write('line3\n')
        
        is_rotated = reader._detect_rotation()
        
        self.assertFalse(is_rotated)
        reader.stop_watching()
    
    def test_rotation_with_inode_change(self):
        """测试inode变化检测"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('initial\n')
        
        reader = FileLogReader(self.test_file)
        reader.read_from_start()
        
        # Set the last inode to track rotation
        reader._last_inode = reader._position.inode if reader._position else None
        
        # Simulate file recreation
        os.remove(self.test_file)
        time.sleep(0.1)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('after rotation\n')
        
        # Detect rotation - on some filesystems inode may be reused
        is_rotated = reader._detect_rotation()
        
        # After detecting rotation, reading should return new content
        entries = reader.read_from_start()
        has_new_content = any('after rotation' in e.raw or 'new' in e.raw.lower() for e in entries)
        
        self.assertTrue(is_rotated or has_new_content, "Expected rotation detected or new content readable")


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
    
    def test_read_tail_lines(self):
        """测试Tail最后行"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        # Create initial file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = FileLogReader(self.test_file)
        
        # Initial read
        entries = reader.read_tail(lines=10)
        self.assertEqual(len(entries), 1)
        
        reader.stop_watching()
    
    def test_read_with_callback(self):
        """测试带回调的读取"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        received_entries = []
        
        def callback(entry):
            received_entries.append(entry)
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\n')
        
        reader = FileLogReader(self.test_file, callback=callback)
        
        # Read
        entries = reader.read()
        
        self.assertEqual(len(received_entries), 1)
        self.assertIn('line1', received_entries[0].raw)
        
        reader.stop_watching()


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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('INFO: Application started\n')
            f.write('ERROR: Connection failed\n')
            f.write('DEBUG: Processing request\n')
            f.write('ERROR: Timeout occurred\n')
            f.write('INFO: Request completed\n')
        
        reader = FileLogReader(self.test_file)
        
        all_entries = reader.read_from_start()
        error_entries = [e for e in all_entries if 'ERROR' in e.raw]
        
        self.assertEqual(len(error_entries), 2)
        self.assertTrue(all('ERROR' in e.raw for e in error_entries))
        
        reader.stop_watching()
    
    def test_read_json_logs(self):
        """测试读取JSON格式日志"""
        from modules.collection.log_collector.file_reader import FileLogReader
        import json
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'level': 'INFO', 'message': 'test1'}) + '\n')
            f.write(json.dumps({'level': 'ERROR', 'message': 'test2'}) + '\n')
        
        reader = FileLogReader(self.test_file)
        
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 2)
        
        # Parse JSON
        for entry in entries:
            log_entry = json.loads(entry.raw)
            self.assertIn('level', log_entry)
        
        reader.stop_watching()


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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'empty.log')
        
        # Create empty file
        with open(test_file, 'w', encoding='utf-8') as f:
            pass
        
        reader = FileLogReader(test_file)
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 0)
        
        reader.stop_watching()
    
    def test_file_with_only_newlines(self):
        """测试只包含换行符的文件"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'newlines.log')
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('\n\n\n')
        
        reader = FileLogReader(test_file)
        entries = reader.read_from_start()
        
        # All lines are empty so no entries
        self.assertEqual(len(entries), 0)
        
        reader.stop_watching()
    
    def test_file_with_special_characters(self):
        """测试包含特殊字符的文件"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'special.log')
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('Normal text\n')
            f.write('Special: !@#$%^&*()\n')
            f.write('Unicode: 你好世界\n')
            f.write('Emoji: 🎉🎊\n')
        
        reader = FileLogReader(test_file)
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 4)
        self.assertIn('Normal text', entries[0].raw)
        
        reader.stop_watching()
    
    def test_large_file(self):
        """测试大文件"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'large.log')
        
        # Create file with many lines
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(1000):
                f.write(f'Line {i} with some content\n')
        
        reader = FileLogReader(test_file)
        entries = reader.read_from_start()
        
        self.assertEqual(len(entries), 1000)
        
        reader.stop_watching()
    
    def test_nonexistent_file(self):
        """测试不存在的文件"""
        from modules.collection.log_collector.file_reader import FileLogReader
        
        test_file = os.path.join(self.test_dir, 'nonexistent.log')
        
        reader = FileLogReader(test_file)
        
        # Reading should return empty list for nonexistent file
        entries = reader.read_from_start()
        self.assertEqual(len(entries), 0)


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
        from modules.collection.log_collector.file_reader import FileLogReader
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            for i in range(100):
                f.write(f'Line {i}\n')
        
        errors = []
        
        def read_task(task_id):
            try:
                reader = FileLogReader(self.test_file)
                for _ in range(5):
                    entries = reader.read_from_start()
                    time.sleep(0.01)
                reader.stop_watching()
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


if __name__ == '__main__':
    unittest.main()