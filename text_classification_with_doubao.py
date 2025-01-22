"""
文本分类脚本
使用火山引擎 ARK Runtime API 的 Doubao 模型对文本按照预定义的类别进行整理和归类

处理流程：
1. 定义分类规则（system_message）
2. 读取原始笔记文件
3. 按分隔符拆分笔记
4. 使用 AI 模型对每条笔记进行分类
5. 将分类结果保存为新的 Markdown 文件
"""

import os
import re
from pathlib import Path
import datetime
import requests
from volcenginesdkarkruntime import Ark

# 火山引擎 ARK Runtime API 配置
endpoint_id = "ep-20241201202141-xghlt"         # doubao-pro-4k 模型端点
api_host = "ark.cn-beijing.volces.com"          # 华北 2 (北京) 服务器

def get_completion_from_messages(messages, model=endpoint_id, temperature=0.8, max_tokens=2048):
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

def decide_category(system_message, user_message):
    """
    使用 AI 模型判断文本所属类别

    Args:
        system_message (str): 系统提示词，定义分类规则
        user_message (str): 需要分类的文本内容

    Returns:
        str: 判断的类别结果
    """
    delimiter = "\n~~~\n"

    messages =  [
    {'role':'system',
    'content': system_message},
    {'role':'user',
    'content': f"请判断以下文本的类别：{delimiter}{user_message}{delimiter}"},
    ]

    response = get_completion_from_messages(messages)
    return response

def split_notes(txt_file, delimiter):
    """
    按指定分隔符拆分笔记文本文件

    Args:
        txt_file (Path): 笔记文本文件路径
        delimiter (str): 分隔符

    Returns:
        list: 拆分后的笔记列表
    """
    with open(txt_file, "r", encoding="utf-8") as f:
        notes = re.split(delimiter, f.read().replace("\u2003", "\n"))
        # print(notes)
    notes = [note.strip('\- \n\t') for note in notes if note.strip()]
    # print(notes)
    return notes

def save_organized_notes(txt_file, notes, system_message):
    """
    将分类后的笔记保存为 Markdown 文件，并打印统计信息

    Args:
        txt_file (Path): 原始笔记文件路径
        notes (list): 笔记列表
        system_message (str): 分类规则系统提示词
    """
    organized_notes = {}
    for note in notes:
        category = decide_category(system_message, note)
        print(f"{category}：\n{note}\n")
        organized_notes.setdefault(category, []).append(note)

    # 添加统计信息
    print("\n=== 分类统计信息 ===")
    print(f"总笔记数量：{len(notes)}")
    for category, notes_list in organized_notes.items():
        count = len(notes_list)
        percentage = (count / len(notes)) * 100
        print(f"{category}: {count} 条 ({percentage:.1f}%)")
    print("================\n")

    content = "# 笔记分类整理\n\n"
    # 添加统计信息到文件
    content += "## 统计信息\n"
    content += f"- 总笔记数量：{len(notes)}\n"
    for category, notes_list in organized_notes.items():
        count = len(notes_list)
        percentage = (count / len(notes)) * 100
        content += f"- {category}: {count} 条 ({percentage:.1f}%)\n"
    content += "\n"

    # 原有的分类内容
    for k, v in organized_notes.items():
        content += f"## {k}\n"
        for note in v:
            content += f"{note}\n\n---\n\n"
        content += "\n"

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    organized_notes_file = txt_file.parent / f"organized_notes_{now}.md"
    with open(organized_notes_file, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    system_message = """
    你是一名笔记整理大师，学识广博，可以充分理解文本内容，并按要求分类整理；
    可能的类别包括：Github项目、AI产品及服务、AI技术、技术趋势、案例故事及段子、书籍推荐、影视推荐、金句及名人名言、其他；
    文本内容只能归入一个类别，如果出现符合多个类别的情况，则按类别先后顺序归入第一个匹配的类别；
    如果文本信息不足，导致无法判别分类的情况，请归入"其他"类别；
    仅使用指定的类别进行分类，不要创建新的类别；
    请只输出类别，不要输出其他内容。
    """

    txt_file = Path(r"D:\Python_Work\AI\original_notes.txt")
    notes = split_notes(txt_file, "%%%")
    save_organized_notes(txt_file, notes, system_message)
