"""
用户 ORM 模型
密码使用 MD5 加密存储
"""
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    # 密码存储为32位小写 MD5 哈希值
    password = Column(String(128), nullable=False, comment="MD5加密密码")
    email = Column(String(100), nullable=True, comment="邮箱")
    avatar = Column(String(500), nullable=True, comment="头像URL")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
