"""
使用freepik的api创建图片

## 功能特性

### 支持的参数
- **prompt**: 图片描述文本
- **num_images**: 生成图片数量 (1-4)
- **aspect_ratio**: 长宽比
  - `square_1_1`: 正方形 1:1
  - `social_story_9_16`: 社交故事 9:16
  - `widescreen_16_9`: 宽屏 16:9
  - `traditional_3_4`: 传统 3:4
  - `classic_4_3`: 经典 4:3

### 风格选项
- **style**: 风格类型
  - `photo`: 照片风格
  - `anime`: 动漫风格
  - `digital_art`: 数字艺术
  - `illustration`: 插画风格
  - 等等

### 效果选项
- **color**: 颜色效果
  - `b&w`: 黑白
  - `pastel`: 粉彩
  - `sepia`: 复古棕色
  - `dramatic`: 戏剧性
  - `vibrant`: 鲜艳
  - `orange&teal`: 橙青对比
  - `film-filter`: 胶片滤镜
  - `split`: 分割色调
  - `electric`: 电光效果
  - `pastel-pink`: 粉彩粉红
  - `gold-glow`: 金色光晕
  - `autumn`: 秋季色调
  - `muted-green`: 静音绿色
  - `deep-teal`: 深青色
  - `duotone`: 双色调
  - `terracotta&teal`: 陶土青色
  - `red&blue`: 红蓝对比
  - `cold-neon`: 冷霓虹
  - `burgundy&blue`: 酒红蓝色

- **lightning**: 光照效果
  - `studio`: 工作室照明
  - `warm`: 暖光
  - `cinematic`: 电影光效
  - `volumetric`: 体积光
  - `golden-hour`: 黄金时段
  - `long-exposure`: 长曝光
  - `cold`: 冷光
  - `iridescent`: 彩虹光
  - `dramatic`: 戏剧性光照
  - `hardlight`: 硬光
  - `redscale`: 红色调
  - `indoor-light`: 室内光

- **framing**: 构图
  - `portrait`: 肖像
  - `macro`: 微距
  - `panoramic`: 全景
  - `aerial-view`: 鸟瞰
  - `close-up`: 特写
  - `cinematic`: 电影构图
  - `high-angle`: 高角度
  - `low-angle`: 低角度
  - `symmetry`: 对称
  - `fish-eye`: 鱼眼
  - `first-person`: 第一人称视角


## 输出文件

生成的图片默认保存在 `output/` 目录下，文件名格式为：
```
freepik_imagen3_{timestamp}_{序号}.{扩展名}
```
例如：`freepik_imagen3_1703123456_1.jpg`

"""

import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class FreepikImageGenerator:
    """使用 Freepik Imagen3 API 生成图片的类"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 FreepikImageGenerator

        Args:
            api_key: Freepik API key，如果不提供则从环境变量 FREEPIK_API_KEY 获取
        """
        self.api_key = api_key or os.getenv('FREEPIK_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 Freepik API key，请设置环境变量 FREEPIK_API_KEY 或直接传入")

        # 检查API key格式（简单验证）
        if len(self.api_key) < 10:
            print(f"警告: API key 长度较短，请确认是否正确: {self.api_key[:5]}...")
        else:
            print(f"✓ API key已加载: {self.api_key[:8]}...{self.api_key[-4:]}")

        self.base_url = "https://api.freepik.com/v1/ai/text-to-image/imagen3"
        self.headers = {
            'Content-Type': 'application/json',
            'x-freepik-api-key': self.api_key
        }

    def create_image(
        self,
        prompt: str,
        num_images: int = 1,
        aspect_ratio: str = "square_1_1",
        style: str = "photo",
        color: str = None,
        lightning: str = None,
        framing: str = None,
        person_generation: str = "allow_adult",
        safety_settings: str = "block_low_and_above"
    ) -> Dict[str, Any]:
        """
        使用 Imagen3 创建图片

        Args:
            prompt: 图片描述文本
            num_images: 生成图片数量 (1-4)
            aspect_ratio: 长宽比，支持选项：
                - 'square_1_1': 正方形 1:1
                - 'social_story_9_16': 社交故事 9:16
                - 'widescreen_16_9': 宽屏 16:9
                - 'traditional_3_4': 传统 3:4
                - 'classic_4_3': 经典 4:3
            style: 风格 (photo, anime, digital_art, illustration, etc.)
            color: 颜色效果，支持选项：
                - 'b&w': 黑白, 'pastel': 粉彩, 'sepia': 复古棕色
                - 'dramatic': 戏剧性, 'vibrant': 鲜艳, 'orange&teal': 橙青对比
                - 'film-filter': 胶片滤镜, 'split': 分割色调, 'electric': 电光效果
                - 'pastel-pink': 粉彩粉红, 'gold-glow': 金色光晕, 'autumn': 秋季色调
                - 'muted-green': 静音绿色, 'deep-teal': 深青色, 'duotone': 双色调
                - 'terracotta&teal': 陶土青色, 'red&blue': 红蓝对比
                - 'cold-neon': 冷霓虹, 'burgundy&blue': 酒红蓝色
            lightning: 光照效果，支持选项：
                - 'studio': 工作室照明, 'warm': 暖光, 'cinematic': 电影光效
                - 'volumetric': 体积光, 'golden-hour': 黄金时段, 'long-exposure': 长曝光
                - 'cold': 冷光, 'iridescent': 彩虹光, 'dramatic': 戏剧性光照
                - 'hardlight': 硬光, 'redscale': 红色调, 'indoor-light': 室内光
            framing: 构图，支持选项：
                - 'portrait': 肖像, 'macro': 微距, 'panoramic': 全景
                - 'aerial-view': 鸟瞰, 'close-up': 特写, 'cinematic': 电影构图
                - 'high-angle': 高角度, 'low-angle': 低角度, 'symmetry': 对称
                - 'fish-eye': 鱼眼, 'first-person': 第一人称视角
            person_generation: 人像生成设置
            safety_settings: 安全设置

        Returns:
            API 响应数据
        """
        payload = {
            "prompt": prompt,
            "num_images": num_images,
            "aspect_ratio": aspect_ratio,
            "styling": {
                "style": style,
                "effects": {}
            },
            "person_generation": person_generation,
            "safety_settings": safety_settings
        }

        # 只添加非空的效果参数
        if color:
            payload["styling"]["effects"]["color"] = color
        if lightning:
            payload["styling"]["effects"]["lightning"] = lightning
        if framing:
            payload["styling"]["effects"]["framing"] = framing

        print(f"正在发送图片生成请求...")
        print(f"提示词: {prompt}")
        print(f"请求URL: {self.base_url}")
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            print(f"HTTP状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")

            # 无论成功失败都打印响应内容
            try:
                response_data = response.json()
                print(f"API响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError:
                print(f"响应内容（非JSON）: {response.text}")
                response_data = {}

            # 检查HTTP状态码
            response.raise_for_status()

            # 根据实际API响应格式解析task_id
            task_id = None
            if 'data' in response_data and 'task_id' in response_data['data']:
                # 新格式：{"data": {"task_id": "...", "status": "..."}}
                task_id = response_data['data']['task_id']
                task_status = response_data['data'].get('status', 'UNKNOWN')
                print(f"任务已创建，任务ID: {task_id}, 状态: {task_status}")
            elif 'task_id' in response_data:
                # 旧格式：{"task_id": "...", "task_status": "..."}
                task_id = response_data.get('task_id')
                task_status = response_data.get('task_status', 'UNKNOWN')
                print(f"任务已创建，任务ID: {task_id}, 状态: {task_status}")
            else:
                print(f"警告: 响应中没有找到task_id字段")

            return response_data

        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误状态码: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"错误详情: {e.response.text}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态数据
        """
        # 根据API文档构建状态查询URL
        status_url = f"https://api.freepik.com/v1/ai/text-to-image/imagen3/{task_id}"

        try:
            response = requests.get(status_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            print(f"状态查询响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result

        except requests.exceptions.RequestException as e:
            print(f"获取任务状态失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {e.response.text}")
            raise

    def wait_for_completion(self, task_id: str, max_wait_time: int = 300, poll_interval: int = 5) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            完成的任务数据
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            print(f"正在检查任务状态...")

            result = self.get_task_status(task_id)

            # 根据实际响应格式提取状态
            status = None
            if 'data' in result:
                # 新格式：{"data": {"status": "...", "generated": [...]}}
                status = result['data'].get('status')
                generated = result['data'].get('generated', [])
            else:
                # 旧格式：{"task_status": "...", "generated": [...]}
                status = result.get('task_status')
                generated = result.get('generated', [])

            print(f"当前状态: {status}")

            if status == 'COMPLETED':
                print("任务完成！")
                return result
            elif status == 'FAILED' or status == 'ERROR':
                print("任务失败")
                raise Exception(f"图片生成失败: {result}")
            elif status in ['IN_PROGRESS', 'PENDING', 'CREATED', 'PROCESSING']:
                print(f"任务进行中，{poll_interval}秒后重新检查...")
                time.sleep(poll_interval)
            else:
                print(f"未知状态: {status}")
                time.sleep(poll_interval)

        raise TimeoutError(f"任务在 {max_wait_time} 秒内未完成")

    def download_images(self, task_result: Dict[str, Any], output_dir: str = "output") -> List[Path]:
        """
        下载生成的图片

        Args:
            task_result: 完成的任务结果
            output_dir: 输出目录

        Returns:
            下载的图片文件路径列表
        """
        print(f"开始处理下载任务...")
        print(f"任务结果类型: {type(task_result)}")
        print(f"任务结果内容: {json.dumps(task_result, ensure_ascii=False, indent=2)}")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        downloaded_files = []

        # 根据响应格式提取生成的图片
        generated_images = []
        if isinstance(task_result, dict):
            if 'data' in task_result and 'generated' in task_result['data']:
                # 新格式：{"data": {"generated": [...]}}
                generated_images = task_result['data']['generated']
                print(f"使用新格式，找到 {len(generated_images)} 张图片")
            elif 'generated' in task_result:
                # 旧格式：{"generated": [...]}
                generated_images = task_result.get('generated', [])
                print(f"使用旧格式，找到 {len(generated_images)} 张图片")
            else:
                print(f"警告: 在任务结果中找不到 'generated' 字段")
                print(f"可用字段: {list(task_result.keys())}")
        else:
            print(f"错误: 任务结果不是字典类型: {type(task_result)}")
            return downloaded_files

        if not generated_images:
            print("没有找到生成的图片")
            return downloaded_files

        print(f"准备下载 {len(generated_images)} 张图片...")

        for i, image_data in enumerate(generated_images):
            print(f"\n处理图片 {i+1}:")
            print(f"  图片数据类型: {type(image_data)}")
            print(f"  图片数据内容: {image_data}")

            if isinstance(image_data, str):
                # 如果图片数据直接是URL字符串
                image_url = image_data
                print(f"  直接使用URL: {image_url}")
            elif isinstance(image_data, dict):
                # 如果图片数据是字典，尝试提取URL
                image_url = image_data.get('url') or image_data.get('image_url') or image_data.get('link')
                print(f"  从字典提取URL: {image_url}")
            else:
                print(f"  错误: 无法处理的图片数据类型: {type(image_data)}")
                continue

            if not image_url:
                print(f"  图片 {i+1} 没有有效的URL")
                continue

            try:
                print(f"  正在下载图片 {i+1}/{len(generated_images)}...")

                response = requests.get(image_url, timeout=30)
                response.raise_for_status()

                # 从URL或响应头中提取文件扩展名
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'  # 默认

                filename = f"freepik_imagen3_{int(time.time())}_{i+1}{ext}"
                file_path = output_path / filename

                with open(file_path, 'wb') as f:
                    f.write(response.content)

                downloaded_files.append(file_path)
                print(f"  ✓ 图片已保存到: {file_path}")

            except requests.exceptions.RequestException as e:
                print(f"  ❌ 下载图片 {i+1} 失败: {e}")
                continue

        return downloaded_files

    def generate_and_download(
        self,
        prompt: str,
        output_dir: str = "output",
        **kwargs
    ) -> List[Path]:
        """
        生成图片并下载到本地

        Args:
            prompt: 图片描述文本
            output_dir: 输出目录
            **kwargs: 其他创建图片的参数

        Returns:
            下载的图片文件路径列表
        """
        print(f"=== 开始图片生成流程 ===")

        # 创建图片生成任务
        result = self.create_image(prompt, **kwargs)

        if not result:
            raise Exception("API返回空响应")

        # 根据实际API响应格式提取task_id
        task_id = None
        if 'data' in result and 'task_id' in result['data']:
            # 新格式：{"data": {"task_id": "...", "status": "..."}}
            task_id = result['data']['task_id']
        elif 'task_id' in result:
            # 旧格式：{"task_id": "...", "task_status": "..."}
            task_id = result.get('task_id')

        if not task_id:
            print(f"完整API响应: {result}")
            raise Exception(f"未获取到任务ID。API响应: {result}")

        print(f"✓ 任务创建成功，ID: {task_id}")

        # 等待任务完成
        print(f"=== 等待任务完成 ===")
        completed_result = self.wait_for_completion(task_id)

        # 下载图片
        print(f"=== 开始下载图片 ===")
        downloaded_files = self.download_images(completed_result, output_dir)

        print(f"=== 流程完成 ===")
        return downloaded_files


def main():
    """主函数示例"""
    try:
        print("=== Freepik Imagen3 图片生成器 ===")

        # 初始化生成器
        generator = FreepikImageGenerator()

        # 示例：生成图片
        prompt = "中国年轻女性在著名旅游景点的单人照片，时尚休闲风格"

        print("开始生成图片...")
        downloaded_files = generator.generate_and_download(
            prompt=prompt,  # 必填，图片描述文本
            num_images=1,  # 可选，生成图片数量，默认1
            aspect_ratio="traditional_3_4",  # 可选，长宽比，支持：'square_1_1', 'social_story_9_16', 'widescreen_16_9', 'traditional_3_4', 'classic_4_3'
            style="photo",  # 可选，风格：photo, anime, digital_art, illustration等
            # color="vibrant",  # 可选，颜色效果：b&w, pastel, sepia, dramatic, vibrant, orange&teal等
            # lightning="golden-hour",  # 可选，光照：studio, warm, cinematic, volumetric, golden-hour等
            framing="portrait",  # 可选，构图：portrait, macro, panoramic, aerial-view, close-up等
            # output_dir="output"  # 可选，输出目录，默认output
        )

        print(f"\n🎉 成功生成并下载了 {len(downloaded_files)} 张图片:")
        for file_path in downloaded_files:
            print(f"  - {file_path}")

    except ValueError as e:
        print(f"\n❌ 配置错误: {e}")
        print("\n💡 解决方案:")
        print("1. 创建 .env 文件并添加: FREEPIK_API_KEY=your_api_key_here")
        print("2. 或者在代码中直接传入: FreepikImageGenerator(api_key='your_key')")
        print("3. 获取API key: https://www.freepik.com/api")

    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        print("\n💡 常见问题排查:")
        print("1. 检查网络连接")
        print("2. 确认API key是否有效")
        print("3. 检查API使用额度")
        print("4. 查看上方的详细错误信息")


if __name__ == "__main__":
    main()