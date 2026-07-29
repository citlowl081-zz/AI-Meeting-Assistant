"""
文件处理模块：负责上传文件的保存、验证和管理
"""
import os
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException
from config import UPLOAD_DIR, ALLOWED_AUDIO_EXTENSIONS, MAX_UPLOAD_SIZE


def get_file_extension(filename: str) -> str:
    """
    从文件名中提取扩展名（小写，不含点号）
    @param filename: 原始文件名
    @return: 小写扩展名，如 'mp3'
    """
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def validate_audio_file(filename: str, file_size: int) -> None:
    """
    验证上传的音频/视频文件格式和大小
    @param filename: 文件名
    @param file_size: 文件大小（字节）
    @raises HTTPException: 文件格式不支持或文件过大
    """
    ext = get_file_extension(filename)
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 .{ext}，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
        )
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制，最大支持 6GB",
        )


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一的存储文件名：UUID + 原始扩展名
    避免文件名冲突
    @param original_filename: 原始文件名
    @return: 唯一文件名，如 'a1b2c3d4_会议录音.mp3'
    """
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    return f"{unique_id}_{original_filename}"


async def save_upload_file(file: UploadFile) -> Tuple[str, str, int]:
    """
    保存上传文件到磁盘，返回存储信息
    使用流式写入支持大文件（最大6GB）
    @param file: FastAPI UploadFile 对象
    @return: (存储文件名, 存储路径, 文件大小)
    """
    # 生成唯一的存储文件名
    stored_filename = generate_unique_filename(file.filename)
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_path = os.path.join(UPLOAD_DIR, stored_filename)

    # 流式写入文件，支持大文件分块处理
    total_size = 0
    chunk_size = 1024 * 1024 * 8  # 8MB 每块，兼顾内存和速度
    with open(stored_path, "wb") as buffer:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            buffer.write(chunk)

    return stored_filename, stored_path, total_size


def delete_upload_file(file_path: str) -> bool:
    """
    删除服务器上的上传文件
    @param file_path: 文件的完整路径
    @return: 删除成功返回 True，文件不存在返回 False
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
