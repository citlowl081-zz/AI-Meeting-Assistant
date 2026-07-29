"""
LangChain LLM 服务模块
使用 DashScope 百炼平台 qwen3.6-plus 模型（OpenAI 兼容模式）
提供会议摘要生成、关键词提取、待办事项提取、发言人总结等功能
"""
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    LLM_MODEL,
)


def _get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """
    获取 LangChain ChatOpenAI 实例
    连接 DashScope 百炼平台 OpenAI 兼容端点

    配置说明:
    - base_url: 百炼平台的 OpenAI 兼容端点
    - api_key: 实际传给 openai 的是 DashScope API Key
    - qwen3.6-plus 支持 128k 上下文窗口

    @param temperature: 生成温度(0-1)，越低越确定，摘要任务使用低温度
    @return: ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=LLM_MODEL,  # "qwen3.6-plus"
        openai_api_key=DASHSCOPE_API_KEY,  # 传给 DashScope 的认证
        openai_api_base=DASHSCOPE_BASE_URL,  # 百炼 OpenAI 兼容端点
        temperature=temperature,
        max_tokens=4096,  # 单次生成最大 Token 数
    )


# ============================================================
# 会议全文摘要生成
# ============================================================
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的会议纪要助手。请根据以下会议转写内容，生成一份清晰、全面的会议全文摘要。

要求：
1. 概括会议的主要议题和讨论内容
2. 突出关键决策和结论
3. 用2-3段文字组织，语言简洁专业
4. 如果有数据指标，请包含在摘要中
5. 字数控制在300-500字"""),
    ("human", "以下是会议转写内容：\n\n{transcript_text}"),
])


def generate_summary(transcript_text: str) -> str:
    """
    基于完整转写文本生成会议全文摘要

    使用 LangChain 的 LLMChain 调用 qwen3.6-plus，
    如果文本过长（超过模型上下文窗口），会自动分段处理后合并

    @param transcript_text: 完整转写文本
    @return: AI生成的会议全文摘要
    """
    llm = _get_llm(temperature=0.1)  # 摘要任务使用低温度保证准确性

    # 如果文本不太长，直接生成摘要
    if len(transcript_text) <= 100000:  # 约 10万字符在 128k token 窗口内安全
        chain = LLMChain(llm=llm, prompt=SUMMARY_PROMPT)
        result = chain.run(transcript_text=transcript_text)
        return result.strip()

    # 文本过长时，使用 Map-Reduce 策略分块处理
    # 1. 将文本按块分割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=80000,  # 每块约 8万字符
        chunk_overlap=500,  # 块之间重叠500字符，避免上下文断裂
    )
    chunks = text_splitter.split_text(transcript_text)

    # 2. 对每块生成局部摘要
    partial_summaries = []
    chain = LLMChain(llm=llm, prompt=SUMMARY_PROMPT)
    for i, chunk in enumerate(chunks):
        partial = chain.run(transcript_text=chunk)
        partial_summaries.append(f"第{i+1}部分摘要：{partial.strip()}")

    # 3. 合并所有局部摘要，再次生成最终摘要
    MERGE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的会议纪要助手。以下是会议各部分的分段摘要，请将它们整合为一份完整、连贯的会议全文摘要。

要求：
1. 整合所有部分的核心内容
2. 消除重复信息
3. 语言简洁专业，字数300-500字"""),
        ("human", "分段摘要如下：\n\n{partial_summaries}"),
    ])
    merge_chain = LLMChain(llm=llm, prompt=MERGE_PROMPT)
    final_summary = merge_chain.run(
        partial_summaries="\n\n".join(partial_summaries)
    )
    return final_summary.strip()


# ============================================================
# 关键词提取
# ============================================================
KEYWORDS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的会议纪要助手。请从以下会议内容中提取5-10个最核心的关键词。

要求：
1. 关键词要能反映会议核心议题
2. 关键词之间用英文逗号分隔
3. 优先提取专业术语和项目名称
4. 只返回关键词列表，不要其他内容

示例格式：产品规划,用户留存,推荐算法,A/B测试,性能优化"""),
    ("human", "会议内容：\n\n{transcript_text}"),
])


def extract_keywords(transcript_text: str) -> str:
    """
    从会议转写文本中提取核心关键词
    @param transcript_text: 转写文本(取前5000字即可提取关键词)
    @return: 逗号分隔的关键词字符串
    """
    llm = _get_llm(temperature=0.0)  # 提取任务使用零温度
    # 只取前5000字即可提取关键词
    text_for_keywords = transcript_text[:5000]

    chain = LLMChain(llm=llm, prompt=KEYWORDS_PROMPT)
    result = chain.run(transcript_text=text_for_keywords)
    return result.strip()


# ============================================================
# 待办事项提取
# ============================================================
ACTION_ITEMS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的会议纪要助手。请从以下会议内容中提取所有待办事项（Action Items）。

要求：
1. 识别会议中明确提出的任务和行动项
2. 每个待办事项包含：任务内容、负责人、截止时间
3. 以 JSON 数组格式返回，每个元素包含 content、responsible_person、deadline 三个字段
4. 如果某个字段没有明确提及，填 null
5. 只返回 JSON 数组，不要其他内容

示例格式：
[{"content": "完成推荐算法优化方案", "responsible_person": "王工", "deadline": "2024-10-20"},
 {"content": "设计新用户引导原型", "responsible_person": null, "deadline": null}]"""),
    ("human", "会议内容：\n\n{transcript_text}"),
])


def extract_action_items(transcript_text: str) -> List[Dict]:
    """
    从转写文本中提取待办事项
    使用 JSON 结构化输出，包含内容和负责人

    @param transcript_text: 转写文本
    @return: 待办事项列表，每项包含 content, responsible_person, deadline
    """
    import json

    llm = _get_llm(temperature=0.0)
    # 取前 8000 字提取待办事项
    text_for_extraction = transcript_text[:8000]

    chain = LLMChain(llm=llm, prompt=ACTION_ITEMS_PROMPT)
    result = chain.run(transcript_text=text_for_extraction)

    # 解析 LLM 返回的 JSON
    try:
        # 处理可能包含 markdown 代码块的情况
        clean_result = result.strip()
        if clean_result.startswith("```"):
            # 去掉 markdown 代码块标记
            clean_result = clean_result.split("\n", 1)[1]
            if clean_result.endswith("```"):
                clean_result = clean_result[:-3]
        action_items = json.loads(clean_result.strip())
        if isinstance(action_items, list):
            return action_items
    except json.JSONDecodeError:
        pass

    # JSON 解析失败时返回空列表
    return []


# ============================================================
# 发言人总结
# ============================================================
SPEAKER_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的会议纪要助手。请根据以下发言人在会议中的全部发言内容，总结该发言人的核心观点和贡献。

要求：
1. 用1-2句话概括该发言人的主要观点
2. 突出其提出的建议、方案或决策
3. 语言简洁专业，控制在80-150字"""),
    ("human", "发言人：{speaker}\n\n发言内容：\n{content}"),
])


def summarize_by_speaker(speaker: str, content: str) -> str:
    """
    按发言人总结其发言内容
    @param speaker: 发言人标签（如 speaker_1）
    @param content: 该发言人的全部发言内容（拼接后）
    @return: AI生成的发言人总结
    """
    llm = _get_llm(temperature=0.2)

    # 如果内容过长，截取前 3000 字
    content_for_summary = content[:3000]

    chain = LLMChain(llm=llm, prompt=SPEAKER_SUMMARY_PROMPT)
    result = chain.run(speaker=speaker, content=content_for_summary)
    return result.strip()
