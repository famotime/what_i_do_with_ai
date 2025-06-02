"""
使用Freepik的API将指定目录下的图片批量去除背景
"""
import os
from pathlib import Path
import requests
import logging
from typing import List
import time
from urllib.parse import urlparse
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FreepikBackgroundRemover:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FREEPIK_API_KEY')
        if not self.api_key:
            raise ValueError("未找到FREEPIK_API_KEY，请在.env文件中设置或直接传入api_key参数")

        self.base_url = "https://api.freepik.com/v1/ai/beta/remove-background"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-freepik-api-key': self.api_key
        }

    def remove_background(self, image_url: str) -> dict:
        """
        调用Freepik API去除图片背景

        Args:
            image_url: 图片URL

        Returns:
            dict: API响应结果
        """
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data={'image_url': image_url}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败: {str(e)}")
            raise

    def process_directory(self, input_dir: str, output_dir: str, supported_extensions: List[str] = None):
        """
        处理指定目录下的所有图片

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            supported_extensions: 支持的图片扩展名列表
        """
        if supported_extensions is None:
            supported_extensions = ['.jpg', '.jpeg', '.png']

        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 获取所有图片文件
        image_files = [
            f for f in input_path.glob('**/*')
            if f.suffix.lower() in supported_extensions
        ]

        logger.info(f"找到 {len(image_files)} 个图片文件")

        for image_file in image_files:
            try:
                logger.info(f"处理文件: {image_file.name}")

                # 这里需要先将图片上传到可访问的URL
                # 注意：实际使用时需要实现图片上传逻辑
                image_url = f"https://example.com/{image_file.name}"  # 替换为实际的上传URL

                # 调用API去除背景
                result = self.remove_background(image_url)

                # 下载处理后的图片
                output_file = output_path / f"no_bg_{image_file.name}"
                self._download_image(result['url'], output_file)

                logger.info(f"成功处理文件: {image_file.name}")

                # API调用间隔
                time.sleep(1)

            except Exception as e:
                logger.error(f"处理文件 {image_file.name} 时出错: {str(e)}")

    def _download_image(self, url: str, output_path: Path):
        """
        下载图片到指定路径

        Args:
            url: 图片URL
            output_path: 输出路径
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            output_path.write_bytes(response.content)
        except requests.exceptions.RequestException as e:
            logger.error(f"下载图片失败: {str(e)}")
            raise

def main():
    # 配置参数
    INPUT_DIR = "input_images"
    OUTPUT_DIR = "output_images"

    try:
        # 创建处理器实例
        remover = FreepikBackgroundRemover()

        # 处理图片
        remover.process_directory(INPUT_DIR, OUTPUT_DIR)
    except ValueError as e:
        logger.error(f"配置错误: {str(e)}")
        return
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        return

if __name__ == "__main__":
    main()