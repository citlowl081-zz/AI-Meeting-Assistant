"""
核心功能单元测试
运行: cd server && python -m pytest tests/ -v
"""
import sys
import os
import json
import pytest

# 确保 server/ 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSecurity:
    """测试安全模块: MD5加密 + JWT"""

    def test_md5_hash_consistency(self):
        from utils.security import md5_hash
        assert md5_hash("123456") == "e10adc3949ba59abbe56e057f20f883e"
        assert md5_hash("hello") != md5_hash("world")

    def test_verify_password(self):
        from utils.security import md5_hash, verify_password
        hashed = md5_hash("mypassword")
        assert verify_password("mypassword", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_jwt_create_and_decode(self):
        from utils.security import create_access_token, decode_access_token
        data = {"user_id": 1, "username": "testuser"}
        token = create_access_token(data)
        assert token is not None

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"

    def test_jwt_invalid_token(self):
        from utils.security import decode_access_token
        assert decode_access_token("invalid.token.here") is None
        assert decode_access_token("") is None


class TestFileHandler:
    """测试文件处理模块"""

    def test_get_file_extension(self):
        from utils.file_handler import get_file_extension
        assert get_file_extension("test.mp3") == "mp3"
        assert get_file_extension("test.MP3") == "mp3"
        assert get_file_extension("noextension") == ""
        assert get_file_extension("archive.tar.gz") == "gz"

    def test_generate_unique_filename(self):
        from utils.file_handler import generate_unique_filename
        name = generate_unique_filename("会议录音.mp3")
        assert "_会议录音.mp3" in name
        # 两次生成的不应相同
        name2 = generate_unique_filename("会议录音.mp3")
        assert name != name2


class TestASRService:
    """测试语音转写服务中的纯函数"""

    def test_parse_sentences_speaker_normalization(self):
        from services.asr_service import _parse_sentences
        sentences = [
            {"speaker_id": 0, "begin_time": 1000, "end_time": 3000, "text": "你好"},
            {"speaker_id": 1, "begin_time": 4000, "end_time": 6000, "text": "你好啊"},
            {"speaker_id": 0, "begin_time": 7000, "end_time": 9000, "text": "再见"},
        ]
        result = _parse_sentences(sentences)
        assert len(result) == 3
        # 说话人映射为 speaker1, speaker2
        assert result[0]["speaker"] == "speaker1"
        assert result[1]["speaker"] == "speaker2"
        assert result[2]["speaker"] == "speaker1"
        # 毫秒转秒
        assert result[0]["start_time"] == 1.0
        assert result[0]["end_time"] == 3.0

    def test_parse_sentences_second_unit(self):
        from services.asr_service import _parse_sentences
        sentences = [
            {"speaker_id": 0, "begin_time": 1.5, "end_time": 3.5, "text": "测试"},
        ]
        result = _parse_sentences(sentences)
        # 秒单位不应被除以1000
        assert result[0]["start_time"] == 1.5

    def test_parse_sentences_missing_fields(self):
        from services.asr_service import _parse_sentences
        sentences = [{"text": "只有文本"}]
        result = _parse_sentences(sentences)
        assert len(result) == 1
        assert result[0]["speaker"] in ("speaker1", "speaker2")

    def test_parse_srt_basic(self):
        from services.asr_service import _parse_srt
        srt = """1
00:00:01,000 --> 00:00:05,000
[speaker_0] 大家好

2
00:00:06,000 --> 00:00:10,000
[speaker_1] 你好
"""
        result = _parse_srt(srt)
        assert len(result) == 2
        assert result[0]["start_time"] == 1.0
        assert result[1]["start_time"] == 6.0

    def test_parse_srt_no_speaker_label(self):
        from services.asr_service import _parse_srt
        srt = """1
00:00:01,000 --> 00:00:05,000
大家好，这是第一句

2
00:00:06,000 --> 00:00:10,000
这是第二句话
"""
        result = _parse_srt(srt)
        assert len(result) == 2


class TestLLMService:
    """测试 LLM 服务模块配置"""

    def test_get_llm_configuration(self):
        from services.llm_service import _get_llm
        from config import LLM_MODEL, DASHSCOPE_BASE_URL
        llm = _get_llm(temperature=0.5)
        assert llm.model_name == LLM_MODEL
        assert llm.temperature == 0.5
        assert DASHSCOPE_BASE_URL in str(llm.openai_api_base)


class TestExportService:
    """测试导出服务"""

    def test_markdown_template_rendering(self):
        from services.export_service import export_markdown
        import os
        ctx = {
            "title": "测试会议",
            "date": "2026-07-31",
            "duration": 120,
            "full_summary": "这是摘要",
            "keywords": "测试,会议",
            "action_items": [{"content": "任务1", "responsible_person": "张三", "deadline": "2026-08-01", "status": "pending"}],
            "speaker_summaries": [{"speaker": "speaker1", "summary": "发言总结"}],
            "transcripts": [{"speaker": "speaker1", "start_time": 0.0, "end_time": 5.0, "content": "你好"}],
        }
        path = export_markdown(ctx)
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "测试会议" in content
        assert "这是摘要" in content
        assert "任务1" in content
        os.remove(path)

    def test_transcript_markdown_export(self):
        from services.export_service import export_transcript_markdown
        import os
        ctx = {
            "title": "对话记录",
            "date": "2026-07-31",
            "duration": 60,
            "full_summary": "",
            "keywords": "",
            "action_items": [],
            "speaker_summaries": [],
            "transcripts": [
                {"speaker": "speaker1", "start_time": 0.0, "end_time": 3.0, "content": "第一句"},
                {"speaker": "speaker2", "start_time": 4.0, "end_time": 7.0, "content": "第二句"},
            ],
        }
        path = export_transcript_markdown(ctx)
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "对话记录" in content
        assert "第一句" in content
        assert "第二句" in content
        os.remove(path)


class TestSchemas:
    """测试 Pydantic 请求/响应模型"""

    def test_user_register_validation(self):
        from schemas.user import UserRegisterRequest
        # 正常数据
        req = UserRegisterRequest(username="test", password="123456", email="test@test.com")
        assert req.username == "test"

        # 密码太短
        with pytest.raises(Exception):
            UserRegisterRequest(username="test", password="12")

    def test_user_login_validation(self):
        from schemas.user import UserLoginRequest
        req = UserLoginRequest(username="admin", password="123456")
        assert req.username == "admin"

    def test_dashboard_stats_response(self):
        from schemas.meeting import DashboardStatsResponse
        stats = DashboardStatsResponse(
            total_meetings=10,
            uploaded_count=3,
            transcribing_count=1,
            transcribed_count=2,
            summarizing_count=1,
            completed_count=2,
            failed_count=1,
        )
        assert stats.total_meetings == 10
        assert stats.failed_count == 1

    def test_speaker_mapping_request(self):
        from schemas.meeting import SpeakerMappingRequest
        req = SpeakerMappingRequest(mapping={"speaker1": "张医生", "speaker2": "李家属"})
        assert req.mapping["speaker1"] == "张医生"


class TestConfig:
    """测试配置模块"""

    def test_required_env_vars(self):
        from config import DASHSCOPE_API_KEY, DASHSCOPE_WORKSPACE_ID
        assert DASHSCOPE_API_KEY != ""
        assert DASHSCOPE_WORKSPACE_ID != ""
        assert DASHSCOPE_API_KEY != "your-api-key-here"

    def test_database_url_encoding(self):
        from config import DATABASE_URL
        assert "meeting_assistant" in DATABASE_URL
        assert "charset=utf8mb4" in DATABASE_URL

    def test_base_url_construction(self):
        from config import DASHSCOPE_BASE_URL, DASHSCOPE_WORKSPACE_ID
        expected = f"https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        assert DASHSCOPE_BASE_URL == expected
