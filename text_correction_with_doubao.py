"""
使用火山引擎 ARK Runtime API 的 Doubao 模型对文本进行语法修正和优化。

处理流程：
1. 将指定的markdown文件按2级标题拆分；
2. 对每个拆分后的文本，调用Doubao模型进行语法修正和优化；
3. 将修正后的文本合并保存为新的markdown文件，文件名后缀为"_modified"。
"""

import os
import re
from pathlib import Path
import datetime
import requests
import pyperclip
from volcenginesdkarkruntime import Ark

def get_completion_from_messages(messages, endpoint_id, api_host, temperature=0.8, max_tokens=2048):
    """
    调用 Doubao API 获取模型响应

    Args:
        messages (list): 对话消息列表，包含 system 和 user 角色的消息
        model (str): 模型端点 ID
        temperature (float): 温度参数，控制输出的随机性，范围 0-1
        max_tokens (int): 生成文本的最大长度

    Returns:
        str: 模型生成的响应文本
    """
    client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    base_url=f"https://{api_host}/api/v3",
    # timeout=120,
    # max_retries=3,
    )

    completion = client.chat.completions.create(
        model=endpoint_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return completion.choices[0].message.content

def split_notes(file_path, delimiter="## "):
    """
    按指定的分隔符拆分Markdown文件

    Args:
        file_path (Path): Markdown文件路径
        delimiter (str): 分隔符，默认为二级标题

    Returns:
        list: 拆分后的文本列表
    """
    with file_path.open("r", encoding="utf-8") as file:
        content = file.read()

    # 正则表达式说明:
    # (?m) - 启用多行模式,使 ^ 能匹配每行的开头
    # ^ - 匹配行的开头
    # {delimiter} - 匹配传入的分隔符(默认为"## ")
    # 整体效果是按每行开头的分隔符进行分割
    return re.split(f"(?m)^{delimiter}", content)

def save_modified_notes(original_file, notes, system_message, endpoint_id, api_host):
    """
    保存修正后的文本到新的Markdown文件

    Args:
        original_file (Path): 原始Markdown文件路径
        notes (list): 修正后的文本列表
        system_message (str): 系统消息，用于API调用
        endpoint_id (str): 模型端点ID
        api_host (str): 火山引擎API主机
    """
    modified_notes = []
    total_notes = len(notes)
    for index, note in enumerate(notes, start=1):
        # print(f"待处理原文 {index}/{total_notes}: {note}\n")
        messages = [{"role": "system", "content": system_message}, {"role": "user", "content": f"待优化文本包含在xml标签中：<note>{note}</note>"}]
        corrected_note = get_completion_from_messages(messages, endpoint_id, api_host)
        if corrected_note.startswith("<note>") and corrected_note.endswith("</note>"):
            corrected_note = corrected_note[6:-7]  # 去掉<note>和</note>标签
        print(f"处理后结果 {index}/{total_notes}: {corrected_note}\n")
        modified_notes.append(corrected_note)

    modified_content = "\n\n".join(modified_notes)
    modified_file = original_file.with_name(original_file.stem + "_modified.md")
    with modified_file.open("w", encoding="utf-8") as file:
        file.write(modified_content)
    print(f"处理完成，结果已保存到 {modified_file}")

def split_long_text(text, max_length=2000):
    """
    将长文本按照最大长度限制分割，在句号处截断

    Args:
        text (str): 待分割的文本
        max_length (int): 每段最大长度限制

    Returns:
        list: 分割后的文本段落列表
    """
    if len(text) <= max_length:
        return [text]

    segments = []
    while text:
        if len(text) <= max_length:
            segments.append(text)
            break

        # 在max_length范围内查找最后一个句号
        pos = text[:max_length].rfind("。")
        if pos == -1:  # 如果没找到句号，则强制在max_length处截断
            pos = max_length

        segments.append(text[:pos + 1])  # 包含句号
        text = text[pos + 1:].lstrip()  # 移除开头的空白字符

    return segments


def main(system_message, endpoint_id, api_host, note, max_length=2000):
    """
    如果文本内容超过最大处理长度，则分批处理再合并结果；截断位置为长度范围内最近一个句号（“。”）
    """
    if len(note) > max_length:
        # 分段处理长文本

        segments = split_long_text(note)
        corrected_segments = []

        for i, segment in enumerate(segments, 1):
            print(f"正在处理第 {i}/{len(segments)} 段...")
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"待优化文本包含在xml标签中：<note>{segment}</note>"}
            ]
            corrected_segment = get_completion_from_messages(messages, endpoint_id, api_host)
            # 如果返回结果包含<note>和</note>标签，则去掉标签
            if corrected_segment.startswith("<note>") and corrected_segment.endswith("</note>"):
                corrected_segment = corrected_segment[6:-7]
            corrected_segments.append(corrected_segment)

        corrected_note = "\n".join(corrected_segments)
    else:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"待优化文本包含在xml标签中：<note>{note}</note>"}
        ]
        corrected_note = get_completion_from_messages(messages, endpoint_id, api_host)
        # 如果返回结果包含<note>和</note>标签，则去掉标签
        if corrected_note.startswith("<note>") and corrected_note.endswith("</note>"):
            corrected_note = corrected_note[6:-7]
    return corrected_note


if __name__ == "__main__":
    # 火山引擎模型配置
    # endpoint_id = "ep-20250207200354-zc5jl"         # doubao-lite-4k
    endpoint_id = "ep-20241201202141-xghlt"         # doubao-pro-4k
    # endpoint_id = "ep-20241201202907-l6cqm"         # doubao-pro-32k-240828
    api_host = "ark.cn-beijing.volces.com"          # 华北 2 (北京) 服务器

    max_length = 1500
    system_message = """
    你是一名精通中文的语言专家，请对文本进行做语法修正，适当修改词句，按照文章含义合理拆分段落，让整体文章内容更流畅，词句更偏向书面写作风格，但所有修改要求贴合原意，不要做大的改动。
    """

    note = pyperclip.paste()
    corrected_note = main(system_message, endpoint_id, api_host, note, max_length)
    pyperclip.copy(corrected_note)
    print(f"处理后结果已经复制到剪贴板: {corrected_note}\n")

    # system_message = """作为一名读书笔记整理者，请编辑调整markdown文档内容，要求：
    # 1. 给书名加上书名号；
    # 2. 调整文字顺序：书名 - 评分 - 作者/出版社 - 书籍图片链接；
    # 3. 仅按上述要求编辑调整文字，其余文字不做修改或增删；
    # 示例：original to edited
    # <original>
    # ## 年度图书

    # [8.9](https://book.douban.com/subject/36593622/)
    # ![image](images/s34705784.jpg)
    # [世上为什么要有图书馆](https://book.douban.com/subject/36593622/)
    # 杨素秋 / 上海译文出版社
    # </original>

    # <edited>
    # ## 年度图书
    # ### [《世上为什么要有图书馆》](https://book.douban.com/subject/36593622/)
    # 杨素秋 / 上海译文出版社
    # 豆瓣评分：8.9
    # ![image](images/s34705784.jpg)

    # <edited>
    # """

    # 按二级标题拆分markdown文件内容分批处理并保存
    # md_file = Path(r"C:\Users\Administrator\Desktop\豆瓣2024年度读书榜单.md")
    # notes = split_notes(md_file, "## ")
    # save_modified_notes(md_file, notes, system_message)
