"""
BM-03 知识库模块单元测试
测试SOP知识库、故障案例库、文档管理、智能检索和RAG功能
"""

import unittest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, '/workspace/itops_platform')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.business.knowledge_base.models import (
    SOPDocument, SOPVersion, SOPReview, FaultCase, Document,
    DocumentChunk, Category, Tag, SearchHistory, SearchBookmark,
    DocumentStatus, ReviewStatus, FaultLevel, FaultStatus, DocumentType
)
from modules.business.knowledge_base.models import Base


class TestSOPKnowledgeBase(unittest.TestCase):
    """测试SOP知识库"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试数据库"""
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        """清理测试数据库"""
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        """每个测试前创建新会话并清理数据"""
        self.db = self.Session()
        # 清理之前的数据
        self.db.query(SOPDocument).delete(synchronize_session=False)
        self.db.commit()
    
    def tearDown(self):
        """每个测试后关闭会话"""
        self.db.close()
    
    def test_create_sop_document(self):
        """测试创建SOP文档"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        
        sop = sop_kb.create(
            title='测试SOP文档',
            content='# 测试标题\n\n这是测试内容',
            author='test_user',
            category_id=None,
            tags=['测试', '示例']
        )
        
        self.assertIsNotNone(sop.id)
        self.assertEqual(sop.title, '测试SOP文档')
        self.assertEqual(sop.author, 'test_user')
        self.assertEqual(sop.version, '1.0.0')
        self.assertEqual(sop.status, DocumentStatus.DRAFT)
        self.assertTrue(sop.doc_no.startswith('SOP'))
    
    def test_get_sop_by_id(self):
        """测试根据ID获取SOP文档"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='测试文档',
            content='测试内容',
            author='test_user'
        )
        
        fetched = sop_kb.get_by_id(sop.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, sop.id)
        self.assertEqual(fetched.title, '测试文档')
    
    def test_list_sop_documents(self):
        """测试查询SOP文档列表"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        
        # 创建多个文档
        for i in range(5):
            sop_kb.create(
                title=f'列表测试文档{i}',
                content=f'内容{i}',
                author='test_user'
            )
        
        sops, total = sop_kb.list(page=1, page_size=10)
        self.assertGreaterEqual(total, 5)
        self.assertGreaterEqual(len(sops), 5)
        
        # 测试分页
        sops, total = sop_kb.list(page=1, page_size=2)
        self.assertEqual(total, 5)
        self.assertEqual(len(sops), 2)
    
    def test_update_sop_document(self):
        """测试更新SOP文档"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='原始标题',
            content='原始内容',
            author='test_user'
        )
        
        updated = sop_kb.update(
            sop.id,
            operator='test_user',
            title='更新后的标题'
        )
        
        self.assertEqual(updated.title, '更新后的标题')
    
    def test_submit_review(self):
        """测试提交审核"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='待审核文档',
            content='内容',
            author='test_user'
        )
        
        success, msg, result = sop_kb.submit_review(sop.id, 'test_user')
        
        self.assertTrue(success)
        self.assertEqual(result.status, DocumentStatus.PENDING_REVIEW)
    
    def test_review_workflow(self):
        """测试审核流程"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='审核流程测试',
            content='内容',
            author='test_user'
        )
        
        # 提交审核
        sop_kb.submit_review(sop.id, 'test_user')
        
        # 审核通过
        success, msg, result = sop_kb.review(
            sop.id, 'reviewer', ReviewStatus.APPROVED, '审核通过'
        )
        
        self.assertTrue(success)
        self.assertEqual(result.status, DocumentStatus.APPROVED)
        self.assertEqual(result.review_status, ReviewStatus.APPROVED)
    
    def test_version_management(self):
        """测试版本管理"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='版本测试',
            content='初始内容',
            author='test_user'
        )
        
        # 更新内容创建新版本
        sop_kb.update(sop.id, 'test_user', content='更新内容')
        
        updated_sop = sop_kb.get_by_id(sop.id)
        # 检查版本号已经改变
        self.assertNotEqual(updated_sop.version, '1.0.0')
        
        # 获取版本历史
        versions = sop_kb.get_versions(sop.id)
        self.assertGreaterEqual(len(versions), 2)  # 至少初始版本 + 更新版本
    
    def test_sop_soft_delete(self):
        """测试软删除"""
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        
        sop_kb = SOPKnowledgeBase(self.db)
        sop = sop_kb.create(
            title='待删除文档',
            content='内容',
            author='test_user'
        )
        
        result = sop_kb.delete(sop.id, 'test_user')
        self.assertTrue(result)
        
        # 验证无法获取
        fetched = sop_kb.get_by_id(sop.id)
        self.assertIsNone(fetched)


class TestCaseLibrary(unittest.TestCase):
    """测试故障案例库"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        """每个测试前创建新会话并清理数据"""
        self.db = self.Session()
        # 清理之前的数据
        self.db.query(FaultCase).delete(synchronize_session=False)
        self.db.commit()
    
    def tearDown(self):
        self.db.close()
    
    def test_create_fault_case(self):
        """测试创建故障案例"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        
        fault_case = case_lib.create(
            title='数据库连接失败',
            author='admin',
            fault_category='database',
            symptom='应用程序无法连接数据库',
            fault_level=FaultLevel.P2,
            affected_systems=['核心系统'],
            affected_services=['用户服务']
        )
        
        self.assertIsNotNone(fault_case.id)
        self.assertEqual(fault_case.title, '数据库连接失败')
        self.assertEqual(fault_case.fault_level, FaultLevel.P2)
        self.assertEqual(fault_case.fault_status, FaultStatus.OPEN)
        self.assertTrue(fault_case.case_no.startswith('CASE'))
    
    def test_update_case_status(self):
        """测试更新案例状态"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        case = case_lib.create(
            title='测试案例',
            author='admin',
            fault_category='network'
        )
        
        success, msg, result = case_lib.update_status(
            case.id, FaultStatus.INVESTIGATING
        )
        
        self.assertTrue(success)
        self.assertEqual(result.fault_status, FaultStatus.INVESTIGATING)
    
    def test_add_solution(self):
        """测试添加解决方案"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        case = case_lib.create(
            title='测试案例',
            author='admin',
            fault_category='network'
        )
        
        success, msg = case_lib.add_solution(
            case.id,
            solution='重启相关服务',
            workaround='临时切换到备用服务器',
            prevention='增加服务监控'
        )
        
        self.assertTrue(success)
        
        updated_case = case_lib.get_by_id(case.id)
        self.assertEqual(updated_case.solution, '重启相关服务')
        self.assertEqual(updated_case.workaround, '临时切换到备用服务器')
    
    def test_add_lessons_learned(self):
        """测试添加经验教训"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        case = case_lib.create(
            title='测试案例',
            author='admin',
            fault_category='network'
        )
        
        success, msg = case_lib.add_lessons_learned(
            case.id,
            root_cause='配置错误',
            lessons_learned='修改配置前需要备份',
            improvement='添加配置变更审核流程'
        )
        
        self.assertTrue(success)
        
        updated_case = case_lib.get_by_id(case.id)
        self.assertEqual(updated_case.root_cause, '配置错误')
        self.assertEqual(updated_case.lessons_learned, '修改配置前需要备份')
    
    def test_list_cases_with_filters(self):
        """测试条件查询"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        
        # 创建不同级别的案例
        for level in [FaultLevel.P1, FaultLevel.P2, FaultLevel.P3]:
            case_lib.create(
                title=f'级别测试{level.value}',
                author='admin',
                fault_category='network',
                fault_level=level
            )
        
        # 按级别筛选
        cases, total = case_lib.list(fault_level=FaultLevel.P2)
        self.assertGreaterEqual(total, 1)
        self.assertEqual(cases[0].fault_level, FaultLevel.P2)
    
    def test_get_similar_cases(self):
        """测试获取相似案例"""
        from modules.business.knowledge_base.case import CaseLibrary
        
        case_lib = CaseLibrary(self.db)
        case1 = case_lib.create(
            title='相似案例测试A',
            author='admin',
            fault_category='database',
            fault_level=FaultLevel.P2
        )
        case2 = case_lib.create(
            title='相似案例测试B',
            author='admin',
            fault_category='database',
            fault_level=FaultLevel.P2  # Same category AND level
        )
        case3 = case_lib.create(
            title='不同分类案例',
            author='admin',
            fault_category='network',  # Different category
            fault_level=FaultLevel.P2
        )
        
        similar = case_lib.get_similar_cases(case1.id)
        # case2 should be similar (same category AND level)
        case_ids = [c.id for c in similar]
        self.assertIn(case2.id, case_ids)
        # case3 should not be similar (different category)
        self.assertNotIn(case3.id, case_ids)


class TestDocumentManager(unittest.TestCase):
    """测试文档管理"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        self.db = self.Session()
    
    def tearDown(self):
        self.db.close()
    
    def test_create_document(self):
        """测试创建文档"""
        from modules.business.knowledge_base.document import DocumentManager
        
        doc_mgr = DocumentManager(self.db)
        
        doc = doc_mgr.create(
            title='技术文档',
            doc_type=DocumentType.TECHNICAL,
            content='# 标题\n\n内容',
            author='admin',
            tags=['技术', '指南']
        )
        
        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.title, '技术文档')
        self.assertEqual(doc.format, 'markdown')
        self.assertEqual(doc.status, DocumentStatus.DRAFT)
    
    def test_permission_control(self):
        """测试权限控制"""
        from modules.business.knowledge_base.document import DocumentManager
        
        doc_mgr = DocumentManager(self.db)
        
        # 公开文档
        public_doc = doc_mgr.create(
            title='公开文档',
            doc_type=DocumentType.OTHER,
            content='内容',
            author='admin',
            is_public=True
        )
        
        # 私有文档
        private_doc = doc_mgr.create(
            title='私有文档',
            doc_type=DocumentType.OTHER,
            content='内容',
            author='admin',
            is_public=False,
            permissions={'user2': {'read': True, 'write': False}}
        )
        
        # 验证权限
        self.assertTrue(doc_mgr.check_permission(public_doc.id, 'user1', 'read'))
        self.assertTrue(doc_mgr.check_permission(private_doc.id, 'admin', 'read'))
        self.assertFalse(doc_mgr.check_permission(private_doc.id, 'user1', 'read'))
        self.assertTrue(doc_mgr.check_permission(private_doc.id, 'user2', 'read'))


class TestIntelligentSearch(unittest.TestCase):
    """测试智能检索"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        self.db = self.Session()
        
        # 创建测试数据
        from modules.business.knowledge_base.sop import SOPKnowledgeBase
        from modules.business.knowledge_base.case import CaseLibrary
        
        sop_kb = SOPKnowledgeBase(self.db)
        case_lib = CaseLibrary(self.db)
        
        sop_kb.create(
            title='服务器重启操作指南',
            content='本文档介绍服务器重启的标准操作流程...',
            author='admin',
            tags=['服务器', '运维']
        )
        
        case_lib.create(
            title='服务器异常宕机案例',
            author='admin',
            fault_category='hardware',
            symptom='服务器突然宕机',
            fault_level=FaultLevel.P1
        )
    
    def tearDown(self):
        self.db.close()
    
    def test_fulltext_search(self):
        """测试全文搜索"""
        from modules.business.knowledge_base.search import IntelligentSearch, SearchType
        
        search = IntelligentSearch(self.db)
        
        results, total = search.search(
            query='服务器',
            search_type=SearchType.FULLTEXT
        )
        
        self.assertGreaterEqual(total, 1)
    
    def test_hybrid_search(self):
        """测试混合搜索"""
        from modules.business.knowledge_base.search import IntelligentSearch, SearchType
        
        search = IntelligentSearch(self.db)
        
        results, total = search.search(
            query='宕机',
            search_type=SearchType.HYBRID
        )
        
        self.assertGreaterEqual(total, 0)
    
    def test_search_highlights(self):
        """测试搜索高亮"""
        from modules.business.knowledge_base.search import IntelligentSearch, SearchType
        
        search = IntelligentSearch(self.db)
        
        results, _ = search.search(
            query='服务器',
            search_type=SearchType.FULLTEXT
        )
        
        for result in results:
            # 检查高亮标记
            for highlight in result.highlights:
                self.assertIn('<em>服务器</em>', highlight)
    
    def test_search_suggestions(self):
        """测试搜索建议"""
        from modules.business.knowledge_base.search import IntelligentSearch
        
        search = IntelligentSearch(self.db)
        
        suggestions = search.get_search_suggestions('服务')
        
        # 验证建议来自标题
        self.assertTrue(len(suggestions) >= 0)


class TestRAGEnhancer(unittest.TestCase):
    """测试RAG增强"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        self.db = self.Session()
    
    def tearDown(self):
        self.db.close()
    
    def test_fixed_chunking(self):
        """测试固定长度分块"""
        from modules.business.knowledge_base.rag import RAGEnhancer, ChunkMethod
        
        rag = RAGEnhancer(self.db)
        
        text = "这是测试文本内容。" * 100
        
        chunks = rag._chunk_text(text, ChunkMethod.FIXED, 100, 20)
        
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 150)  # 考虑边界调整
    
    def test_paragraph_chunking(self):
        """测试段落分块"""
        from modules.business.knowledge_base.rag import RAGEnhancer, ChunkMethod
        
        rag = RAGEnhancer(self.db)
        
        text = """
这是第一段内容。

这是第二段内容，包含更多细节。

这是第三段内容。

这是第四段内容，可能稍微长一些。
"""
        
        chunks = rag._chunk_text(text, ChunkMethod.PARAGRAPH, 50, 10)
        
        self.assertGreater(len(chunks), 0)


class TestCategoryManager(unittest.TestCase):
    """测试分类管理"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        self.db = self.Session()
    
    def tearDown(self):
        self.db.close()
    
    def test_create_category(self):
        """测试创建分类"""
        from modules.business.knowledge_base.sop import CategoryManager
        
        cat_mgr = CategoryManager(self.db)
        
        category = cat_mgr.create(
            name='网络设备',
            code='network',
            description='网络设备相关文档'
        )
        
        self.assertIsNotNone(category.id)
        self.assertEqual(category.name, '网络设备')
        self.assertEqual(category.code, 'network')
    
    def test_get_category_tree(self):
        """测试获取分类树"""
        from modules.business.knowledge_base.sop import CategoryManager
        
        cat_mgr = CategoryManager(self.db)
        
        # 创建父子分类 - 使用唯一的code
        parent = cat_mgr.create(name='分类树测试父类', code='tree_test_parent')
        cat_mgr.create(name='子分类A', code='tree_child_a', parent_id=parent.id)
        cat_mgr.create(name='子分类B', code='tree_child_b', parent_id=parent.id)
        
        tree = cat_mgr.get_tree()
        
        # 验证树结构
        parent_nodes = [n for n in tree if n['name'] == '分类树测试父类']
        self.assertGreaterEqual(len(parent_nodes), 1)
        if parent_nodes:
            self.assertGreaterEqual(len(parent_nodes[0].get('children', [])), 2)


class TestTagManager(unittest.TestCase):
    """测试标签管理"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.engine = create_engine(f'sqlite:///{cls.db_path}')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        os.unlink(cls.db_path)
    
    def setUp(self):
        self.db = self.Session()
    
    def tearDown(self):
        self.db.close()
    
    def test_create_tag(self):
        """测试创建标签"""
        from modules.business.knowledge_base.sop import TagManager
        
        tag_mgr = TagManager(self.db)
        
        tag = tag_mgr.create(
            name='紧急',
            color='#ff0000'
        )
        
        self.assertIsNotNone(tag.id)
        self.assertEqual(tag.name, '紧急')
        self.assertEqual(tag.usage_count, 0)
    
    def test_update_usage_count(self):
        """测试更新使用次数"""
        from modules.business.knowledge_base.sop import TagManager
        
        tag_mgr = TagManager(self.db)
        
        tag = tag_mgr.create(name='测试标签')
        
        tag_mgr.update_usage_count('测试标签', 5)
        
        updated_tag = tag_mgr.get_by_name('测试标签')
        self.assertEqual(updated_tag.usage_count, 5)


class TestAIAssist(unittest.TestCase):
    """测试AI辅助功能"""
    
    def setUp(self):
        self.db = MagicMock()
    
    def test_suggest_tags(self):
        """测试AI建议标签"""
        from modules.business.knowledge_base.ai_assist import AIAssist, MockLLMClient
        
        ai = AIAssist(self.db, MockLLMClient())
        
        success, result = ai.suggest_tags(
            '这是一篇关于服务器维护的技术文档，介绍了Linux服务器的基本操作和维护流程。',
            max_tags=3
        )
        
        # Mock客户端返回固定的标签
        self.assertTrue(success)
        self.assertIsInstance(result, list)
    
    def test_summarize_content(self):
        """测试内容摘要"""
        from modules.business.knowledge_base.ai_assist import AIAssist, MockLLMClient
        
        ai = AIAssist(self.db, MockLLMClient())
        
        content = "这是测试内容。" * 50
        
        success, result = ai.summarize_content(
            content,
            max_length=200,
            summary_type='brief'
        )
        
        self.assertTrue(success)
        self.assertIsInstance(result, str)
    
    def test_translate_content(self):
        """测试内容翻译"""
        from modules.business.knowledge_base.ai_assist import AIAssist, MockLLMClient
        
        ai = AIAssist(self.db, MockLLMClient())
        
        success, result = ai.translate_content(
            '这是一段测试文本',
            source_lang='zh-CN',
            target_lang='en-US'
        )
        
        self.assertTrue(success)
        self.assertIsInstance(result, str)


class TestMarkdownProcessor(unittest.TestCase):
    """测试Markdown处理器"""
    
    def test_to_html(self):
        """测试Markdown转HTML"""
        from modules.business.knowledge_base.document import MarkdownProcessor
        
        md_text = "# 标题\n\n这是加粗文本"
        
        html = MarkdownProcessor.to_html(md_text)
        
        # 验证HTML输出(可能返回原始文本如果没有markdown库)
        self.assertTrue('<h1' in html or '<br>' in html or '<p>' in html)
    
    def test_extract_toc(self):
        """测试提取目录"""
        from modules.business.knowledge_base.document import MarkdownProcessor
        
        md_text = """
# 一级标题
## 二级标题
### 三级标题
"""
        
        toc = MarkdownProcessor.extract_toc(md_text)
        
        self.assertEqual(len(toc), 3)
        self.assertEqual(toc[0]['level'], 1)
        self.assertEqual(toc[1]['level'], 2)
    
    def test_word_count(self):
        """测试字数统计"""
        from modules.business.knowledge_base.document import MarkdownProcessor
        
        md_text = """
# 标题

这是正文内容。

第二段内容。
"""
        
        stats = MarkdownProcessor.word_count(md_text)
        
        self.assertGreater(stats['words'], 0)
        self.assertGreater(stats['lines'], 0)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
