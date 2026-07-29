"""
发言人总结模型
对每个发言人各自的发言内容进行 AI 总结
"""
from sqlalchemy import (
    Column, BigInteger, String, Text, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from database import Base


class SpeakerSummary(Base):
    __tablename__ = "speaker_summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="发言人总结ID")
    meeting_id = Column(
        BigInteger,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        comment="会议ID",
    )
    # 发言人标签（如 speaker_1, speaker_2）
    speaker = Column(String(50), nullable=False, comment="发言人")
    # AI 生成的该发言人发言内容总结
    summary = Column(Text, nullable=True, comment="发言内容总结")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
