"""
向量嵌入服务模块
使用 DashScope 百炼平台 text-embedding-v4 模型
生成 2048 维文本嵌入向量，用于语义搜索和相似度计算
"""
from typing import List
from langchain_openai import OpenAIEmbeddings
from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)


def get_embeddings() -> OpenAIEmbeddings:
    """
    获取 LangChain OpenAIEmbeddings 实例
    连接到 DashScope 百炼平台的嵌入服务

    配置说明:
    - model: text-embedding-v4，向量维度 2048
    - base_url: 与 LLM 共用同一个 OpenAI 兼容端点
    - 嵌入模型支持中文和英文文本

    @return: OpenAIEmbeddings 实例
    """
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,  # "text-embedding-v4"
        openai_api_key=DASHSCOPE_API_KEY,
        openai_api_base=DASHSCOPE_BASE_URL,
        dimensions=EMBEDDING_DIMENSION,  # 2048 维
    )


def embed_text(text: str) -> List[float]:
    """
    将单段文本转换为嵌入向量
    @param text: 输入文本
    @return: 2048 维浮点数向量
    """
    embeddings = get_embeddings()
    vector = embeddings.embed_query(text)
    return vector


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    将多段文本批量转换为嵌入向量
    用于会议室语义搜索场景

    @param texts: 文本列表
    @return: 向量列表，每个向量 2048 维
    """
    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(texts)
    return vectors


def compute_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个嵌入向量之间的余弦相似度

    余弦相似度公式：
    cos(θ) = (A·B) / (||A|| × ||B||)

    @param vec1: 第一个向量
    @param vec2: 第二个向量
    @return: 余弦相似度 [-1, 1]，越接近1表示语义越相似
    """
    import math

    # 计算点积 A·B
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # 计算向量范数 ||A|| 和 ||B||
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)
