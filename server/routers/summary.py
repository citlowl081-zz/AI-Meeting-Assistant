"""
纪要管理路由模块
处理语音转写(ASR)、AI摘要生成、纪要导出等核心功能
"""
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, SessionLocal
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
from services.asr_service import submit_asr_task, poll_asr_result, get_oss_url, upload_to_oss
from services.llm_service import generate_summary, extract_keywords, extract_action_items, summarize_by_speaker
from services.export_service import export_markdown, export_pdf, export_transcript_markdown, export_transcript_pdf

router = APIRouter()


# ============================================================
# 语音转写 (ASR)
# ============================================================

@router.post("/{meeting_id}/transcribe", summary="触发语音转写（异步后台处理）")
async def transcribe_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    提交语音转写任务，立即返回（后台异步处理）

    流程:
    1. 获取预上传的 OSS URL（或即时上传）
    2. 提交 DashScope ASR 任务 → 获取 task_id
    3. 立即返回 "任务已提交"
    4. 后台线程轮询任务状态 → 完成时自动保存结果

    前端只需轮询 GET /meetings/{id} 检查 status 变化:
    transcribing → transcribed (成功) / failed (失败)
    """
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

    # 1. 获取 OSS URL（优先用预上传的，否则即时上传）
    oss_url = ""
    if meeting.oss_file_id:
        try:
            oss_url = get_oss_url(meeting.oss_file_id)
        except Exception:
            pass  # OSS URL过期则重新上传

    if not oss_url:
        meeting.status = "transcribing"
        db.commit()
        meeting_id_val = meeting.id
        file_path_val = meeting.file_path
        # 上传到OSS并在后台线程中继续
        threading.Thread(
            target=_background_transcribe,
            args=(meeting_id_val, file_path_val, None),
            daemon=True,
        ).start()
        return {"message": "转写任务已提交，正在后台上传文件并处理...", "status": "transcribing"}

    # 2. 提交ASR任务
    try:
        task_id = submit_asr_task(oss_url)
    except Exception as e:
        meeting.status = "failed"
        meeting.error_message = f"提交ASR任务失败: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    # 3. 存储task_id，启动后台轮询
    meeting.status = "transcribing"
    meeting.asr_task_id = task_id
    meeting.error_message = None
    db.commit()

    # 4. 后台线程轮询结果
    threading.Thread(
        target=_background_transcribe,
        args=(meeting_id, "", task_id),
        daemon=True,
    ).start()

    return {
        "message": "转写任务已提交，后台正在处理...",
        "status": "transcribing",
        "task_id": task_id,
    }


def _background_transcribe(meeting_id: int, file_path: str, task_id: Optional[str]):
    """
    后台转写工作线程
    - 如果有 file_path 无 task_id: 先上传OSS再提交任务
    - 如果有 task_id: 直接轮询等待结果
    """
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return

        # 如果需要先上传
        if not task_id and file_path:
            try:
                oss_id = upload_to_oss(file_path)
                meeting.oss_file_id = oss_id
                db.commit()
                oss_url = get_oss_url(oss_id)
                task_id = submit_asr_task(oss_url)
                meeting.asr_task_id = task_id
                db.commit()
            except Exception as e:
                meeting.status = "failed"
                meeting.error_message = f"OSS上传或任务提交失败: {e}"
                db.commit()
                return

        # 轮询等待ASR结果
        print(f"[BG-ASR] 后台轮询 task_id={task_id}")
        segments = poll_asr_result(task_id)

        if not segments:
            meeting.status = "failed"
            meeting.error_message = "转写结果为空，音频可能无法识别"
            db.commit()
            return

        # 保存转写结果
        db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
        for i, seg in enumerate(segments):
            transcript = Transcript(
                meeting_id=meeting_id,
                speaker=seg.get("speaker", f"speaker{i+1}"),
                start_time=seg.get("start_time", 0),
                end_time=seg.get("end_time", 0),
                content=seg.get("content", ""),
                sequence=i + 1,
            )
            db.add(transcript)

        meeting.status = "transcribed"
        meeting.error_message = None
        db.commit()
        print(f"[BG-ASR] 转写完成 meeting={meeting_id}, segments={len(segments)}")

    except Exception as e:
        print(f"[BG-ASR] 转写失败 meeting={meeting_id}: {e}")
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                meeting.status = "failed"
                meeting.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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
        # 所有 LLM 调用互相独立，使用线程池并行执行，大幅缩短总耗时
        import concurrent.futures

        # 摘要使用完整文本，关键词和待办只需前8000字即可
        text_short = full_text[:8000]

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # 提交所有独立任务
            future_summary = executor.submit(generate_summary, full_text)
            future_keywords = executor.submit(extract_keywords, text_short)
            future_actions = executor.submit(extract_action_items, text_short)

            # 每个发言人的总结也并行提交
            future_speakers = {}
            for speaker, texts in speaker_texts.items():
                speaker_text = " ".join(texts)
                future_speakers[speaker] = executor.submit(
                    summarize_by_speaker, speaker, speaker_text
                )

            # 等待所有结果返回
            full_summary = future_summary.result()
            keywords = future_keywords.result()
            action_items_data = future_actions.result()

            # 收集发言人总结结果
            speaker_summaries_data = {}
            for speaker, future in future_speakers.items():
                speaker_summaries_data[speaker] = future.result()

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
    export_type: str = Query("full", description="导出类型: full=完整纪要, transcript=纯对话"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出会议纪要为 Markdown 或 PDF 格式
    - export_type=full: 完整纪要（摘要+待办+对话+发言人总结）
    - export_type=transcript: 纯发言对话（仅发言人对话内容）
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

    # 根据导出类型和格式导出
    if export_type == "transcript":
        # 纯对话导出
        if format == "pdf":
            file_path = export_transcript_pdf(context)
            media_type = "application/pdf"
            filename = f"{meeting.title}_对话记录.pdf"
        else:
            file_path = export_transcript_markdown(context)
            media_type = "text/markdown; charset=utf-8"
            filename = f"{meeting.title}_对话记录.md"
    else:
        # 完整纪要导出
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
