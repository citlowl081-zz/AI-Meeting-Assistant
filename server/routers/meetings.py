"""
会议管理路由模块
处理文件上传、会议列表、会议详情、删除
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import threading

from database import get_db, SessionLocal
from models.user import User
from models.meeting import Meeting
from routers.auth import get_current_user
from schemas.meeting import (
    MeetingResponse,
    MeetingListResponse,
    DashboardStatsResponse,
    SpeakerMappingRequest,
)
from utils.file_handler import validate_audio_file, save_upload_file, get_file_extension
import json

router = APIRouter()


@router.post("/upload", response_model=MeetingResponse, summary="上传会议音频/视频文件")
async def upload_meeting(
    title: str = Form(..., description="会议标题"),
    file: UploadFile = File(..., description="音频/视频文件(最大6GB)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传会议录音文件
    - 支持 mp3, wav, m4a, mp4 等格式
    - 文件大小最大 6GB，使用流式写入
    - 上传成功后自动创建会议记录，状态为 uploaded
    """
    # 1. 校验文件格式和大小
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 获取文件大小：先读取文件内容来确定大小
    # 由于需要流式处理大文件，我们先用 save_upload_file 保存再获取大小
    # FastAPI UploadFile 的 size 属性依赖于读取整个文件，大文件时不可靠
    validate_audio_file(file.filename, 0)  # 先校验格式，大小在校验通过后检查

    # 2. 保存文件到服务器，同时获取文件大小
    stored_filename, stored_path, file_size = await save_upload_file(file)

    # 3. 检查文件大小是否超过限制
    from config import MAX_UPLOAD_SIZE
    if file_size > MAX_UPLOAD_SIZE:
        # 删除已保存的超大文件
        from utils.file_handler import delete_upload_file
        delete_upload_file(stored_path)
        raise HTTPException(status_code=400, detail="文件大小超过6GB限制")

    # 4. 创建会议数据库记录
    file_type = get_file_extension(file.filename)
    meeting = Meeting(
        user_id=current_user.id,
        title=title,
        original_filename=file.filename,
        file_path=stored_path,
        file_type=file_type,
        file_size=file_size,
        status="uploaded",  # 初始状态：已上传
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    meeting_id = meeting.id

    # 5. 后台线程预上传文件到 OSS（不阻塞响应）
    def _background_oss_upload(meeting_id: int, file_path: str):
        """后台将文件上传到百炼OSS，转写时直接复用避免重复上传"""
        db_bg = SessionLocal()
        try:
            from services.asr_service import upload_to_oss
            oss_file_id = upload_to_oss(file_path)
            meeting_bg = db_bg.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting_bg:
                meeting_bg.oss_file_id = oss_file_id
                db_bg.commit()
                print(f"[OSS] 后台预上传完成 meeting={meeting_id} oss_id={oss_file_id}")
        except Exception as e:
            print(f"[OSS] 后台预上传失败 meeting={meeting_id}: {e}")
        finally:
            db_bg.close()

    threading.Thread(
        target=_background_oss_upload,
        args=(meeting_id, stored_path),
        daemon=True,
    ).start()

    return MeetingResponse.model_validate(meeting)


@router.get("", response_model=MeetingListResponse, summary="获取会议列表")
async def list_meetings(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的会议列表（分页）
    @param page: 页码，默认第1页
    @param page_size: 每页记录数，默认10条
    @param status: 按状态筛选（可选）
    """
    # 构建查询条件
    query = db.query(Meeting).filter(Meeting.user_id == current_user.id)
    if status:
        query = query.filter(Meeting.status == status)

    # 获取总记录数
    total = query.count()

    # 分页查询，按创建时间倒序
    meetings = (
        query.order_by(desc(Meeting.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return MeetingListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[MeetingResponse.model_validate(m) for m in meetings],
    )


@router.get("/{meeting_id}", response_model=MeetingResponse, summary="获取会议详情")
async def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定会议的详细信息
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}", summary="删除会议")
async def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除会议及其所有关联数据（转写、摘要、待办等）
    同时删除服务器上的上传文件
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    # 删除上传的文件
    if meeting.file_path:
        from utils.file_handler import delete_upload_file
        delete_upload_file(meeting.file_path)

    # 删除数据库记录（CASCADE 会自动删除关联的子表记录）
    db.delete(meeting)
    db.commit()

    return {"message": "会议已删除", "meeting_id": meeting_id}


@router.get("/stats/dashboard", response_model=DashboardStatsResponse, summary="获取仪表盘统计")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的会议统计数据
    包含：总数、已上传、转写中、已转写、摘要生成中、已完成、失败
    """
    base_query = db.query(Meeting).filter(Meeting.user_id == current_user.id)

    total = base_query.count()
    uploaded = base_query.filter(Meeting.status == "uploaded").count()
    transcribing = base_query.filter(Meeting.status == "transcribing").count()
    transcribed = base_query.filter(Meeting.status == "transcribed").count()
    summarizing = base_query.filter(Meeting.status == "summarizing").count()
    completed = base_query.filter(Meeting.status == "completed").count()
    failed = base_query.filter(Meeting.status == "failed").count()

    return DashboardStatsResponse(
        total_meetings=total,
        uploaded_count=uploaded,
        transcribing_count=transcribing,
        transcribed_count=transcribed,
        summarizing_count=summarizing,
        completed_count=completed,
        failed_count=failed,
    )


@router.put("/{meeting_id}/speakers", summary="更新说话人名称映射")
async def update_speaker_mapping(
    meeting_id: int,
    request: SpeakerMappingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    设置说话人的显示名称映射
    如 {"speaker1": "张医生", "speaker2": "李家属"}
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    meeting.speaker_mapping = json.dumps(request.mapping, ensure_ascii=False)
    db.commit()

    return {"message": "说话人名称已更新", "mapping": request.mapping}


@router.get("/{meeting_id}/speakers", summary="获取说话人名称映射")
async def get_speaker_mapping(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取说话人名称映射
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if meeting.speaker_mapping:
        return {"mapping": json.loads(meeting.speaker_mapping)}
    return {"mapping": {}}
