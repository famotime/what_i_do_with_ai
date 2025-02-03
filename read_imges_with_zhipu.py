"""
使用大模型读取图片信息并生成图片内容的文本文件：
1. 提取图片中的文字，但去除手机截图中的时间戳、运营商等无关信息，去除不必要的换行；
2. 将提取的文字内容保存到文本文件中，文件名为图片文件名，文件路径为图片文件所在目录；
"""
import base64
import os
import json
from pathlib import Path
# 通过 pip install zhipuai 安装智谱 AI SDK
from zhipuai import ZhipuAI


def encode_image(image_path: str) -> str:
    """
    将指定路径的图片转换为Base64编码
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    try:
        return base64.b64encode(image_path.read_bytes()).decode('utf-8')
    except IOError as e:
        raise IOError(f"读取图片文件失败: {e}")


def get_completion_from_messages(image_path, model, api_key, prompt):
    """
    调用大模型API处理图片
    """
    client = ZhipuAI(api_key=api_key)

    # 直接读取图片的base64编码
    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image  # 直接使用base64编码
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )

    return response.choices[0].message.content.strip()


def save_text_to_file(image_path: str, text_content: str) -> None:
    """
    将文本内容保存到与图片同名的txt文件中

    Args:
        image_path (str): 图片文件路径
        text_content (str): 要保存的文本内容
    """
    image_path = Path(image_path)
    output_path = image_path.with_suffix('.txt')

    try:
        output_path.write_text(text_content, encoding='utf-8')
        print(f"文本已保存到: {output_path}")
    except IOError as e:
        raise IOError(f"保存文本文件失败: {e}")


def process_image_directory(directory_path: str, model: str, prompt: str, skip_existing: bool = False) -> None:
    """
    批量处理指定目录下的所有图片文件

    Args:
        directory_path (str): 图片目录路径
        model (str): 模型编码
        prompt (str): 提示词
        skip_existing (bool): 是否跳过已存在对应文本文件的图片，默认为False
    """
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}

    # 获取所有图片文件
    image_files = [f for f in directory.glob('*') if f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"在目录 {directory} 中未找到支持的图片文件")
        return

    print(f"找到 {len(image_files)} 个图片文件，开始处理...")

    for i, image_path in enumerate(image_files, 1):
        try:
            # 检查对应的文本文件是否存在
            text_file = image_path.with_suffix('.txt')
            if skip_existing and text_file.exists():
                print(f"\n跳过第 {i}/{len(image_files)} 个文件: {image_path.name} (文本文件已存在)")
                continue

            print(f"\n处理第 {i}/{len(image_files)} 个文件: {image_path.name}")
            response = get_completion_from_messages(str(image_path), model, api_key, prompt)
            print("提取的文本内容：")
            print(response)

            # 保存提取的文本到文件
            save_text_to_file(str(image_path), response)
        except Exception as e:
            print(f"处理文件 {image_path.name} 时出错: {e}")
            continue


def read_account(account_path, service):
    """从json文件读取帐号秘钥信息"""
    with open(account_path) as f:
        web_accounts = json.load(f)
    return web_accounts[service]['api_key']


if __name__ == "__main__":
    account_path = "../account/web_accounts.json"
    model = "glm-4v-flash"  # 模型编码：glm-4v-plus-0111beta 、glm-4v-plus 、glm-4v、glm-4v-flash(免费)；
    prompt = "提取图片中的文字，但去除手机截图中的时间戳、运营商等无关信息，去除不必要的换行；仅返回图片中的文本内容，不要增加额外描述。"
    # prompt = "提取书籍照片中的文字，注意只提取手工划线的文字，以及在页面左侧使用竖线标记范围内的段落文字；仅返回照片中的文本，不要增加额外描述。"

    api_key = read_account(account_path, "zhipu")

    # 处理单个图片
    # image_path = r"H:\个人图片及视频\待整理\HLTE700T相册\截屏录屏\Screenshot_20190407_212814419_Chrome.jpg"
    # response = get_completion_from_messages(image_path, model, api_key, prompt)
    # print("\n提取的文本内容：")
    # print(response)
    # save_text_to_file(image_path, response)

    # 批量处理目录下的图片，设置 skip_existing=True 可以跳过已有文本文件的图片
    directory_path = r"C:\Users\Administrator\Desktop\images"
    process_image_directory(directory_path, model, prompt, skip_existing=True)
