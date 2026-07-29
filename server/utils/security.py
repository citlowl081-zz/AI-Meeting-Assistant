"""
安全模块：MD5 密码加密 + JWT Token 认证
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS


def md5_hash(password: str) -> str:
    """
    使用 MD5 算法对密码进行哈希加密
    @param password: 明文密码
    @return: 32位小写 MD5 哈希值
    """
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与加密后的密码匹配
    @param plain_password: 明文密码
    @param hashed_password: 数据库中存储的 MD5 加密密码
    @return: 是否匹配
    """
    return md5_hash(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    @param data: 要编码到 Token 中的数据（通常包含 user_id, username）
    @param expires_delta: 自定义过期时间，默认使用配置中的 JWT_EXPIRE_HOURS
    @return: JWT Token 字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    # exp 是 JWT 标准过期时间字段
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解析并验证 JWT Token
    @param token: JWT Token 字符串
    @return: 解码后的载荷数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
