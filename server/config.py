"""
系统配置文件
所有敏感配置从 .env 环境变量文件加载，不硬编码到代码中
"""
import os
from urllib.parse import quote_plus

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 优先从 server/.env 加载，其次从项目根目录 .env
    _env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
    else:
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass  # dotenv 未安装时跳过

# ============================================================
# 必填配置校验（生产环境启动时必须设置，否则报错）
# ============================================================
_required = {
    "DASHSCOPE_API_KEY": "DashScope API密钥，在百炼平台获取: https://bailian.console.aliyun.com/",
    "DASHSCOPE_WORKSPACE_ID": "DashScope工作空间ID",
}
_missing = [k for k, v in _required.items() if not os.getenv(k)]
if _missing:
    _msgs = "\n  - ".join([f"{k}: {_required[k]}" for k in _missing])
    raise RuntimeError(
        f"缺少必要的环境变量，请在 server/.env 文件中设置:\n  - {_msgs}\n"
        f"可参考 server/.env.example 复制并修改"
    )

# ============================================================
# DashScope 百炼平台 AI 配置
# base_url 格式: https://{workspace-id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
# ============================================================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_WORKSPACE_ID = os.getenv("DASHSCOPE_WORKSPACE_ID")
DASHSCOPE_BASE_URL = (
    f"https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)

# 聊天模型：用于摘要生成、要点提取、发言总结
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.6-plus")
# 嵌入模型：用于文本向量化，向量维度 2048
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "2048"))
# 语音识别模型：paraformer-v2 中文识别率远优于 fun-asr，且原生支持说话人分离
ASR_MODEL = os.getenv("ASR_MODEL", "paraformer-v2")

# ============================================================
# MySQL 数据库配置 (端口 3308)
# 密码使用 URL 编码，防止特殊字符导致连接串解析错误
# ============================================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3308"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "meeting_assistant")

# SQLAlchemy 数据库连接 URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# ============================================================
# JWT 认证配置
# ============================================================
JWT_SECRET = os.getenv("JWT_SECRET", "meeting-assistant-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# ============================================================
# 文件上传配置
# ============================================================
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(6 * 1024 * 1024 * 1024)))
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "aac", "flac", "ogg", "wma"}

# ============================================================
# 服务配置
# ============================================================
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]
