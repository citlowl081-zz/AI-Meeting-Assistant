-- ============================================================
-- 基于LangChain的智能会议纪要助手系统 - 数据库初始化脚本
-- MySQL 8.0+, 端口 3308
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS meeting_assistant
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE meeting_assistant;

-- ============================================================
-- 1. 用户表
-- ============================================================
DROP TABLE IF EXISTS speaker_summaries;
DROP TABLE IF EXISTS action_items;
DROP TABLE IF EXISTS summaries;
DROP TABLE IF EXISTS transcripts;
DROP TABLE IF EXISTS meetings;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    password VARCHAR(128) NOT NULL COMMENT 'MD5加密密码',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    avatar VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================================
-- 2. 会议表
-- ============================================================
CREATE TABLE meetings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '会议ID',
    user_id BIGINT NOT NULL COMMENT '上传用户ID',
    title VARCHAR(255) NOT NULL COMMENT '会议标题',
    original_filename VARCHAR(500) DEFAULT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) DEFAULT NULL COMMENT '服务器存储路径',
    file_type VARCHAR(20) DEFAULT NULL COMMENT '文件类型(mp3/wav/m4a/mp4)',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小(bytes)',
    duration INT DEFAULT 0 COMMENT '音频时长(秒)',
    status ENUM('uploaded','transcribing','transcribed','summarizing','completed','failed') DEFAULT 'uploaded' COMMENT '处理状态',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    oss_file_id VARCHAR(200) DEFAULT NULL COMMENT 'DashScope OSS文件ID',
    asr_task_id VARCHAR(200) DEFAULT NULL COMMENT 'DashScope ASR任务ID',
    speaker_mapping TEXT DEFAULT NULL COMMENT '说话人名称映射JSON',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_meetings_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议表';

-- ============================================================
-- 3. 转写记录表（说话人分离结果）
-- ============================================================
CREATE TABLE transcripts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '转写记录ID',
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    speaker VARCHAR(50) NOT NULL COMMENT '发言人标签(如speaker_1)',
    start_time FLOAT DEFAULT 0 COMMENT '开始时间(秒)',
    end_time FLOAT DEFAULT 0 COMMENT '结束时间(秒)',
    content TEXT NOT NULL COMMENT '发言内容',
    sequence INT DEFAULT 0 COMMENT '排序序号',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_meeting_id (meeting_id),
    INDEX idx_sequence (meeting_id, sequence),
    CONSTRAINT fk_transcripts_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='转写记录表';

-- ============================================================
-- 4. 摘要表
-- ============================================================
CREATE TABLE summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '摘要ID',
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    full_summary TEXT COMMENT '全文摘要',
    keywords VARCHAR(500) DEFAULT NULL COMMENT '关键词(逗号分隔)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_meeting_id (meeting_id),
    CONSTRAINT fk_summaries_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='摘要表';

-- ============================================================
-- 5. 待办事项表
-- ============================================================
CREATE TABLE action_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '待办事项ID',
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    content VARCHAR(500) NOT NULL COMMENT '待办事项内容',
    responsible_person VARCHAR(50) DEFAULT NULL COMMENT '负责人',
    deadline VARCHAR(50) DEFAULT NULL COMMENT '截止时间',
    status ENUM('pending','completed') DEFAULT 'pending' COMMENT '完成状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_meeting_id (meeting_id),
    CONSTRAINT fk_action_items_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='待办事项表';

-- ============================================================
-- 6. 发言人总结表
-- ============================================================
CREATE TABLE speaker_summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '发言人总结ID',
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    speaker VARCHAR(50) NOT NULL COMMENT '发言人',
    summary TEXT COMMENT '发言内容总结',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_meeting_id (meeting_id),
    CONSTRAINT fk_speaker_summaries_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='发言人总结表';
