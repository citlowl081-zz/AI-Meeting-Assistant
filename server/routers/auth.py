"""
认证路由模块
处理用户注册、登录、获取当前用户信息
密码使用 MD5 加密存储
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from utils.security import md5_hash, verify_password, create_access_token, decode_access_token

router = APIRouter()
# HTTP Bearer Token 认证方案
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前登录用户
    作为 FastAPI 依赖项注入到需要认证的路由中
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    # 从 Token 中获取用户ID
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 数据不完整")

    # 查询数据库获取用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或被删除")
    return user


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    注册新用户
    - 校验用户名唯一性
    - 使用 MD5 加密密码
    - 返回 JWT Token
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 创建用户，密码使用 MD5 加密
    user = User(
        username=request.username,
        password=md5_hash(request.password),  # MD5加密
        email=request.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 注册成功后直接返回 Token（自动登录）
    token = create_access_token({"user_id": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    - 验证用户名和密码（MD5比对）
    - 返回 JWT Token
    """
    # 查询用户
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证明文密码与存储的 MD5 哈希是否匹配
    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 签发 JWT Token
    token = create_access_token({"user_id": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息（需要认证）
    """
    return UserResponse.model_validate(current_user)
