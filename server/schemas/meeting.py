"""
会议相关的 Pydantic 请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MeetingCreateRequest(BaseModel):
    """
    创建会议请求体（上传时使用）
    """
    title: str = Field(..., min_length=1, max_length=255, description="会议标题")


class MeetingResponse(BaseModel):
    """
    会议基本信息响应体
    """
    id: int
    user_id: int
    title: str
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = 0
    duration: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    speaker_mapping: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """
    会议列表分页响应体
    """
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    items: list[MeetingResponse] = Field(default_factory=list, description="会议列表")


class DashboardStatsResponse(BaseModel):
    """
    仪表盘统计响应体
    """
    total_meetings: int = Field(default=0, description="会议总数")
    uploaded_count: int = Field(default=0, description="已上传数量")
    transcribing_count: int = Field(default=0, description="转写中数量")
    transcribed_count: int = Field(default=0, description="已转写数量")
    summarizing_count: int = Field(default=0, description="摘要生成中数量")
    completed_count: int = Field(default=0, description="已完成数量")
    failed_count: int = Field(default=0, description="失败数量")


class SpeakerMappingRequest(BaseModel):
    """
    说话人名称映射请求体
    """
    mapping: dict = Field(..., description="说话人名称映射，如 {'speaker1': '张医生', 'speaker2': '李家属'}")
