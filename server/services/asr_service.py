"""
语音转写 (ASR) 服务模块
使用 DashScope (百炼) 平台的 Fun-ASR 模型进行语音识别
支持说话人分离（Speaker Diarization）
"""
import json
import os
import subprocess
import requests
from typing import List, Dict
from http import HTTPStatus
import dashscope
from config import DASHSCOPE_API_KEY, ASR_MODEL

# Fun-ASR 原生支持的格式（不需要转换）
NATIVE_ASR_FORMATS = {"wav", "mp3", "pcm"}


def transcribe_audio(file_path: str) -> List[Dict]:
    """
    调用百炼 Fun-ASR 模型进行语音转写（含说话人分离）

    Fun-ASR API 流程:
    1. 使用 Transcription.async_call 提交异步任务
    2. Transcription.wait 轮询等待任务完成
    3. 从返回的 transcription_url 下载转写结果文件
    4. 解析 JSON 格式的转写结果，提取说话人和时间戳

    @param file_path: 音频/视频文件的本地路径（绝对路径或相对路径）
    @return: 转写片段列表，每个片段包含 speaker, start_time, end_time, content
    @raises Exception: API 调用失败或模型返回错误
    """
    dashscope.api_key = DASHSCOPE_API_KEY

    # 将文件路径转为绝对路径，确保 DashScope SDK 能正确读取
    abs_file_path = os.path.abspath(file_path)
    actual_file_path = abs_file_path

    # ============================================================
    # 自动转换音频格式
    # .m4a, .mp4, .aac, .flac 等格式 Fun-ASR 可能解码失败，
    # 使用 ffmpeg 自动转换为 WAV 格式再提交
    # ============================================================
    file_ext = os.path.splitext(abs_file_path)[1].lower().lstrip(".")
    if file_ext not in NATIVE_ASR_FORMATS:
        print(f"[ASR] 格式 {file_ext} 非原生支持，正在用ffmpeg转换为WAV...")
        converted_path = _convert_to_wav(abs_file_path)
        if converted_path:
            actual_file_path = converted_path
            print(f"[ASR] 已转换为WAV: {actual_file_path}")
        else:
            print(f"[ASR] ffmpeg转换失败，尝试直接使用原文件")

    file_url = f"file://{actual_file_path}"

    print(f"[ASR] 开始转写: {actual_file_path}")
    print(f"[ASR] 使用模型: {ASR_MODEL}")

    try:
        # ============================================================
        # 步骤0: 上传文件到百炼 OSS
        # Fun-ASR 是云端服务，无法直接读取本地 file:// 路径，
        # 需要先将文件上传到阿里云 OSS，再用 OSS URL 调用转写
        # ============================================================
        print(f"[ASR] 正在上传文件到百炼OSS...")
        file_size_mb = os.path.getsize(actual_file_path) / 1024 / 1024
        print(f"[ASR] 文件大小: {file_size_mb:.1f}MB")

        # 使用 DashScope Files API 将文件上传到 OSS
        # 流程: upload(file_path) → file_id → get(file_id) → OSS presigned URL
        from dashscope.files import Files
        files_api = Files()

        # 步骤0a: 上传文件
        upload_resp = files_api.upload(
            file_path=actual_file_path,
            purpose="asr_transcription",
        )
        print(f"[ASR] 上传响应: status_code={upload_resp.status_code}")

        oss_url = file_url  # 默认用本地路径兜底
        if upload_resp.status_code == HTTPStatus.OK:
            uploaded_files = upload_resp.output.get("uploaded_files", [])
            if uploaded_files:
                # 步骤0b: 通过 file_id 获取 OSS URL
                file_id = uploaded_files[0].get("file_id", "")
                print(f"[ASR] file_id: {file_id}")
                get_resp = files_api.get(file_id=file_id)
                if get_resp.status_code == HTTPStatus.OK:
                    oss_url = get_resp.output.get("url", "")
                    print(f"[ASR] OSS URL获取成功")
                else:
                    print(f"[ASR] get OSS URL失败: {get_resp.message}")
            else:
                print(f"[ASR] 上传成功但无uploaded_files")
        else:
            print(f"[ASR] 上传失败: {upload_resp.message}, 用本地file://兜底")

        print(f"[ASR] 文件URL: {oss_url[:80]}...")

        # ============================================================
        # 步骤1: 提交异步转写任务
        # 使用 OSS URL 而非 file:// 路径
        # ============================================================
        task_response = dashscope.audio.asr.Transcription.async_call(
            model=ASR_MODEL,
            file_urls=[oss_url],
            # Fun-ASR 的说话人分离参数直接作为顶层参数传递
            diarization_enabled=True,
        )

        print(f"[ASR] 任务提交响应: status_code={task_response.status_code}")

        # 检查任务提交是否成功
        if task_response.status_code != HTTPStatus.OK:
            error_msg = f"ASR 任务提交失败: code={task_response.code}, message={task_response.message}"
            print(f"[ASR] ERROR: {error_msg}")
            raise Exception(error_msg)

        # ============================================================
        # 步骤2: 轮询等待转写完成
        # ============================================================
        task_id = task_response.output.get("task_id", "")
        print(f"[ASR] 任务ID: {task_id}, 等待转写完成...")

        result_response = dashscope.audio.asr.Transcription.wait(task=task_id)

        print(f"[ASR] 转写结果状态: status_code={result_response.status_code}")

        # 检查转写是否成功
        if result_response.status_code != HTTPStatus.OK:
            error_msg = f"ASR 转写失败: code={result_response.code}, message={result_response.message}"
            print(f"[ASR] ERROR: {error_msg}")
            raise Exception(error_msg)

        # ============================================================
        # 步骤3: 检查转写子任务状态
        # Fun-ASR 可能 HTTP 200 但子任务失败（如音频解码失败）
        # ============================================================
        output = result_response.output
        print(f"[ASR] 输出结构: {json.dumps(output, ensure_ascii=False)[:500]}")

        # 检查子任务状态
        subtask_status = output.get("subtask_status", "")
        if subtask_status == "FAILED":
            # 从 results 中提取具体的错误码
            results_data = output.get("results", [])
            sub_error_code = ""
            if results_data:
                sub_error_code = results_data[0].get("subtask_status", "")
            # DECOD 错误说明音频编码不被 Fun-ASR 支持
            if "DECOD" in str(result_response.code) or "DECOD" in str(sub_error_code):
                file_ext = os.path.splitext(file_path)[1].lower()
                raise Exception(
                    f"音频解码失败：{file_ext} 格式的编码不被 Fun-ASR 支持。"
                    f"请将音频转换为 WAV 或 MP3 格式后重新上传。"
                    f"(错误码: {result_response.code})"
                )
            raise Exception(
                f"ASR 子任务执行失败。错误码: {result_response.code}，"
                f"详情: {json.dumps(output, ensure_ascii=False)[:300]}"
            )

        results = output.get("results", [])
        if not results:
            raise Exception("ASR 返回结果为空，未能识别到语音内容")

        transcription_result = results[0]

        # 方式1: 从 transcription_url 下载转写文件
        transcription_url = transcription_result.get("transcription_url", "")
        if transcription_url:
            print(f"[ASR] 下载转写结果: {transcription_url}")
            segments = _download_and_parse_transcription(transcription_url)
            if segments:
                print(f"[ASR] 成功解析 {len(segments)} 个转写片段")
                return segments

        # 方式2: 如果有 sentences 字段，直接解析
        sentences = transcription_result.get("sentences", [])
        if sentences:
            segments = _parse_sentences(sentences)
            print(f"[ASR] 从sentences解析到 {len(segments)} 个片段")
            if segments:
                return segments

        # 方式3: 尝试 transcription_urls (复数形式)
        urls = transcription_result.get("transcription_urls", [])
        if urls:
            all_segments = []
            for url in urls:
                segs = _download_and_parse_transcription(url)
                all_segments.extend(segs)
            if all_segments:
                print(f"[ASR] 从URLs解析到 {len(all_segments)} 个片段")
                return all_segments

        # 所有解析方式都失败了
        raise Exception(
            f"无法解析ASR转写结果。响应内容: {json.dumps(transcription_result, ensure_ascii=False)[:500]}"
        )

    except Exception as e:
        error_msg = f"语音转写服务异常: {str(e)}"
        print(f"[ASR] ERROR: {error_msg}")
        raise Exception(error_msg)


def _download_and_parse_transcription(url: str) -> List[Dict]:
    """
    从转写结果 URL 下载并解析完整的转写文本
    Fun-ASR 返回的 JSON/SRT 格式转写文件

    @param url: 转写结果文件的下载 URL
    @return: 转写片段列表
    """
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        raw_text = resp.text.strip()
        print(f"[ASR] 下载的转写内容长度: {len(raw_text)} 字符")

        # ============================================================
        # 尝试 JSON 格式解析
        # ============================================================
        if raw_text.startswith("{"):
            data = resp.json()
            # 可能的 JSON 格式1: {"sentences": [...]}
            if "sentences" in data:
                return _parse_sentences(data["sentences"])
            # 可能的 JSON 格式2: {"transcripts": [...]}
            if "transcripts" in data:
                return _parse_transcripts(data["transcripts"])
            # 可能的 JSON 格式3: {"results": {...}}
            if "results" in data:
                results = data["results"]
                if isinstance(results, dict):
                    if "sentences" in results:
                        return _parse_sentences(results["sentences"])
                    if "transcripts" in results:
                        return _parse_transcripts(results["transcripts"])
            # 尝试通用的键
            for key in ["sentences", "segments", "utterances", "transcripts"]:
                if key in data:
                    return _parse_sentences(data[key])

        # ============================================================
        # 尝试 SRT 字幕格式解析
        # SRT 格式:
        # 1
        # 00:00:01,000 --> 00:00:05,000
        # [speaker_1] 发言内容
        # ============================================================
        if raw_text[0].isdigit() or "--> " in raw_text:
            return _parse_srt(raw_text)

        # 无法识别的格式，记录并返回空
        print(f"[ASR] 无法识别的转写格式: {raw_text[:200]}")
        return []

    except requests.RequestException as e:
        print(f"[ASR] 下载转写文件失败: {e}")
        return []
    except json.JSONDecodeError:
        # JSON 解析失败，尝试作为纯文本处理
        print(f"[ASR] JSON解析失败，尝试SRT格式")
        return _parse_srt(raw_text)


def _parse_sentences(sentences: List[Dict]) -> List[Dict]:
    """
    解析 sentences 数组格式的转写结果
    每个 sentence 包含 speaker_id/begin_time/end_time/text
    """
    segments = []
    for i, sent in enumerate(sentences):
        # 兼容多种字段名：speaker_id / speaker / spk
        speaker = (
            sent.get("speaker_id")
            or sent.get("speaker")
            or sent.get("spk")
            or f"speaker_{i % 2 + 1}"
        )
        # 兼容多种时间单位：毫秒或秒
        begin = sent.get("begin_time", sent.get("start_time", sent.get("begin", 0)))
        end = sent.get("end_time", sent.get("end", 0))
        # 如果时间值大于 1000，说明是毫秒单位，转换为秒
        if isinstance(begin, (int, float)) and begin > 1000:
            begin = begin / 1000.0
        if isinstance(end, (int, float)) and end > 1000:
            end = end / 1000.0

        text = sent.get("text", sent.get("content", sent.get("sentence", "")))
        if text.strip():
            segments.append({
                "speaker": str(speaker),
                "start_time": float(begin),
                "end_time": float(end),
                "content": text.strip(),
            })
    return segments


def _parse_transcripts(transcripts: List[Dict]) -> List[Dict]:
    """解析 transcripts 数组格式（同 sentences 处理逻辑）"""
    return _parse_sentences(transcripts)


def _parse_srt(srt_text: str) -> List[Dict]:
    """
    解析 SRT 字幕格式的转写结果
    如果包含说话人标注 [speaker_X] 则进行分离
    """
    import re

    segments = []
    # 按空行分割每个字幕块
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    speaker_counter = 1
    last_speaker = None

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        # 跳过序号行，找到时间戳行
        time_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                time_line = line
            elif not line.strip().isdigit():
                text_lines.append(line)

        if not time_line:
            continue

        # 解析时间戳: 00:00:01,000 --> 00:00:05,000
        times = re.findall(r"(\d+):(\d+):(\d+)[.,](\d+)", time_line)
        if len(times) < 2:
            continue

        start_time = (
            int(times[0][0]) * 3600
            + int(times[0][1]) * 60
            + int(times[0][2])
            + int(times[0][3]) / 1000
        )
        end_time = (
            int(times[1][0]) * 3600
            + int(times[1][1]) * 60
            + int(times[1][2])
            + int(times[1][3]) / 1000
        )

        text = " ".join(text_lines).strip()
        if not text:
            continue

        # 尝试提取说话人标签 [speaker_X]
        speaker_match = re.match(r"\[([^\]]+)\]\s*", text)
        if speaker_match:
            speaker = speaker_match.group(1)
            text = text[speaker_match.end() :].strip()
            last_speaker = speaker
        elif last_speaker:
            # 同一说话人连续发言
            speaker = last_speaker
        else:
            speaker = f"speaker_{speaker_counter}"
            speaker_counter += 1

        segments.append({
            "speaker": speaker,
            "start_time": start_time,
            "end_time": end_time,
            "content": text,
        })

    return segments


def _convert_to_wav(file_path: str) -> str:
    """
    使用 ffmpeg 将音频文件转换为 16kHz 单声道 WAV 格式
    Fun-ASR 对 WAV 格式支持最好，m4a/mp4/aac 等格式需先转换

    ffmpeg 参数说明:
    - -i: 输入文件
    - -acodec pcm_s16le: 输出PCM 16-bit 编码
    - -ar 16000: 采样率16kHz (Fun-ASR推荐)
    - -ac 1: 单声道
    - -y: 覆盖已有输出文件

    @param file_path: 原始音频文件路径
    @return: 转换后的WAV路径，失败返回空字符串
    """
    base = os.path.splitext(file_path)[0]
    output_path = f"{base}_converted.wav"

    # 已转换过则直接复用
    if os.path.exists(output_path):
        print(f"[ASR] 复用已有转换文件: {output_path}")
        return output_path

    try:
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"[ASR] ffmpeg转换成功: {size_mb:.1f}MB")
            return output_path
        else:
            print(f"[ASR] ffmpeg转换失败: {result.stderr[:300]}")
            return ""
    except FileNotFoundError:
        print("[ASR] ffmpeg 未安装，无法转换音频")
        return ""
    except subprocess.TimeoutExpired:
        print("[ASR] ffmpeg 转换超时")
        return ""
    except Exception as e:
        print(f"[ASR] ffmpeg 异常: {e}")
        return ""
