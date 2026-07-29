"""
用户相关的 Pydantic 请求/响应模型
用于 API 数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """
    用户注册请求体
    """
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码(明文)")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")


class UserLoginRequest(BaseModel):
    """
    用户登录请求体
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码(明文)")


class UserResponse(BaseModel):
    """
    用户信息响应体（不包含密码）
    """
    id: int
    username: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        # 允许从 ORM 对象直接转换
        from_attributes = True


class TokenResponse(BaseModel):
    """
    JWT Token 响应体
    """
    access_token: str = Field(..., description="JWT Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    user: UserResponse = Field(..., description="用户信息")
