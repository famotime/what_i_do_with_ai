"""
使用大模型读取图片信息并生成图片内容的文本文件：
1. 提取图片中的文字，但去除手机截图中的时间戳、运营商等无关信息，去除不必要的换行；
2. 将提取的文字内容保存到文本文件中，文件名为图片文件名，文件路径为图片文件所在目录；
"""
import base64
import os
from pathlib import Path
# 通过 pip install volcengine-python-sdk[ark] 安装方舟SDK
from volcenginesdkarkruntime import Ark


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


def get_completion_from_messages(image_path, endpoint_id, prompt):
    """
    调用大模型API处理图片

    Args:
        image_path (str): 图片路径
        endpoint_id (str): 模型端点ID
        api_host (str): API主机地址
    """
    # 初始化Client对象
    client = Ark(
        api_key=os.environ.get("ARK_API_KEY"),
    )

    # 获取图片格式
    image_path = Path(image_path)
    image_format = image_path.suffix.lower()[1:]  # 移除点号
    if image_format == 'jpg':
        image_format = 'jpeg'

    base64_image = encode_image(image_path)
    # print(image_format, '\n', base64_image)

    response = client.chat.completions.create(
        model=endpoint_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            # 需要注意：传入Base64编码前需要增加前缀 data:image/{图片格式};base64,{Base64编码}：
                            # PNG图片："url":  f"data:image/png;base64,{base64_image}"
                            # JEPG图片："url":  f"data:image/jpeg;base64,{base64_image}"
                            # WEBP图片："url":  f"data:image/webp;base64,{base64_image}"
                            "url": f"data:image/{image_format};base64,{base64_image}"
                        },
                    },
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


def process_image_directory(directory_path: str, endpoint_id: str, prompt: str) -> None:
    """
    批量处理指定目录下的所有图片文件

    Args:
        directory_path (str): 图片目录路径
        endpoint_id (str): 模型端点ID
        prompt (str): 提示词
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
            print(f"\n处理第 {i}/{len(image_files)} 个文件: {image_path.name}")
            response = get_completion_from_messages(str(image_path), endpoint_id, prompt)
            print("提取的文本内容：")
            print(response)

            # 保存提取的文本到文件
            save_text_to_file(str(image_path), response)
        except Exception as e:
            print(f"处理文件 {image_path.name} 时出错: {e}")
            continue


if __name__ == "__main__":
    endpoint_id = "ep-20250118173521-zkx6c"         # Doubao-vision-lite-32k 视觉大模型
    # endpoint_id = "ep-20250118221957-kx6pg"         # Doubao-vision-pro-32k 视觉大模型

    prompt = "提取图片中的文字，但去除手机截图中的时间戳、运营商等无关信息，去除不必要的换行；仅返回图片中的文本内容，不要增加额外描述。"

    # 处理单个图片
    image_path = r"H:\个人图片及视频\手机截图\todo\1386073528941.jpg"
    response = get_completion_from_messages(image_path, endpoint_id, prompt)
    print("\n提取的文本内容：")
    print(response)
    save_text_to_file(image_path, response)

    # 批量处理目录下的图片
    # directory_path = r"H:\个人图片及视频\手机截图\todo"
    # process_image_directory(directory_path, endpoint_id, prompt)
