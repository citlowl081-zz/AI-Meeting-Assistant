"""
语音转写 (ASR) 服务模块
使用 DashScope (百炼) 平台的 Fun-ASR 模型进行语音识别
支持说话人分离（Speaker Diarization）
"""
import json
from typing import List, Dict
from http import HTTPStatus
import dashscope
from config import DASHSCOPE_API_KEY, ASR_MODEL


def transcribe_audio(file_path: str) -> List[Dict]:
    """
    调用百炼 Fun-ASR 模型进行语音转写（含说话人分离）

    DashScope Fun-ASR API 调用方式：
    1. 使用 dashscope.audio.asr.Transcription 异步调用
    2. 传入本地音频文件路径
    3. 启用 speaker_diarization 参数实现说话人分离

    @param file_path: 音频/视频文件的本地路径
    @return: 转写片段列表，每个片段包含 speaker, start_time, end_time, content
    @raises Exception: API 调用失败或模型返回错误
    """
    # 设置 API Key
    dashscope.api_key = DASHSCOPE_API_KEY

    try:
        # ============================================================
        # 调用 Fun-ASR 异步转写 API
        # Fun-ASR 通过 Transcription.async_call 提交任务，
        # 然后通过 Transcription.wait 轮询等待结果
        # ============================================================
        task_response = dashscope.audio.asr.Transcription.async_call(
            model=ASR_MODEL,  # "fun-asr"
            file_urls=[f"file://{file_path}"],  # 本地文件使用 file:// 协议
            parameters={
                "speaker_diarization": {
                    "speaker_count": None,  # None 表示自动检测说话人数量
                },
                "format": _get_file_format(file_path),  # 音频格式
            },
        )

        # 检查任务提交是否成功
        if task_response.status_code != HTTPStatus.OK:
            raise Exception(
                f"ASR 任务提交失败: {task_response.code} - {task_response.message}"
            )

        # 获取任务 ID，轮询等待转写完成
        task_id = task_response.output["task_id"]
        result_response = dashscope.audio.asr.Transcription.wait(task=task_id)

        # 检查转写结果
        if result_response.status_code != HTTPStatus.OK:
            raise Exception(
                f"ASR 转写失败: {result_response.code} - {result_response.message}"
            )

        # ============================================================
        # 解析转写结果
        # Fun-ASR 返回的结果中包含：
        # - sentences: 带有时间戳的句子列表
        # - speaker_id: 每个句子的说话人标识（启用说话人分离后）
        # ============================================================
        output = result_response.output
        if "results" not in output:
            raise Exception("ASR 返回结果格式异常，缺少 results 字段")

        # 获取第一个（通常只有一个）转录结果
        results = output["results"]
        if not results:
            return []  # 没有识别到任何语音内容

        transcription_result = results[0]

        # 提取转写片段，包含说话人分离信息
        segments = []
        if "sentences" in transcription_result:
            for sentence in transcription_result["sentences"]:
                segment = {
                    "speaker": sentence.get("speaker_id", "unknown_speaker"),
                    "start_time": sentence.get("begin_time", 0) / 1000.0,  # 毫秒转秒
                    "end_time": sentence.get("end_time", 0) / 1000.0,
                    "content": sentence.get("text", "").strip(),
                }
                segments.append(segment)

        # 如果没有 sentences 字段，尝试从整体文本中提取
        if not segments and "transcription_urls" in transcription_result:
            # 部分情况下需要从 URL 下载完整结果
            segments = _parse_transcription_from_url(
                transcription_result["transcription_urls"]
            )

        return segments

    except Exception as e:
        raise Exception(f"语音转写服务异常: {str(e)}")


def _get_file_format(file_path: str) -> str:
    """
    根据文件扩展名确定音频格式参数
    @param file_path: 文件路径
    @return: 格式标识符（如 'mp3', 'wav', 'm4a', 'mp4'）
    """
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "mp3"
    # Fun-ASR 支持的主流音频格式
    format_map = {
        "mp3": "mp3",
        "wav": "wav",
        "m4a": "m4a",
        "mp4": "mp4",
        "aac": "aac",
        "flac": "flac",
        "ogg": "ogg",
        "wma": "wma",
    }
    return format_map.get(ext, "mp3")


def _parse_transcription_from_url(urls: List[str]) -> List[Dict]:
    """
    从转写结果 URL 下载并解析完整的转写文本
    当 Fun-ASR 返回的是下载链接而非内嵌结果时使用
    @param urls: 转写结果文件的 URL 列表
    @return: 转写片段列表
    """
    import requests

    segments = []
    for url in urls:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # 解析结果：格式与 sentences 类似
            if "sentences" in data:
                for sentence in data["sentences"]:
                    segment = {
                        "speaker": sentence.get("speaker_id", "unknown_speaker"),
                        "start_time": sentence.get("begin_time", 0) / 1000.0,
                        "end_time": sentence.get("end_time", 0) / 1000.0,
                        "content": sentence.get("text", "").strip(),
                    }
                    segments.append(segment)
        except Exception:
            continue

    return segments
