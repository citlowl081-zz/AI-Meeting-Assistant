"""
纪要导出服务模块
支持将会议纪要导出为 Markdown 和 PDF 格式
使用 Jinja2 模板渲染内容
"""
import os
import uuid
from typing import Dict
from jinja2 import Template

# 导出文件存储目录（临时文件，使用后清理）
EXPORT_DIR = "exports/"
os.makedirs(EXPORT_DIR, exist_ok=True)

# ============================================================
# Markdown 导出模板
# ============================================================
MARKDOWN_TEMPLATE = Template("""# {{ title }}

> **会议时间**: {{ date }}
> **会议时长**: {{ duration // 60 }}分{{ duration % 60 }}秒

---

## 📋 会议摘要

{{ full_summary }}

{% if keywords %}
**关键词**: {{ keywords }}
{% endif %}

---

## 🎯 待办事项

| 序号 | 任务内容 | 负责人 | 截止时间 | 状态 |
|------|---------|--------|---------|------|
{% for item in action_items %}
| {{ loop.index }} | {{ item.content }} | {{ item.responsible_person or '未指定' }} | {{ item.deadline or '未指定' }} | {{ '✅ 已完成' if item.status == 'completed' else '⏳ 进行中' }} |
{% endfor %}

{% if speaker_summaries %}
---

## 👤 发言人总结

{% for sp in speaker_summaries %}
### {{ sp.speaker }}

{{ sp.summary }}

{% endfor %}
{% endif %}

---

## 📝 完整转写文本

{% for seg in transcripts %}
**[{{ seg.speaker }}]** ({{ "%.1f"|format(seg.start_time) }}s - {{ "%.1f"|format(seg.end_time) }}s)

{{ seg.content }}

{% endfor %}

---

> 本纪要由 **基于LangChain的智能会议纪要助手系统** 自动生成
> 生成时间: {{ date }}
""")


def export_markdown(context: Dict) -> str:
    """
    将会议纪要数据渲染为 Markdown 格式文件

    @param context: 包含会议所有信息的字典
        - title: 会议标题
        - date: 会议时间
        - duration: 时长(秒)
        - full_summary: 全文摘要
        - keywords: 关键词
        - action_items: 待办事项列表
        - speaker_summaries: 发言人总结列表
        - transcripts: 转写片段列表
    @return: Markdown 文件的完整路径
    """
    # 使用 Jinja2 模板渲染 Markdown
    markdown_content = MARKDOWN_TEMPLATE.render(**context)

    # 写入文件
    filename = f"{uuid.uuid4().hex[:8]}_minutes.md"
    file_path = os.path.join(EXPORT_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return file_path


# ============================================================
# PDF 导出模板 (HTML 格式，通过 WeasyPrint 转换)
# ============================================================
HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        h1 {
            text-align: center;
            color: #1a1a2e;
            border-bottom: 2px solid #409EFF;
            padding-bottom: 16px;
            margin-bottom: 8px;
        }
        h2 {
            color: #303133;
            border-left: 4px solid #409EFF;
            padding-left: 12px;
            margin-top: 32px;
        }
        h3 { color: #606266; margin-top: 20px; }
        .meta {
            text-align: center;
            color: #909399;
            margin-bottom: 24px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }
        th, td {
            border: 1px solid #DCDFE6;
            padding: 10px 12px;
            text-align: left;
        }
        th {
            background: #F5F7FA;
            font-weight: 600;
        }
        .summary-box {
            background: #F0F9FF;
            border: 1px solid #BAE7FF;
            border-radius: 8px;
            padding: 20px;
            margin: 16px 0;
        }
        .keywords {
            color: #409EFF;
            font-size: 14px;
            margin-top: 12px;
        }
        .transcript-segment {
            margin: 12px 0;
            padding: 12px;
            background: #FAFAFA;
            border-radius: 6px;
        }
        .speaker-label {
            font-weight: 600;
            color: #409EFF;
        }
        .time-label {
            color: #909399;
            font-size: 12px;
        }
        .footer {
            text-align: center;
            color: #C0C4CC;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #EBEEF5;
        }
        @page {
            size: A4;
            margin: 2cm;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p class="meta">
        会议时间: {{ date }} | 时长: {{ duration // 60 }}分{{ duration % 60 }}秒
    </p>

    <h2>📋 会议摘要</h2>
    <div class="summary-box">
        <p>{{ full_summary | replace('\n', '<br>') }}</p>
        {% if keywords %}
        <p class="keywords"><strong>关键词:</strong> {{ keywords }}</p>
        {% endif %}
    </div>

    <h2>🎯 待办事项</h2>
    <table>
        <tr><th>序号</th><th>任务内容</th><th>负责人</th><th>截止时间</th><th>状态</th></tr>
        {% for item in action_items %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.content }}</td>
            <td>{{ item.responsible_person or '未指定' }}</td>
            <td>{{ item.deadline or '未指定' }}</td>
            <td>{{ '已完成' if item.status == 'completed' else '进行中' }}</td>
        </tr>
        {% endfor %}
    </table>

    {% if speaker_summaries %}
    <h2>👤 发言人总结</h2>
    {% for sp in speaker_summaries %}
    <h3>{{ sp.speaker }}</h3>
    <p>{{ sp.summary }}</p>
    {% endfor %}
    {% endif %}

    <h2>📝 完整转写文本</h2>
    {% for seg in transcripts %}
    <div class="transcript-segment">
        <span class="speaker-label">[{{ seg.speaker }}]</span>
        <span class="time-label">({{ "%.1f"|format(seg.start_time) }}s - {{ "%.1f"|format(seg.end_time) }}s)</span>
        <p>{{ seg.content }}</p>
    </div>
    {% endfor %}

    <div class="footer">
        <p>本纪要由 基于LangChain的智能会议纪要助手系统 自动生成</p>
    </div>
</body>
</html>
""")


def export_pdf(context: Dict) -> str:
    """
    将会议纪要数据渲染为 PDF 格式文件
    先将数据渲染为 HTML，再通过 WeasyPrint 转换为 PDF

    @param context: 包含会议所有信息的字典（同 export_markdown）
    @return: PDF 文件的完整路径
    """
    from weasyprint import HTML

    # 1. 使用 Jinja2 模板渲染 HTML
    html_content = HTML_TEMPLATE.render(**context)

    # 2. 写入临时 HTML 文件
    html_filename = f"{uuid.uuid4().hex[:8]}_temp.html"
    html_path = os.path.join(EXPORT_DIR, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3. 使用 WeasyPrint 将 HTML 转换为 PDF
    pdf_filename = f"{uuid.uuid4().hex[:8]}_minutes.pdf"
    pdf_path = os.path.join(EXPORT_DIR, pdf_filename)
    HTML(filename=html_path).write_pdf(pdf_path)

    # 4. 清理临时 HTML 文件
    try:
        os.remove(html_path)
    except OSError:
        pass

    return pdf_path
