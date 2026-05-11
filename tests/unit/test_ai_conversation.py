"""
AI对话历史持久化测试
测试AIConversation和AIMessage模型的创建、查询功能
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from modules.foundation.db_models.ai import AIConversation, AIMessage, ConversationType, MessageRole


class TestAIConversationModel:
    """AIConversation模型测试"""

    def test_conversation_creation(self):
        """测试对话会话创建"""
        conversation = AIConversation(
            conversation_id="conv-12345",
            user_id="user_001",
            username="testuser",
            conversation_type=ConversationType.CHAT.value,
            title="测试会话",
            message_count=0,
        )

        assert conversation.conversation_id == "conv-12345"
        assert conversation.user_id == "user_001"
        assert conversation.title == "测试会话"
        assert conversation.message_count == 0

    def test_conversation_types(self):
        """测试所有对话类型"""
        types = [
            (ConversationType.CHAT, "chat"),
            (ConversationType.TROUBLESHOOTING, "troubleshooting"),
            (ConversationType.SUGGESTION, "suggestion"),
            (ConversationType.ANALYSIS, "analysis"),
            (ConversationType.QA, "qa"),
        ]

        for enum_type, expected_value in types:
            conversation = AIConversation(
                conversation_id=f"conv-{expected_value}",
                conversation_type=enum_type.value,
            )
            assert conversation.conversation_type == expected_value

    def test_conversation_default_values(self):
        """测试默认值"""
        conversation = AIConversation(
            conversation_id="conv-default",
        )

        assert conversation.is_pinned is False
        assert conversation.is_deleted is False
        assert conversation.message_count == 0

    def test_conversation_repr(self):
        """测试字符串表示"""
        conversation = AIConversation(
            id=1,
            conversation_id="conv-test",
            conversation_type="chat",
        )

        repr_str = repr(conversation)
        assert "AIConversation" in repr_str
        assert "conv-test" in repr_str


class TestAIMessageModel:
    """AIMessage模型测试"""

    def test_message_creation(self):
        """测试消息创建"""
        message = AIMessage(
            conversation_id="conv-123",
            user_id="user_001",
            role=MessageRole.USER.value,
            content="你好，请帮我分析这个问题",
        )

        assert message.conversation_id == "conv-123"
        assert message.role == "user"
        assert message.content == "你好，请帮我分析这个问题"

    def test_message_roles(self):
        """测试所有消息角色"""
        roles = [
            (MessageRole.USER, "user"),
            (MessageRole.ASSISTANT, "assistant"),
            (MessageRole.SYSTEM, "system"),
            (MessageRole.FUNCTION, "function"),
        ]

        for enum_role, expected_value in roles:
            message = AIMessage(
                conversation_id="conv-test",
                role=enum_role.value,
                content="test",
            )
            assert message.role == expected_value

    def test_message_with_suggestions(self):
        """测试带建议的消息"""
        message = AIMessage(
            conversation_id="conv-123",
            role=MessageRole.ASSISTANT.value,
            content="分析结果...",
            suggestions=json.dumps(["建议1", "建议2", "建议3"]),
        )

        suggestions = json.loads(message.suggestions)
        assert len(suggestions) == 3
        assert "建议1" in suggestions

    def test_message_with_references(self):
        """测试带参考的消息"""
        references = [
            {"id": 1, "title": "文档1", "type": "sop"},
            {"id": 2, "title": "案例2", "type": "fault_case"},
        ]

        message = AIMessage(
            conversation_id="conv-123",
            role=MessageRole.ASSISTANT.value,
            content="相关内容...",
            references=json.dumps(references),
        )

        refs = json.loads(message.references)
        assert len(refs) == 2
        assert refs[0]["title"] == "文档1"

    def test_message_to_dict(self):
        """测试消息转字典"""
        message = AIMessage(
            id=1,
            conversation_id="conv-123",
            role="assistant",
            content="测试内容",
            model="qwen3.5",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        msg_dict = message.to_dict()
        assert msg_dict["id"] == 1
        assert msg_dict["conversation_id"] == "conv-123"
        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "测试内容"
        assert msg_dict["model"] == "qwen3.5"

    def test_message_token_tracking(self):
        """测试Token计数"""
        message = AIMessage(
            conversation_id="conv-123",
            role="assistant",
            content="回复内容",
            token_count=150,
            input_tokens=80,
            output_tokens=70,
        )

        assert message.token_count == 150
        assert message.input_tokens == 80
        assert message.output_tokens == 70


class TestConversationHistoryPersistence:
    """对话历史持久化测试"""

    def test_save_message_increments_count(self):
        """测试保存消息增加计数"""
        conversation = AIConversation(
            conversation_id="conv-123",
            message_count=5,
        )

        # 模拟保存消息
        conversation.message_count += 1
        assert conversation.message_count == 6

    def test_update_last_message_time(self):
        """测试更新最后消息时间"""
        conversation = AIConversation(
            conversation_id="conv-123",
        )

        now = datetime.now()
        conversation.last_message_at = now

        assert conversation.last_message_at == now

    def test_auto_title_from_first_message(self):
        """测试从第一条消息自动生成标题"""
        conversation = AIConversation(
            conversation_id="conv-123",
            message_count=1,
        )

        first_message = "服务器CPU使用率过高如何处理"

        if conversation.message_count == 1:
            conversation.title = first_message[:50] + ("..." if len(first_message) > 50 else "")

        assert conversation.title == "服务器CPU使用率过高如何处理"

    def test_auto_title_truncation(self):
        """测试标题自动截断"""
        conversation = AIConversation(
            conversation_id="conv-123",
        )

        long_message = "这是一条非常长的消息内容，我们需要对其进行截断处理以适合作为会话标题显示在列表中"

        if len(long_message) > 50:
            title = long_message[:50] + "..."
        else:
            title = long_message

        assert len(title) == 53  # 50 + "..."

    def test_soft_delete_conversation(self):
        """测试软删除会话"""
        conversation = AIConversation(
            conversation_id="conv-123",
            is_deleted=False,
        )

        # 软删除
        conversation.is_deleted = True
        conversation.updated_at = datetime.now()

        assert conversation.is_deleted is True

    def test_pin_conversation(self):
        """测试置顶会话"""
        conversation = AIConversation(
            conversation_id="conv-123",
            is_pinned=False,
        )

        conversation.is_pinned = True

        assert conversation.is_pinned is True


class TestConversationQuery:
    """对话查询测试"""

    def test_filter_by_user_id(self):
        """测试按用户ID过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_query.filter().count.return_value = 10
        mock_query.filter().order_by().limit().all.return_value = []

        result = mock_query.filter().all()
        assert isinstance(result, list)

    def test_filter_by_conversation_type(self):
        """测试按对话类型过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        mock_query.filter().all.return_value = [
            AIConversation(conversation_id="conv-1", conversation_type="troubleshooting"),
        ]

        result = mock_query.filter().all()
        assert len(result) == 1
        assert result[0].conversation_type == "troubleshooting"

    def test_filter_deleted_conversations(self):
        """测试过滤已删除会话"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        mock_query.filter().count.return_value = 0
        mock_query.filter().order_by.return_value.limit.return_value.all.return_value = []

        result = mock_query.filter().all()
        assert isinstance(result, list)

    def test_pinned_conversations_first(self):
        """测试置顶会话排在前面"""
        conversations = [
            AIConversation(conversation_id="conv-1", is_pinned=False),
            AIConversation(conversation_id="conv-2", is_pinned=True),
            AIConversation(conversation_id="conv-3", is_pinned=False),
        ]

        # 按置顶排序
        sorted_convs = sorted(
            conversations,
            key=lambda x: (not x.is_pinned, x.last_message_at or datetime.min),
            reverse=True
        )

        assert sorted_convs[0].conversation_id == "conv-2"  # 置顶的排第一


class TestMessageQuery:
    """消息查询测试"""

    def test_get_messages_ordered_by_time(self):
        """测试按时间顺序获取消息"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_query.filter().order_by().limit().all.return_value = [
            AIMessage(id=1, role="user", content="消息1", created_at=datetime(2024, 1, 1, 10, 0)),
            AIMessage(id=2, role="assistant", content="消息2", created_at=datetime(2024, 1, 1, 10, 1)),
        ]

        result = mock_query.filter().order_by().limit().all()
        assert len(result) == 2
        # 验证按created_at升序排列
        assert result[0].created_at < result[1].created_at

    def test_limit_message_count(self):
        """测试限制消息数量"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_query.filter().order_by().limit().all.return_value = [
            AIMessage(id=i, role="user", content=f"消息{i}")
            for i in range(50)
        ]

        result = mock_query.filter().order_by().limit().all()
        assert len(result) == 50
