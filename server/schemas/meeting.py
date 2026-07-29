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
