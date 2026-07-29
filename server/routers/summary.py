"""
纪要管理路由模块
处理语音转写(ASR)、AI摘要生成、纪要导出等核心功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.user import User
from models.meeting import Meeting
from models.transcript import Transcript
from models.summary import Summary, ActionItem
from models.speaker_summary import SpeakerSummary
from routers.auth import get_current_user
from schemas.summary import (
    TranscriptResponse,
    TranscriptSegment,
    SummaryResponse,
    ActionItemResponse,
    SpeakerSummaryResponse,
    MeetingMinutesResponse,
)
from services.asr_service import transcribe_audio
from services.llm_service import generate_summary, extract_keywords, extract_action_items, summarize_by_speaker
from services.export_service import export_markdown, export_pdf

router = APIRouter()


# ============================================================
# 语音转写 (ASR)
# ============================================================

@router.post("/{meeting_id}/transcribe", summary="触发语音转写")
async def transcribe_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    对已上传的会议音频/视频进行语音转写（Fun-ASR + 说话人分离）
    转写完成后结果自动存入 transcripts 表
    """
    # 1. 获取会议信息，校验权限
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if meeting.status == "transcribing":
        raise HTTPException(status_code=400, detail="会议正在转写中，请稍候")

    if not meeting.file_path:
        raise HTTPException(status_code=400, detail="会议没有可转写的音频文件")

    # 2. 更新状态为转写中
    meeting.status = "transcribing"
    db.commit()

    try:
        # 3. 调用 Fun-ASR 进行语音转写（带说话人分离）
        segments = transcribe_audio(meeting.file_path)

        # 3b. 如果转写结果为空，说明音频无法识别或解析失败
        if not segments:
            raise Exception("转写结果为空，音频可能无法识别或格式不支持")

        # 4. 删除旧的转写记录（如果已存在）
        db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()

        # 5. 将转写结果批量插入数据库
        for i, seg in enumerate(segments):
            transcript = Transcript(
                meeting_id=meeting_id,
                speaker=seg.get("speaker", f"speaker_{i}"),
                start_time=seg.get("start_time", 0),
                end_time=seg.get("end_time", 0),
                content=seg.get("content", ""),
                sequence=i + 1,
            )
            db.add(transcript)

        # 6. 更新状态为已转写
        meeting.status = "transcribed"
        meeting.error_message = None
        db.commit()

        return {"message": "转写完成", "segments_count": len(segments)}

    except Exception as e:
        # 转写失败，记录错误信息
        meeting.status = "failed"
        meeting.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"语音转写失败: {str(e)}")


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse, summary="获取转写结果")
async def get_transcript(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定会议的语音转写结果
    返回按发言人分组的转写文本，按时间顺序排列
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    # 按 sequence 排序获取所有转写片段
    transcripts = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.sequence)
        .all()
    )

    # 收集所有说话人（去重、保持顺序）
    speakers = list(dict.fromkeys([t.speaker for t in transcripts]))

    # 拼接完整转写文本（带说话人标注）
    full_text_parts = []
    for t in transcripts:
        full_text_parts.append(f"[{t.speaker}] ({t.start_time:.1f}s-{t.end_time:.1f}s): {t.content}")
    full_text = "\n\n".join(full_text_parts)

    return TranscriptResponse(
        meeting_id=meeting_id,
        speakers=speakers,
        segments=[TranscriptSegment.model_validate(t) for t in transcripts],
        full_text=full_text,
    )


# ============================================================
# AI 摘要生成
# ============================================================

@router.post("/{meeting_id}/summarize", summary="生成AI会议纪要")
async def summarize_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    调用 LLM (qwen3.6-plus via LangChain) 生成完整的会议纪要：
    1. 全文摘要
    2. 关键词提取
    3. 待办事项提取
    4. 发言人总结
    """
    # 1. 校验会议和权限
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if meeting.status not in ("transcribed", "completed"):
        raise HTTPException(status_code=400, detail="请先完成语音转写再生成纪要")

    # 2. 获取转写结果
    transcripts = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.sequence)
        .all()
    )
    if not transcripts:
        raise HTTPException(status_code=400, detail="没有转写数据")

    # 3. 拼接完整转写文本
    full_text = "\n".join([
        f"[{t.speaker}] {t.content}" for t in transcripts
    ])

    # 4. 按发言人分组文本
    speaker_texts = {}
    for t in transcripts:
        speaker = t.speaker
        if speaker not in speaker_texts:
            speaker_texts[speaker] = []
        speaker_texts[speaker].append(t.content)

    # 5. 更新状态为摘要生成中
    meeting.status = "summarizing"
    db.commit()

    try:
        # === 并行调用 LLM 生成各类纪要 ===

        # 5a. 生成全文摘要
        full_summary = generate_summary(full_text)
        keywords = extract_keywords(full_text)

        # 5b. 提取待办事项
        action_items_data = extract_action_items(full_text)

        # 5c. 按发言人总结
        speaker_summaries_data = {}
        for speaker, texts in speaker_texts.items():
            speaker_text = " ".join(texts)
            speaker_summaries_data[speaker] = summarize_by_speaker(speaker, speaker_text)

        # === 将结果存入数据库 ===

        # 删除旧的摘要和待办（如果已存在）
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
        db.query(SpeakerSummary).filter(SpeakerSummary.meeting_id == meeting_id).delete()

        # 保存全文摘要
        existing_summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
        if existing_summary:
            existing_summary.full_summary = full_summary
            existing_summary.keywords = keywords
        else:
            summary_record = Summary(
                meeting_id=meeting_id,
                full_summary=full_summary,
                keywords=keywords,
            )
            db.add(summary_record)

        # 保存待办事项
        for item in action_items_data:
            action_item = ActionItem(
                meeting_id=meeting_id,
                content=item.get("content", ""),
                responsible_person=item.get("responsible_person"),
                deadline=item.get("deadline"),
            )
            db.add(action_item)

        # 保存发言人总结
        for speaker, summary_text in speaker_summaries_data.items():
            speaker_summary = SpeakerSummary(
                meeting_id=meeting_id,
                speaker=speaker,
                summary=summary_text,
            )
            db.add(speaker_summary)

        # 更新状态为已完成
        meeting.status = "completed"
        meeting.error_message = None
        db.commit()

        return {"message": "会议纪要生成完成"}

    except Exception as e:
        meeting.status = "failed"
        meeting.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"纪要生成失败: {str(e)}")


@router.get("/{meeting_id}/summary", response_model=MeetingMinutesResponse, summary="获取会议完整纪要")
async def get_summary(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会议的完整纪要信息
    聚合：基本信息 + 转写 + 摘要 + 待办 + 发言人总结
    """
    # 校验会议权限
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    # 获取转写结果
    transcripts = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.sequence)
        .all()
    )
    speakers = list(dict.fromkeys([t.speaker for t in transcripts]))
    full_text = "\n\n".join([
        f"[{t.speaker}] {t.content}" for t in transcripts
    ])
    transcript_response = TranscriptResponse(
        meeting_id=meeting_id,
        speakers=speakers,
        segments=[TranscriptSegment.model_validate(t) for t in transcripts],
        full_text=full_text,
    )

    # 获取摘要
    summary_record = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    summary_response = SummaryResponse.model_validate(summary_record) if summary_record else None

    # 获取待办事项
    action_items = (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting_id)
        .all()
    )

    # 获取发言人总结
    speaker_summaries = (
        db.query(SpeakerSummary)
        .filter(SpeakerSummary.meeting_id == meeting_id)
        .all()
    )

    return MeetingMinutesResponse(
        meeting_id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        transcript=transcript_response,
        summary=summary_response,
        action_items=[ActionItemResponse.model_validate(a) for a in action_items],
        speaker_summaries=[SpeakerSummaryResponse.model_validate(s) for s in speaker_summaries],
    )


# ============================================================
# 纪要导出
# ============================================================

@router.get("/{meeting_id}/export", summary="导出会议纪要")
async def export_minutes(
    meeting_id: int,
    format: str = Query("md", description="导出格式: md 或 pdf"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出会议纪要为 Markdown 或 PDF 格式
    """
    # 校验会议权限
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id,
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    # 收集完整的会议数据
    transcripts = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.sequence)
        .all()
    )
    summary_record = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    speaker_summaries = db.query(SpeakerSummary).filter(SpeakerSummary.meeting_id == meeting_id).all()

    # 构建上下文数据
    context = {
        "title": meeting.title,
        "date": meeting.created_at.strftime("%Y-%m-%d %H:%M") if meeting.created_at else "",
        "duration": meeting.duration or 0,
        "full_text": "\n\n".join([f"[{t.speaker}] {t.content}" for t in transcripts]) if transcripts else "",
        "full_summary": summary_record.full_summary if summary_record else "",
        "keywords": summary_record.keywords if summary_record else "",
        "action_items": [
            {"content": a.content, "responsible_person": a.responsible_person or "", "deadline": a.deadline or "", "status": a.status}
            for a in action_items
        ],
        "speaker_summaries": [
            {"speaker": s.speaker, "summary": s.summary or ""}
            for s in speaker_summaries
        ],
        "transcripts": [
            {"speaker": t.speaker, "start_time": t.start_time, "end_time": t.end_time, "content": t.content}
            for t in transcripts
        ],
    }

    # 根据格式导出
    if format == "pdf":
        file_path = export_pdf(context)
        media_type = "application/pdf"
        filename = f"{meeting.title}_会议纪要.pdf"
    else:
        file_path = export_markdown(context)
        media_type = "text/markdown; charset=utf-8"
        filename = f"{meeting.title}_会议纪要.md"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
