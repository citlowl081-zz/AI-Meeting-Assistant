"""
数据库连接和会话管理
使用 SQLAlchemy 2.0 连接 MySQL 8
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# 创建数据库引擎
# pool_size=10: 连接池大小
# pool_recycle=3600: 连接回收时间(秒)，避免 MySQL 8 小时超时断连
# pool_pre_ping=True: 每次使用前检查连接是否有效
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,  # 生产环境设为 False
)

# 会话工厂，每个请求使用独立的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 模型基类，所有模型继承此类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖注入函数
    用于 FastAPI 路由中，确保请求结束后关闭会话
    用法: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构
    在应用启动时调用，自动创建所有 ORM 模型对应的数据表
    """
    Base.metadata.create_all(bind=engine)
