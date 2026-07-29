"""
转写记录 ORM 模型
存储 Fun-ASR 语音转写的结果，包含说话人分离信息
每一条记录代表一个发言人的一段发言
"""
from sqlalchemy import (
    Column, BigInteger, String, Float, Text, Integer, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="转写记录ID")
    meeting_id = Column(
        BigInteger,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        comment="会议ID",
    )
    # 发言人标签，ASR 返回的 speaker_id（如 speaker_1, speaker_2）
    speaker = Column(String(50), nullable=False, comment="发言人标签")
    # 该段发言的开始时间（秒）
    start_time = Column(Float, default=0, comment="开始时间(秒)")
    # 该段发言的结束时间（秒）
    end_time = Column(Float, default=0, comment="结束时间(秒)")
    # 发言的文本内容
    content = Column(Text, nullable=False, comment="发言内容")
    # 在会议中的排序序号，用于按时间顺序展示转写结果
    sequence = Column(Integer, default=0, comment="排序序号")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
