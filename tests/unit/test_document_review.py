"""
文档多级审核流程测试
BM-05 文档多级审核模块单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from importlib import util

import sys
import os

# 直接从模块文件导入，避免通过 modules.business.__init__.py 触发所有依赖
def import_from_path(module_name, file_path):
    spec = util.spec_from_file_location(module_name, file_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

doc_review_path = '/home/zcxx/.hermes/projects/itops_platform/modules/business/knowledge_base/document_review.py'
dr = import_from_path('document_review', doc_review_path)
DocumentReviewFlow = dr.DocumentReviewFlow
ReviewFlowConfig = dr.ReviewFlowConfig
ReviewLevelConfig = dr.ReviewLevelConfig
ReviewLevel = dr.ReviewLevel
ReviewRecord = dr.ReviewRecord
ReviewStatus = dr.ReviewStatus
ReviewAction = dr.ReviewAction


class TestDocumentReviewFlow:
    """文档多级审核流程测试"""
    
    def setup_method(self):
        """每个测试方法前 setup"""
        self.flow_manager = DocumentReviewFlow()
        self.ReviewFlowConfig = ReviewFlowConfig
        self.ReviewLevelConfig = ReviewLevelConfig
        self.ReviewLevel = ReviewLevel
        self.ReviewRecord = ReviewRecord
        self.ReviewStatus = ReviewStatus
    
    def test_flow_manager_initialization(self):
        """测试流程管理器初始化"""
        assert self.flow_manager is not None
        # 应该有默认流程
        flows = self.flow_manager.list_flows()
        assert len(flows) >= 3  # standard, simple, urgent
    
    def test_add_custom_flow(self):
        """测试添加自定义流程"""
        custom_flow = self.ReviewFlowConfig(
            id='custom-flow',
            name='自定义流程',
            description='这是一个自定义审核流程',
            levels=[
                self.ReviewLevelConfig(
                    level=self.ReviewLevel.LEVEL_1,
                    name='技术审核',
                    description='技术人员审核',
                    reviewer_role='tech_reviewer',
                    timeout_hours=24,
                ),
                self.ReviewLevelConfig(
                    level=self.ReviewLevel.LEVEL_2,
                    name='管理层审核',
                    description='管理层最终审批',
                    reviewer_role='manager',
                    timeout_hours=48,
                ),
            ],
        )
        
        flow_id = self.flow_manager.add_flow(custom_flow)
        assert flow_id == 'custom-flow'
        
        retrieved_flow = self.flow_manager.get_flow('custom-flow')
        assert retrieved_flow is not None
        assert retrieved_flow.name == '自定义流程'
        assert len(retrieved_flow.levels) == 2
    
    def test_update_flow(self):
        """测试更新流程"""
        # 使用默认流程
        standard_flow = self.flow_manager.get_flow('standard')
        original_name = standard_flow.name
        
        standard_flow.name = '更新后的名称'
        standard_flow.levels[0].timeout_hours = 12
        self.flow_manager.update_flow(standard_flow)
        
        updated_flow = self.flow_manager.get_flow('standard')
        assert updated_flow.name == '更新后的名称'
        assert updated_flow.levels[0].timeout_hours == 12
    
    def test_delete_flow(self):
        """测试删除流程"""
        # 先添加一个可删除的流程
        temp_flow = self.ReviewFlowConfig(
            id='temp-flow',
            name='临时流程',
            levels=[],
        )
        self.flow_manager.add_flow(temp_flow)
        assert self.flow_manager.get_flow('temp-flow') is not None
        
        # 删除
        result = self.flow_manager.delete_flow('temp-flow')
        assert result is True
        assert self.flow_manager.get_flow('temp-flow') is None
        
        # 删除不存在的流程
        result = self.flow_manager.delete_flow('non-existent')
        assert result is False
    
    def test_select_flow_by_doc_type(self):
        """测试根据文档类型选择流程"""
        # SOP文档应该选择standard流程
        flow = self.flow_manager.select_flow('sop')
        assert flow is not None
        assert flow.id == 'standard'
        
        # notice文档应该选择simple流程
        flow = self.flow_manager.select_flow('notice')
        assert flow is not None
        assert flow.id == 'simple'
    
    def test_submit_for_review(self):
        """测试提交审核"""
        record = self.flow_manager.submit_for_review(
            flow_id='standard',
            document_id=1,
            document_type='sop',
            document_title='测试文档',
            submitter='test_user',
            comment='请审核',
        )
        
        assert record is not None
        assert record.flow_id == 'standard'
        assert record.document_id == 1
        assert record.document_type == 'sop'
        assert record.status == self.ReviewStatus.PENDING
        assert record.current_level == 1
        assert record.total_levels == 3  # standard流程有3级
        assert record.submitted_by == 'test_user'
        assert len(record.history) == 1
        assert record.history[0]['action'] == 'submit'
    
    def test_submit_duplicate_review(self):
        """测试重复提交审核"""
        # 第一次提交
        self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=100,
            document_type='notice',
            document_title='第一份文档',
            submitter='user1',
        )
        
        # 第二次提交同一文档
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=100,
            document_type='notice',
            document_title='第二份文档',
            submitter='user2',
        )
        
        # 应该失败
        assert record is None
    
    def test_approve_single_level(self):
        """测试批准单级审核"""
        # 使用simple流程（只有一级）
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=200,
            document_type='notice',
            document_title='简单通知',
            submitter='submitter',
            comment='请快速审核',
        )
        
        review_id = record.id
        
        # 批准
        result = self.flow_manager.approve(review_id, 'reviewer1', '同意')
        assert result is True
        
        updated_record = self.flow_manager.get_review(review_id)
        assert updated_record.status == self.ReviewStatus.APPROVED
        assert updated_record.completed_by == 'reviewer1'
        assert updated_record.completed_at is not None
    
    def test_approve_multi_level(self):
        """测试批准多级审核"""
        record = self.flow_manager.submit_for_review(
            flow_id='standard',
            document_id=300,
            document_type='sop',
            document_title='标准流程文档',
            submitter='author',
        )
        
        review_id = record.id
        
        # 第一级审核
        result = self.flow_manager.approve(review_id, 'level1_reviewer', '初审通过')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.IN_REVIEW
        assert updated.current_level == 2  # 进入第二级
        
        # 第二级审核
        result = self.flow_manager.approve(review_id, 'level2_reviewer', '复审通过')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.IN_REVIEW
        assert updated.current_level == 3  # 进入第三级
        
        # 第三级审核（最后一级别）
        result = self.flow_manager.approve(review_id, 'level3_reviewer', '终审通过')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.APPROVED
        assert updated.completed_at is not None
    
    def test_reject_review(self):
        """测试拒绝审核"""
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=400,
            document_type='notice',
            document_title='测试拒绝',
            submitter='author',
        )
        
        review_id = record.id
        
        # 拒绝
        result = self.flow_manager.reject(review_id, 'reviewer', '内容不符合要求')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.REJECTED
        assert updated.final_comment == '内容不符合要求'
    
    def test_request_revision(self):
        """测试要求修订"""
        record = self.flow_manager.submit_for_review(
            flow_id='standard',
            document_id=500,
            document_type='sop',
            document_title='需要修订的文档',
            submitter='author',
        )
        
        review_id = record.id
        
        # 第一级要求修订
        result = self.flow_manager.request_revision(review_id, 'reviewer', '请补充详细内容')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.REVISION_REQUESTED
    
    def test_resubmit_after_revision(self):
        """测试修订后重新提交"""
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=600,
            document_type='notice',
            document_title='修订后重新提交',
            submitter='author',
        )
        
        review_id = record.id
        
        # 要求修订
        self.flow_manager.request_revision(review_id, 'reviewer', '需要修改')
        
        # 重新提交
        result = self.flow_manager.resubmit(review_id, 'author', '已按要求修改')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.PENDING
    
    def test_withdraw_review(self):
        """测试撤回审核"""
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=700,
            document_type='notice',
            document_title='待撤回的文档',
            submitter='author',
        )
        
        review_id = record.id
        
        # 撤回
        result = self.flow_manager.withdraw(review_id, 'author', '误提交，撤回')
        assert result is True
        
        updated = self.flow_manager.get_review(review_id)
        assert updated.status == self.ReviewStatus.WITHDRAWN
    
    def test_get_review_by_document(self):
        """测试根据文档ID获取审核记录"""
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=800,
            document_type='notice',
            document_title='查找测试',
            submitter='author',
        )
        
        retrieved = self.flow_manager.get_review_by_document(800)
        assert retrieved is not None
        assert retrieved.id == record.id
        
        # 不存在的文档
        retrieved = self.flow_manager.get_review_by_document(999999)
        assert retrieved is None
    
    def test_list_reviews(self):
        """测试列出审核记录"""
        # 提交几个审核
        for i in range(5):
            self.flow_manager.submit_for_review(
                flow_id='simple',
                document_id=1000 + i,
                document_type='notice',
                document_title=f'文档{i}',
                submitter=f'user{i}',
            )
        
        # 列出所有
        reviews = self.flow_manager.list_reviews()
        assert len(reviews) >= 5
        
        # 按状态过滤
        pending_reviews = self.flow_manager.list_reviews(status=self.ReviewStatus.PENDING)
        for r in pending_reviews:
            assert r.status == self.ReviewStatus.PENDING
        
        # 按提交人过滤
        user0_reviews = self.flow_manager.list_reviews(submitted_by='user0')
        assert len(user0_reviews) >= 1
        assert user0_reviews[0].submitted_by == 'user0'
    
    def test_callback_registration(self):
        """测试回调函数注册"""
        callback_executed = {'count': 0}
        
        def test_callback(record):
            callback_executed['count'] += 1
        
        self.flow_manager.register_callback('approved', test_callback)
        
        # 提交并批准审核
        record = self.flow_manager.submit_for_review(
            flow_id='simple',
            document_id=900,
            document_type='notice',
            document_title='回调测试',
            submitter='author',
        )
        
        self.flow_manager.approve(record.id, 'reviewer', 'OK')
        
        # 回调应该被执行了（因为simple流程一级就批准了）
        assert callback_executed['count'] >= 1


class TestReviewLevelConfig:
    """审核级别配置测试"""
    
    def test_review_level_config_creation(self):
        """测试审核级别配置创建"""
        config = ReviewLevelConfig(
            level=ReviewLevel.LEVEL_1,
            name='初审',
            description='第一级审核',
            reviewer_role='team_leader',
            specific_reviewers=['user1', 'user2'],
            require_all_approved=True,
            auto_assign=True,
            allow_skip=False,
            timeout_hours=24,
        )
        
        assert config.level == ReviewLevel.LEVEL_1
        assert config.name == '初审'
        assert len(config.specific_reviewers) == 2
        assert config.timeout_hours == 24
    
    def test_review_level_config_to_dict(self):
        """测试审核级别配置转字典"""
        config = ReviewLevelConfig(
            level=ReviewLevel.LEVEL_1,
            name='测试级别',
            reviewer_role='test_role',
        )
        
        config_dict = config.to_dict()
        assert config_dict['level'] == 'level_1'
        assert config_dict['name'] == '测试级别'
        assert config_dict['reviewer_role'] == 'test_role'


class TestReviewFlowConfig:
    """审核流程配置测试"""
    
    def test_review_flow_config_creation(self):
        """测试审核流程配置创建"""
        config = ReviewFlowConfig(
            id='test-config',
            name='测试流程',
            description='这是一个测试流程',
            levels=[
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_1,
                    name='级别1',
                    reviewer_role='role1',
                ),
            ],
            enable_timeout_notification=True,
            timeout_notification_interval=12,
            applicable_doc_types=['sop', 'policy'],
            created_by='test_user',
        )
        
        assert config.id == 'test-config'
        assert config.name == '测试流程'
        assert len(config.levels) == 1
        assert 'sop' in config.applicable_doc_types
    
    def test_review_flow_config_to_dict(self):
        """测试审核流程配置转字典"""
        config = ReviewFlowConfig(
            id='test-id',
            name='测试',
            levels=[],
        )
        
        config_dict = config.to_dict()
        assert config_dict['id'] == 'test-id'
        assert config_dict['name'] == '测试'
        assert 'levels' in config_dict


class TestReviewRecord:
    """审核记录测试"""
    
    def test_review_record_creation(self):
        """测试审核记录创建"""
        record = ReviewRecord(
            id='review-1',
            flow_id='standard',
            document_id=1,
            document_type='sop',
            document_title='测试文档',
            total_levels=3,
            submitted_by='test_user',
            submit_comment='请审核',
        )
        
        assert record.id == 'review-1'
        assert record.status == ReviewStatus.PENDING
        assert record.current_level == 1
        assert record.total_levels == 3
    
    def test_review_record_to_dict(self):
        """测试审核记录转字典"""
        record = ReviewRecord(
            id='review-1',
            flow_id='standard',
            document_id=1,
            document_type='sop',
            document_title='测试文档',
            submitted_by='test_user',
        )
        
        record_dict = record.to_dict()
        assert record_dict['id'] == 'review-1'
        assert record_dict['flow_id'] == 'standard'
        assert record_dict['status'] == 'pending'
        assert record_dict['submitted_by'] == 'test_user'


class TestReviewStatus:
    """审核状态枚举测试"""
    
    def test_review_status_values(self):
        """测试审核状态枚举值"""
        assert ReviewStatus.PENDING.value == 'pending'
        assert ReviewStatus.IN_REVIEW.value == 'in_review'
        assert ReviewStatus.APPROVED.value == 'approved'
        assert ReviewStatus.REJECTED.value == 'rejected'
        assert ReviewStatus.REVISION_REQUESTED.value == 'revision_requested'
        assert ReviewStatus.WITHDRAWN.value == 'withdrawn'


class TestReviewLevel:
    """审核级别枚举测试"""
    
    def test_review_level_values(self):
        """测试审核级别枚举值"""
        assert ReviewLevel.LEVEL_1.value == 'level_1'
        assert ReviewLevel.LEVEL_2.value == 'level_2'
        assert ReviewLevel.LEVEL_3.value == 'level_3'


class TestReviewAction:
    """审核动作枚举测试"""
    
    def test_review_action_values(self):
        """测试审核动作枚举值"""
        assert ReviewAction.SUBMIT.value == 'submit'
        assert ReviewAction.APPROVE.value == 'approve'
        assert ReviewAction.REJECT.value == 'reject'
        assert ReviewAction.REQUEST_REVISION.value == 'request_revision'
        assert ReviewAction.WITHDRAW.value == 'withdraw'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
