"""
FastAPI 应用主入口
基于LangChain的智能会议纪要助手系统
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import CORS_ORIGINS, UPLOAD_DIR
from database import init_db, SessionLocal
from models.meeting import Meeting
from routers import auth, meetings, summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时：初始化数据库表、确保上传目录存在
    关闭时：清理资源
    """
    # === 启动时执行 ===
    print("[系统启动] 正在初始化数据库表...")
    init_db()
    print("[系统启动] 数据库表初始化完成")

    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"[系统启动] 上传目录已就绪: {UPLOAD_DIR}")

    # 恢复服务重启前卡在"处理中"状态的会议
    _recover_stale_meetings()

    yield  # 应用运行中...

    # === 关闭时执行 ===
    print("[系统关闭] 正在清理资源...")


def _recover_stale_meetings():
    """服务重启时，将卡在"处理中"的会议重置，避免永久卡死"""
    db = SessionLocal()
    try:
        stale = db.query(Meeting).filter(
            Meeting.status.in_(["transcribing", "summarizing"])
        ).all()
        if stale:
            for m in stale:
                m.status = "uploaded" if m.status == "transcribing" else "transcribed"
                m.error_message = "服务重启，处理中断，请重新操作"
            db.commit()
            print(f"[启动恢复] 已重置 {len(stale)} 个中断的会议")
    except Exception as e:
        print(f"[启动恢复] 恢复失败: {e}")
        db.rollback()
    finally:
        db.close()


# 创建 FastAPI 应用实例
app = FastAPI(
    title="基于LangChain的智能会议纪要助手系统",
    description="支持音频/视频上传、语音转写(ASR)、AI摘要生成、要点提炼、发言总结、纪要导出",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================
# CORS 跨域中间件配置
# 允许前端开发服务器 (Vite :5173) 访问后端 API
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 注册路由模块
# ============================================================
app.include_router(auth.router, prefix="/api/auth", tags=["认证管理"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["会议管理"])
app.include_router(summary.router, prefix="/api/meetings", tags=["纪要管理"])

# 静态文件服务 - 用于访问上传的文件
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """
    根路径 - 系统信息
    """
    return {
        "name": "基于LangChain的智能会议纪要助手系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "ok", "message": "服务运行正常"}
