"""
AI对话历史数据库模型
用于持久化AI对话记录
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.sql import func

from .base import Base


class ConversationType(str, Enum):
    """对话类型"""
    CHAT = "chat"                     # 通用聊天
    TROUBLESHOOTING = "troubleshooting"  # 故障排查
    SUGGESTION = "suggestion"         # 建议生成
    ANALYSIS = "analysis"             # 分析解读
    QA = "qa"                        # 知识问答


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"


class AIConversation(Base):
    """
    AI对话会话模型
    存储对话会话的元信息
    """
    __tablename__ = 'ai_conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 会话标识
    conversation_id = Column(String(128), unique=True, index=True, nullable=False, comment='会话ID')

    # 用户信息
    user_id = Column(String(64), index=True, comment='用户ID')
    username = Column(String(64), comment='用户名')

    # 会话类型
    conversation_type = Column(String(32), default=ConversationType.CHAT.value, comment='会话类型')

    # 标题/摘要
    title = Column(String(256), comment='会话标题')
    summary = Column(Text, comment='会话摘要')

    # 状态
    is_pinned = Column(Boolean, default=False, comment='是否置顶')
    is_deleted = Column(Boolean, default=False, comment='是否删除')

    # 上下文信息 (JSON)
    context = Column(Text, comment='上下文信息(JSON)')

    # 统计
    message_count = Column(Integer, default=0, comment='消息数量')

    # 时间
    last_message_at = Column(DateTime, comment='最后消息时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联
    device_id = Column(Integer, comment='关联设备ID')
    workorder_id = Column(Integer, ForeignKey('work_orders.id'), comment='关联工单ID')

    # 索引
    __table_args__ = (
        Index('idx_conv_user_time', 'user_id', 'last_message_at'),
        Index('idx_conv_type_time', 'conversation_type', 'created_at'),
        Index('idx_conv_deleted_time', 'is_deleted', 'last_message_at'),
    )

    def __repr__(self):
        return f"<AIConversation(id={self.id}, conversation_id='{self.conversation_id}', type='{self.conversation_type}')>"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Python-side defaults (SQLAlchemy default only applies on INSERT)
        if self.is_pinned is None:
            self.is_pinned = False
        if self.is_deleted is None:
            self.is_deleted = False
        if self.message_count is None:
            self.message_count = 0


class AIMessage(Base):
    """
    AI对话消息模型
    存储对话中的每条消息
    """
    __tablename__ = 'ai_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联会话
    conversation_id = Column(String(128), index=True, nullable=False, comment='会话ID')
    user_id = Column(String(64), index=True, comment='用户ID')

    # 消息内容
    role = Column(String(32), nullable=False, comment='角色: user, assistant, system, function')
    content = Column(Text, comment='消息内容')

    # 可选字段
    name = Column(String(128), comment='function name (for function role)')
    function_call = Column(Text, comment='函数调用信息(JSON)')

    # 消息统计
    token_count = Column(Integer, comment='Token数量')
    input_tokens = Column(Integer, comment='输入Token数')
    output_tokens = Column(Integer, comment='输出Token数')

    # LLM元数据
    model = Column(String(128), comment='使用的模型')
    completion_reason = Column(String(64), comment='结束原因')

    # 建议/引用
    suggestions = Column(Text, comment='建议列表(JSON)')
    references = Column(Text, comment='参考资料(JSON)')

    # 错误信息
    error_message = Column(Text, comment='错误信息')

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='创建时间')

    # 关联
    device_id = Column(Integer, comment='关联设备ID')

    # 索引
    __table_args__ = (
        Index('idx_msg_conv_time', 'conversation_id', 'created_at'),
        Index('idx_msg_user_time', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<AIMessage(id={self.id}, conversation_id='{self.conversation_id}', role='{self.role}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'name': self.name,
            'function_call': self.function_call,
            'suggestions': self.suggestions,
            'references': self.references,
            'model': self.model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
