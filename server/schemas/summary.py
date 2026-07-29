"""
摘要/转写/待办相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# 转写相关
# ============================================================
class TranscriptSegment(BaseModel):
    """
    单个转写片段（一个说话人的一段发言）
    """
    id: Optional[int] = None
    speaker: str = Field(..., description="说话人标签")
    start_time: float = Field(..., description="开始时间(秒)")
    end_time: float = Field(..., description="结束时间(秒)")
    content: str = Field(..., description="发言内容")
    sequence: int = Field(default=0, description="排序序号")

    class Config:
        from_attributes = True


class TranscriptResponse(BaseModel):
    """
    完整转写结果响应体
    """
    meeting_id: int
    # 按说话人分组后的转写结果
    speakers: List[str] = Field(default_factory=list, description="说话人列表")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="转写片段列表")
    # 完整的纯文本转写内容
    full_text: str = Field(default="", description="完整转写文本")


# ============================================================
# 摘要相关
# ============================================================
class SummaryResponse(BaseModel):
    """
    会议摘要响应体
    """
    id: Optional[int] = None
    meeting_id: int
    full_summary: Optional[str] = Field(None, description="全文摘要")
    keywords: Optional[str] = Field(None, description="关键词(逗号分隔)")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# 待办事项相关
# ============================================================
class ActionItemResponse(BaseModel):
    """
    待办事项响应体
    """
    id: Optional[int] = None
    meeting_id: Optional[int] = None
    content: str = Field(..., description="待办事项内容")
    responsible_person: Optional[str] = Field(None, description="负责人")
    deadline: Optional[str] = Field(None, description="截止时间")
    status: str = Field(default="pending", description="完成状态")

    class Config:
        from_attributes = True


# ============================================================
# 发言人总结相关
# ============================================================
class SpeakerSummaryResponse(BaseModel):
    """
    发言人总结响应体
    """
    id: Optional[int] = None
    meeting_id: Optional[int] = None
    speaker: str = Field(..., description="发言人")
    summary: Optional[str] = Field(None, description="发言内容总结")

    class Config:
        from_attributes = True


# ============================================================
# 会议完整纪要（聚合所有信息）
# ============================================================
class MeetingMinutesResponse(BaseModel):
    """
    会议完整纪要响应体
    聚合了转写、摘要、待办事项和发言人总结
    """
    meeting_id: int
    title: str
    status: str
    transcript: Optional[TranscriptResponse] = None
    summary: Optional[SummaryResponse] = None
    action_items: List[ActionItemResponse] = Field(default_factory=list)
    speaker_summaries: List[SpeakerSummaryResponse] = Field(default_factory=list)
