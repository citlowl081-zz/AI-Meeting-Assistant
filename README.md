# 基于LangChain的智能会议纪要助手系统

一个完整的企业级智能会议纪要助手系统，支持音频/视频上传、语音转写（说话人分离）、AI摘要生成、要点提炼、发言总结、纪要导出等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.10+, FastAPI, LangChain, SQLAlchemy, DashScope SDK |
| **前端** | Vue 3, Vite, Element Plus, Axios, Vue Router |
| **数据库** | MySQL 8 (端口 3308) |
| **AI 模型** | 百炼 DashScope - qwen3.6-plus (LLM), text-embedding-v4 (Embedding, 2048维), fun-asr (ASR) |

## 项目结构

```
├── server/                    # 后端 Python FastAPI
│   ├── main.py               # 应用主入口
│   ├── config.py             # 配置文件
│   ├── database.py           # 数据库连接
│   ├── requirements.txt      # Python 依赖
│   ├── models/               # SQLAlchemy ORM 模型
│   │   ├── user.py           # 用户模型
│   │   ├── meeting.py        # 会议模型
│   │   ├── transcript.py     # 转写记录模型
│   │   ├── summary.py        # 摘要 + 待办事项模型
│   │   └── speaker_summary.py # 发言人总结模型
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── routers/              # API 路由
│   │   ├── auth.py           # 认证（注册/登录）
│   │   ├── meetings.py       # 会议管理（上传/列表/删除）
│   │   └── summary.py        # 纪要管理（转写/摘要/导出）
│   ├── services/             # 核心业务服务
│   │   ├── asr_service.py    # Fun-ASR 语音转写
│   │   ├── llm_service.py    # LangChain LLM 服务
│   │   ├── embedding_service.py # 向量嵌入服务
│   │   └── export_service.py # MD/PDF 导出服务
│   └── utils/                # 工具函数
│       ├── security.py       # MD5加密 + JWT
│       └── file_handler.py   # 文件上传处理
├── client/                   # 前端 Vue 3 + Element Plus
│   └── src/
│       ├── views/            # 页面
│       │   ├── Login.vue     # 登录页
│       │   ├── Register.vue  # 注册页
│       │   ├── Dashboard.vue # 仪表盘
│       │   ├── MeetingUpload.vue # 上传会议
│       │   ├── MeetingList.vue   # 会议列表
│       │   └── MeetingDetail.vue # 会议详情/纪要展示
│       ├── components/       # 公共组件
│       │   └── AppLayout.vue # 主布局组件
│       ├── api/              # API 封装
│       └── router/           # 路由配置
└── sql/                      # 数据库脚本
    ├── init.sql              # 建表语句
    └── test_data.sql         # 测试数据
```

## 功能特性

1. **音频/视频上传** - 支持 mp3、wav、m4a、mp4 等常见格式，最大 6GB
2. **语音转写 (ASR)** - 调用百炼 Fun-ASR 模型，支持说话人分离
3. **会议摘要生成** - AI 自动生成全文摘要，提炼核心内容
4. **要点提炼** - 自动提取关键词和待办事项
5. **发言总结** - 按发言人分别总结发言内容
6. **纪要导出** - 支持导出为 Markdown / PDF 格式

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0 (端口 3308)

### 2. 数据库初始化

```bash
# 连接 MySQL，执行建表脚本
mysql -h localhost -P 3308 -u root -p < sql/init.sql

# (可选) 导入测试数据
mysql -h localhost -P 3308 -u root -p < sql/test_data.sql
```

### 3. 后端启动

```bash
cd server

# 创建虚拟环境 (推荐)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 修改 config.py 中的配置:
#   - DASHSCOPE_API_KEY: 百炼平台 API Key
#   - DASHSCOPE_WORKSPACE_ID: 百炼工作空间 ID
#   - DB_PASSWORD: 数据库密码

# 启动服务 (端口 8000)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档: http://localhost:8000/docs

### 4. 前端启动

```bash
cd client

# 安装依赖
npm install

# 启动开发服务器 (端口 5173)
npm run dev
```

前端地址: http://localhost:5173

### 5. 测试账号

| 用户名 | 密码 |
|--------|------|
| admin | 123456 |
| testuser | 123456 |

## 配置说明

在 `server/config.py` 中配置以下关键参数：

```python
# DashScope 百炼平台（必须修改）
DASHSCOPE_API_KEY = "your-api-key-here"        # 百炼 API Key
DASHSCOPE_WORKSPACE_ID = "your-workspace-id"   # 百炼工作空间 ID

# 数据库（按需修改）
DB_HOST = "localhost"
DB_PORT = 3308
DB_PASSWORD = "your-db-password"

# 文件上传（按需修改）
UPLOAD_DIR = "uploads/"   # 可改为 D:/uploads19/
```

## 处理流程

```
上传文件 → 校验/存储 → 状态: uploaded
    ↓
语音转写 → Fun-ASR(说话人分离) → 状态: transcribing → transcribed
    ↓
AI生成纪要 → LLM Chain 并行:
  ├─ 全文摘要
  ├─ 关键词提取
  ├─ 待办事项提取
  └─ 发言人总结
    ↓
状态: completed → 展示/导出
```

## API 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 当前用户信息 |
| POST | /api/meetings/upload | 上传会议文件 |
| GET | /api/meetings | 会议列表 |
| GET | /api/meetings/{id} | 会议详情 |
| DELETE | /api/meetings/{id} | 删除会议 |
| POST | /api/meetings/{id}/transcribe | 触发语音转写 |
| GET | /api/meetings/{id}/transcript | 获取转写结果 |
| POST | /api/meetings/{id}/summarize | 生成AI纪要 |
| GET | /api/meetings/{id}/summary | 获取完整纪要 |
| GET | /api/meetings/{id}/export | 导出纪要(MD/PDF) |

## DashScope API Key 获取方式

1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 登录阿里云账号
3. 左侧菜单 → **模型广场** → 开通所需模型（qwen3.6-plus, text-embedding-v4, fun-asr）
4. 右上角头像 → **API-KEY 管理** → 创建 API Key
5. 在 **业务空间** 页面获取 Workspace ID
6. 将这两个值填入 `server/config.py`

## License

MIT
