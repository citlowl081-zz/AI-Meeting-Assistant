"""
会议 ORM 模型
记录上传的音频/视频文件信息和处理状态
"""
from sqlalchemy import (
    Column, BigInteger, String, Integer, DateTime, Text, Enum, ForeignKey
)
from sqlalchemy.sql import func
from database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="会议ID")
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="上传用户ID",
    )
    title = Column(String(255), nullable=False, comment="会议标题")
    original_filename = Column(String(500), nullable=True, comment="原始文件名")
    file_path = Column(String(500), nullable=True, comment="服务器存储路径")
    file_type = Column(String(20), nullable=True, comment="文件类型(mp3/wav/m4a/mp4)")
    file_size = Column(BigInteger, default=0, comment="文件大小(bytes)")
    duration = Column(Integer, default=0, comment="音频时长(秒)")

    # 处理状态流转: uploaded → transcribing → transcribed → summarizing → completed
    # 如果任何步骤失败，状态变为 failed，error_message 记录错误详情
    status = Column(
        Enum(
            "uploaded", "transcribing", "transcribed",
            "summarizing", "completed", "failed",
            name="meeting_status"
        ),
        default="uploaded",
        comment="处理状态",
    )
    error_message = Column(Text, nullable=True, comment="错误信息")
    # JSON 格式存储说话人名称映射，如 {"speaker1": "张医生", "speaker2": "李家属"}
    speaker_mapping = Column(Text, nullable=True, comment="说话人名称映射JSON")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
