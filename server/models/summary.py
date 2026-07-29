"""
摘要模型和待办事项模型
存储 AI 生成的会议摘要、关键词和待办事项
"""
from sqlalchemy import (
    Column, BigInteger, String, Text, DateTime, Enum, ForeignKey
)
from sqlalchemy.sql import func
from database import Base


class Summary(Base):
    """
    会议摘要表
    每个会议只有一条摘要记录（meeting_id 唯一约束）
    """
    __tablename__ = "summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="摘要ID")
    meeting_id = Column(
        BigInteger,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 确保每个会议只有一条摘要
        comment="会议ID",
    )
    # AI 生成的全文摘要
    full_summary = Column(Text, nullable=True, comment="全文摘要")
    # 逗号分隔的关键词列表
    keywords = Column(String(500), nullable=True, comment="关键词(逗号分隔)")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class ActionItem(Base):
    """
    待办事项表
    从会议内容中提取的行动项，包含负责人和截止时间
    """
    __tablename__ = "action_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="待办事项ID")
    meeting_id = Column(
        BigInteger,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        comment="会议ID",
    )
    content = Column(String(500), nullable=False, comment="待办事项内容")
    responsible_person = Column(String(50), nullable=True, comment="负责人")
    deadline = Column(String(50), nullable=True, comment="截止时间")
    # 待办状态：pending-未完成, completed-已完成
    status = Column(
        Enum("pending", "completed", name="action_status"),
        default="pending",
        comment="完成状态",
    )
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
