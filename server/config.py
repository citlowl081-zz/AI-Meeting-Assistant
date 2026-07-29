"""
系统配置文件
包含 DashScope AI 平台、数据库、文件上传、JWT 等核心配置
"""

import os

# ============================================================
# DashScope 百炼平台 AI 配置
# 使用 OpenAI 兼容模式调用，base_url 格式:
#   https://{workspace-id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
# ============================================================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_REMOVED_ROTATE_IMMEDIATELY")
DASHSCOPE_WORKSPACE_ID = os.getenv("DASHSCOPE_WORKSPACE_ID", "ws-ujry5px7m5k2m903")
DASHSCOPE_BASE_URL = (
    f"https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)

# 聊天模型：用于摘要生成、要点提取、发言总结
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.6-plus")
# 嵌入模型：用于文本向量化，向量维度 2048
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIMENSION = 2048
# 语音识别模型：paraformer-v2 中文识别率远优于 fun-asr，且原生支持说话人分离
# 备选: fun-asr（兼容更多格式，但准确率较低）
ASR_MODEL = os.getenv("ASR_MODEL", "paraformer-v2")

# ============================================================
# MySQL 数据库配置 (端口 3308)
# ============================================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3308"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "meeting_assistant")

# SQLAlchemy 数据库连接 URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# ============================================================
# 文件上传配置
# uploads/ 为项目相对路径，在 Windows 部署时可改为 D:/uploads19/
# ============================================================
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/")
# 最大上传文件大小：6GB
MAX_UPLOAD_SIZE = 6 * 1024 * 1024 * 1024
# 支持的文件格式
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "aac", "flac", "ogg", "wma"}

# ============================================================
# JWT 认证配置
# ============================================================
JWT_SECRET = os.getenv("JWT_SECRET", "meeting-assistant-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24  # Token 有效期 24 小时

# ============================================================
# 服务配置
# ============================================================
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
# 前端开发服务器地址（CORS 白名单）
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite 默认端口
    "http://localhost:3000",
]
