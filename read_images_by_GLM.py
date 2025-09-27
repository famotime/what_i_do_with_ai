#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
## 功能描述
1. 批量读取指定目录下的图片文件；
2. 调用GLM视觉大模型，根据图片文本输出标题和完整正文；
3. 将输出标题增加到图片文件名，如："20250101-123456_Chrome.png"，更新为"20250101-123456_Chrome -- 标题.png"；
4. 将输出正文保存到同名的markdown文件中，如："20250101-123456_Chrome -- 标题.md"；
5. 智能跳过数据量过大的图片文件，避免API调用失败；
6. 返回批量处理统计结果。

## 参考信息
1. GLM大模型API文档：GLM大模型API文档.md、GLM文件API文档.md；
2. 调用模型型号可配置(glm-4.5v, glm-4v-plus-0111, glm-4v-flash, glm-4.1v-thinking-flashx, glm-4.1v-thinking-flash)，默认调用模型型号：glm-4v-flash（仅支持img_url参数，img_url内容为base64）；
"""

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
import os
import mimetypes
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from dotenv import load_dotenv
from PIL import Image

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GLMImageProcessor:
    def __init__(self, api_key: str, model: str = "glm-4v-flash", 
                 prompt: str = "",
                 base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                 files_url: str = "https://open.bigmodel.cn/api/paas/v4/files",
                 max_requests_per_second: float = 2.0,
                 max_tokens=1024, temperature=0.95, enable_token_estimation=True):
        """
        初始化GLM图片处理器
        
        Args:
            api_key: GLM API密钥
            model: 模型名称
            prompt: 提示词
            base_url: 对话API基础URL
            files_url: 文件上传API基础URL
            max_requests_per_second: 每秒最大请求数
            max_tokens: 最大token数
            temperature: 温度参数
            enable_token_estimation: 是否启用token预估功能
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.files_url = files_url
        self.prompt = prompt
        self.max_requests_per_second = max_requests_per_second
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_token_estimation = enable_token_estimation
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 速率限制相关
        self._last_request_time = 0
        self._min_interval = 1.0 / max_requests_per_second if max_requests_per_second > 0 else 0
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        
        # 支持base64编码的模型
        self.base64_supported_models = {'glm-4.5v', 'glm-4v-plus-0111', 'glm-4.1v-thinking-flashx', 'glm-4.1v-thinking-flash', 'glm-4v-flash'}
        
        # 需要文件上传的模型（已弃用，现在都使用base64）
        self.file_upload_models = set()
    
    def _rate_limit(self):
        """速率限制，确保不超过每秒最大请求数"""
        if self._min_interval > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._min_interval:
                sleep_time = self._min_interval - time_since_last
                time.sleep(sleep_time)
            self._last_request_time = time.time()
    
    def upload_file(self, image_path: Path) -> Optional[str]:
        """
        上传图片文件到GLM平台
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            文件ID，失败时返回None
        """
        try:
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type:
                mime_type = 'application/octet-stream'
            files = {
                'file': (image_path.name, open(image_path, 'rb'), mime_type),
                'purpose': (None, 'file-extract')
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(self.files_url, headers=headers, files=files, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            file_id = result['id']
            logger.info(f"文件上传成功: {image_path.name} -> {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"上传文件失败 {image_path}: {str(e)}")
            return None
        finally:
            if 'files' in locals():
                files['file'][1].close()
    
    def get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """
        获取图片的宽度和高度
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            (宽度, 高度) 元组
        """
        try:
            with Image.open(image_path) as img:
                return img.size  # 返回 (width, height)
        except Exception as e:
            logger.error(f"获取图片尺寸失败 {image_path}: {str(e)}")
            # 如果无法获取尺寸，返回默认值
            return (1024, 1024)
    
    def encode_image_to_base64(self, image_path: Path) -> str:
        """
        将图片文件编码为base64字符串
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片字符串
        """
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"编码图片失败 {image_path}: {str(e)}")
            raise
    
    def estimate_token_count(self, image_path: Path, prompt: str) -> int:
        """
        基于图片像素尺寸估算请求数据的token数量
        
        这个函数用于在调用API之前估算请求的token数量，避免因数据量过大导致API调用失败。
        当估算的token数量超过max_tokens的80%时，会跳过该文件的处理。
        
        估算逻辑：
        1. 图片会被缩放到一定分辨率范围内，并分割成512×512像素块
        2. 每个512×512像素块大约消耗170个tokens
        3. 基础token数为85个
        4. 文本内容按1:3比例估算（3个字符约等于1个token）
        
        示例计算：
        - 1024×1024图片：2×2=4块 → 4×170+85=765 tokens
        - 2048×4096图片：4×8=32块 → 32×170+85=5525 tokens
        
        Args:
            image_path: 图片文件路径
            prompt: 提示词文本
            
        Returns:
            估算的token数量
        """
        try:
            # 获取图片尺寸
            width, height = self.get_image_dimensions(image_path)
            
            # 计算文本部分的token数
            text_tokens = len(prompt) // 3  # 保守估算：3个字符约等于1个token
            
            # 计算图片的token数
            # 图片会被分割成512×512的像素块
            block_size = 512
            blocks_width = (width + block_size - 1) // block_size  # 向上取整
            blocks_height = (height + block_size - 1) // block_size  # 向上取整
            total_blocks = blocks_width * blocks_height
            
            # 每个512×512像素块大约消耗170个tokens
            tokens_per_block = 170
            image_tokens = total_blocks * tokens_per_block
            
            # 基础token数（系统开销）
            base_tokens = 85
            
            total_tokens = text_tokens + image_tokens + base_tokens
            
            logger.debug(f"图片 {image_path.name}: {width}×{height} -> {blocks_width}×{blocks_height} 块 -> {total_blocks} 块 -> {image_tokens} tokens")
            
            return total_tokens
            
        except Exception as e:
            logger.error(f"估算token数量失败 {image_path}: {str(e)}")
            # 如果估算失败，返回一个较大的保守值
            return self.max_tokens
    
    def call_glm_api(self, image_path: Path) -> Optional[Dict[str, str]]:
        """
        调用GLM视觉模型API分析图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            包含title和content的字典，失败时返回None
        """
        try:
            # 应用速率限制
            self._rate_limit()
            
            # 所有模型都使用base64编码
            base64_image = self.encode_image_to_base64(image_path)
            
            # 预处理：检查数据大小是否接近max_tokens（如果启用了token预估）
            if self.enable_token_estimation:
                estimated_tokens = self.estimate_token_count(image_path, self.prompt)
                token_threshold = self.max_tokens * 0.8  # 当估算token数达到max_tokens的80%时跳过
                
                if estimated_tokens > token_threshold:
                    logger.warning(f"跳过处理 {image_path.name}: 估算token数 {estimated_tokens} 接近max_tokens {self.max_tokens} (阈值: {token_threshold})")
                    return None
            
            # 构建请求数据（使用base64）
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": base64_image  # 直接使用base64字符串，不加前缀
                                }
                            },
                            {
                                "type": "text",
                                "text": self.prompt
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            # 发送请求
            response = requests.post(self.base_url, headers=self.headers, json=data, timeout=60)
            
            # 如果请求失败，打印详细错误信息
            if response.status_code != 200:
                logger.error(f"API请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                logger.error(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析JSON响应
            try:
                # 先清理内容，移除可能的markdown代码块标记
                cleaned_content = content.strip()
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]  # 移除 ```json
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]  # 移除 ```
                cleaned_content = cleaned_content.strip()
                
                # 尝试从响应中提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    
                    # 进一步清理JSON字符串，移除开头可能的多余字符
                    json_str = json_str.strip()
                    # 确保以{开头
                    if not json_str.startswith('{'):
                        brace_start = json_str.find('{')
                        if brace_start != -1:
                            json_str = json_str[brace_start:]
                    
                    # 改进的JSON字符串处理
                    # 先处理content字段中的换行符和引号
                    def fix_json_string(match):
                        field_name = match.group(1)
                        field_value = match.group(2)
                        
                        if field_name == 'content':
                            # 对于content字段，需要特殊处理换行符
                            # 将未转义的换行符替换为\\n
                            field_value = field_value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            # 处理未转义的引号
                            field_value = field_value.replace('"', '\\"')
                        else:
                            # 对于其他字段，只处理基本的转义
                            field_value = field_value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                        
                        return f'"{field_name}": "{field_value}"'
                    
                    # 使用正则表达式匹配字段并修复
                    json_str = re.sub(r'"([^"]+)":\s*"([^"]*(?:\\.[^"]*)*)"', fix_json_string, json_str, flags=re.DOTALL)
                    
                    parsed_content = json.loads(json_str)
                else:
                    # 如果没有找到JSON，尝试直接解析整个内容
                    cleaned_content = cleaned_content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    parsed_content = json.loads(cleaned_content)
                
                return {
                    'title': parsed_content.get('title', ''),
                    'content': parsed_content.get('content', '')
                }
            except json.JSONDecodeError as e:
                logger.error(f"解析API响应JSON失败: {str(e)}")
                logger.error(f"原始响应: {content}")
                
                # 尝试更简单的手动解析方法
                try:
                    # 首先尝试从原始content中提取JSON部分
                    json_start = content.find('{')
                    json_end = content.rfind('}')
                    
                    if json_start != -1 and json_end != -1 and json_end > json_start:
                        json_content = content[json_start:json_end + 1]
                        
                        # 使用更宽松的正则表达式提取title和content
                        title_match = re.search(r'"title":\s*"([^"]*)"', json_content)
                        content_match = re.search(r'"content":\s*"([^"]*(?:\\.[^"]*)*)"', json_content, re.DOTALL)
                        
                        if title_match and content_match:
                            title = title_match.group(1)
                            content_text = content_match.group(1)
                            # 处理转义的换行符
                            content_text = content_text.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
                            return {
                                'title': title,
                                'content': content_text
                            }
                    
                    # 如果上述方法失败，尝试更简单的方法
                    # 查找title和content的边界
                    title_start = content.find('"title":')
                    content_start = content.find('"content":')
                    
                    if title_start != -1 and content_start != -1:
                        # 提取title
                        title_start = content.find('"', title_start + 8) + 1
                        title_end = content.find('"', title_start)
                        title = content[title_start:title_end]
                        
                        # 提取content - 使用更智能的方法
                        content_start = content.find('"', content_start + 9) + 1
                        
                        # 找到content字段的结束位置
                        # 由于content可能包含换行符，需要更仔细地处理
                        content_end = content_start
                        quote_count = 0
                        in_escape = False
                        
                        for i in range(content_start, len(content)):
                            char = content[i]
                            if in_escape:
                                in_escape = False
                                continue
                            if char == '\\':
                                in_escape = True
                                continue
                            if char == '"':
                                quote_count += 1
                                if quote_count % 2 == 0:  # 找到配对的引号
                                    content_end = i
                                    break
                        
                        content_text = content[content_start:content_end]
                        
                        # 处理转义的换行符
                        content_text = content_text.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
                        
                        return {
                            'title': title,
                            'content': content_text
                        }
                            
                except Exception as parse_error:
                    logger.error(f"手动解析也失败: {str(parse_error)}")
                
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败 {image_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"处理图片失败 {image_path}: {str(e)}")
            return None
    
    def is_image_file(self, file_path: Path) -> bool:
        """
        判断文件是否为支持的图片格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为支持的图片格式
        """
        return file_path.suffix.lower() in self.supported_formats
    
    def is_processed_file(self, file_path: Path) -> bool:
        """
        判断文件是否已经处理过（文件名中包含" -- "）
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否已经处理过
        """
        return " -- " in file_path.name
    
    def clean_filename(self, filename: str, max_length: int = 250) -> str:
        """
        清理文件名，移除不合法字符并限制长度
        
        Args:
            filename: 原始文件名
            max_length: 最大长度限制
            
        Returns:
            清理后的文件名
        """
        # Windows不合法字符
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        
        # 移除不合法字符
        clean_name = re.sub(invalid_chars, '_', filename)
        
        # 移除开头和结尾的空格和点
        clean_name = clean_name.strip(' .')
        
        # 移除连续的下划线
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # 确保文件名不为空
        if not clean_name or clean_name == '_':
            clean_name = 'unnamed'
        
        # 限制长度，保留扩展名
        if len(clean_name) > max_length:
            # 如果有扩展名，保留扩展名
            if '.' in clean_name:
                name_part, ext_part = clean_name.rsplit('.', 1)
                max_name_length = max_length - len(ext_part) - 1
                clean_name = name_part[:max_name_length] + '.' + ext_part
            else:
                clean_name = clean_name[:max_length]
        
        return clean_name
    
    def generate_unique_filename(self, base_path: Path) -> Path:
        """
        生成唯一的文件名，如果文件已存在则添加数字后缀
        
        Args:
            base_path: 基础文件路径
            
        Returns:
            唯一的文件路径
        """
        if not base_path.exists():
            return base_path
        
        # 分离文件名和扩展名
        stem = base_path.stem
        suffix = base_path.suffix
        parent = base_path.parent
        
        # 添加数字后缀直到找到不存在的文件名
        counter = 1
        while True:
            new_stem = f"{stem}_{counter}"
            new_path = parent / (new_stem + suffix)
            if not new_path.exists():
                return new_path
            counter += 1
            
            # 防止无限循环
            if counter > 9999:
                # 使用时间戳作为后缀
                import time
                timestamp = int(time.time())
                new_stem = f"{stem}_{timestamp}"
                return parent / (new_stem + suffix)
    
    def generate_new_filename(self, original_path: Path, title: str) -> Path:
        """
        生成新的文件名，在原名后添加标题
        
        Args:
            original_path: 原始文件路径
            title: 标题
            
        Returns:
            新的文件路径
        """
        # 清理标题
        clean_title = self.clean_filename(title, max_length=100)
        
        # 构建新文件名
        stem = original_path.stem
        suffix = original_path.suffix
        
        # 清理原始文件名
        clean_stem = self.clean_filename(stem, max_length=100)
        
        # 构建新文件名，确保总长度不超过255字符（Windows限制）
        new_stem = f"{clean_stem} -- {clean_title}"
        
        # 如果总长度超过限制，进一步缩短
        max_total_length = 250  # 留一些余量
        if len(new_stem) > max_total_length:
            # 计算各部分的最大长度
            separator = " -- "
            max_title_length = 100
            max_stem_length = max_total_length - len(separator) - max_title_length
            
            clean_stem = clean_stem[:max_stem_length]
            clean_title = clean_title[:max_title_length]
            new_stem = f"{clean_stem}{separator}{clean_title}"
        
        new_filename = new_stem + suffix
        
        # 最终清理
        new_filename = self.clean_filename(new_filename)
        
        # 生成新路径
        new_path = original_path.parent / new_filename
        
        # 确保文件名唯一
        return self.generate_unique_filename(new_path)
    
    def save_markdown(self, image_path: Path, title: str, content: str) -> Path:
        """
        保存markdown文件
        
        Args:
            image_path: 原始图片路径
            title: 标题
            content: 内容
            
        Returns:
            markdown文件路径
        """
        # 使用新的文件名清理功能
        clean_title = self.clean_filename(title, max_length=50)
        clean_stem = self.clean_filename(image_path.stem, max_length=100)
        
        # 构建markdown文件名
        new_stem = f"{clean_stem} -- {clean_title}"
        
        # 确保总长度不超过限制
        max_total_length = 200
        if len(new_stem) > max_total_length:
            separator = " -- "
            max_title_length = 30
            max_stem_length = max_total_length - len(separator) - max_title_length
            
            clean_stem = clean_stem[:max_stem_length]
            clean_title = clean_title[:max_title_length]
            new_stem = f"{clean_stem}{separator}{clean_title}"
        
        md_filename = new_stem + ".md"
        md_filename = self.clean_filename(md_filename)
        md_path = image_path.parent / md_filename
        
        # 确保markdown文件名唯一
        md_path = self.generate_unique_filename(md_path)
        
        # 保存markdown文件
        try:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"保存markdown文件: {md_path}")
            return md_path
        except Exception as e:
            logger.error(f"保存markdown文件失败 {md_path}: {str(e)}")
            # 不抛出异常，返回None让调用者处理
            return None

class ImageBatchProcessor:
    def __init__(self, source_dir: str, api_key: str, model: str = "glm-4v-flash", 
                 prompt: str = "", max_workers: int = 4, max_requests_per_second: float = 2.0, 
                 max_tokens=1024, temperature=0.95, enable_token_estimation=True):
        """
        初始化批量图片处理器
        
        Args:
            source_dir: 源目录路径
            api_key: GLM API密钥
            model: 模型名称
            prompt: 提示词
            max_workers: 最大并发工作线程数
            max_requests_per_second: 每秒最大请求数
            max_tokens: 最大token数
            temperature: 温度参数
            enable_token_estimation: 是否启用token预估功能
        """
        self.source_dir = Path(source_dir)
        self.max_workers = max_workers
        self.processor = GLMImageProcessor(api_key, model, prompt, 
                                         max_requests_per_second=max_requests_per_second,
                                         max_tokens=max_tokens,
                                         temperature=temperature,
                                         enable_token_estimation=enable_token_estimation)
        
        if not self.source_dir.exists():
            raise FileNotFoundError(f"源目录不存在: {self.source_dir}")
        
        if not self.source_dir.is_dir():
            raise NotADirectoryError(f"路径不是目录: {self.source_dir}")
    
    def scan_images(self, recursive: bool = True) -> List[Path]:
        """
        扫描目录中的图片文件
        
        Args:
            recursive: 是否递归扫描子目录
            
        Returns:
            图片文件路径列表
        """
        if recursive:
            all_files = [f for f in self.source_dir.rglob('*') if f.is_file()]
        else:
            all_files = [f for f in self.source_dir.iterdir() if f.is_file()]
        
        # 筛选图片文件
        image_files = [f for f in all_files if self.processor.is_image_file(f)]
        
        # 筛选未处理的文件
        unprocessed_files = [f for f in image_files if not self.processor.is_processed_file(f)]
        
        processed_count = len(image_files) - len(unprocessed_files)
        logger.info(f"找到 {len(image_files)} 个图片文件，其中 {processed_count} 个已处理，{len(unprocessed_files)} 个待处理")
        
        return unprocessed_files
    
    def process_images_concurrent(self, image_files: List[Path], dry_run: bool = False) -> List[Dict]:
        """
        并发处理图片文件
        
        Args:
            image_files: 图片文件列表
            dry_run: 是否为试运行模式
            
        Returns:
            处理结果列表
        """
        results = []
        
        # 使用ThreadPoolExecutor进行并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_path = {
                executor.submit(self.process_single_image, image_path, dry_run): image_path 
                for image_path in image_files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_path):
                image_path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 打印进度
                    completed = len(results)
                    total = len(image_files)
                    logger.info(f"处理进度: {completed}/{total} - {image_path.name}")
                    
                except Exception as e:
                    logger.error(f"处理图片失败 {image_path}: {str(e)}")
                    results.append({
                        'file': str(image_path),
                        'success': False,
                        'title': '',
                        'new_filename': '',
                        'md_file': '',
                        'error': str(e)
                    })
        
        return results
    
    def process_single_image(self, image_path: Path, dry_run: bool = False) -> Dict:
        """
        处理单个图片文件
        
        Args:
            image_path: 图片文件路径
            dry_run: 是否为试运行模式
            
        Returns:
            处理结果字典
        """
        result = {
            'file': str(image_path),
            'success': False,
            'title': '',
            'new_filename': '',
            'md_file': '',
            'error': '',
            'skipped': False,
            'skip_reason': ''
        }
        
        try:
            logger.info(f"处理图片: {image_path.name}")
            
            # 调用API分析图片
            api_result = self.processor.call_glm_api(image_path)
            if not api_result:
                # 检查是否是因为token限制而跳过（如果启用了token预估）
                if self.processor.enable_token_estimation:
                    estimated_tokens = self.processor.estimate_token_count(image_path, self.processor.prompt)
                    token_threshold = self.processor.max_tokens * 0.8
                    
                    if estimated_tokens > token_threshold:
                        result['skipped'] = True
                        result['skip_reason'] = f'数据量过大 (估算token: {estimated_tokens}, 阈值: {token_threshold})'
                        logger.info(f"跳过处理 {image_path.name}: {result['skip_reason']}")
                        return result
                
                result['error'] = 'API调用失败'
                return result
            
            title = api_result['title']
            content = api_result['content']
            
            if not title or not content:
                result['error'] = 'API返回空结果'
                return result
            
            result['title'] = title
            
            if not dry_run:
                # 重命名图片文件
                new_image_path = self.processor.generate_new_filename(image_path, title)
                image_path.rename(new_image_path)
                result['new_filename'] = new_image_path.name
                
                # 保存markdown文件
                md_path = self.processor.save_markdown(image_path, title, content)
                if md_path:
                    result['md_file'] = str(md_path)
                else:
                    result['error'] = '保存markdown文件失败'
                    return result
            else:
                # 试运行模式，只生成新文件名
                new_image_path = self.processor.generate_new_filename(image_path, title)
                result['new_filename'] = new_image_path.name
                result['md_file'] = str(new_image_path.parent / f"{new_image_path.stem}.md")
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"处理图片失败 {image_path}: {str(e)}")
        
        return result
    
    def process_batch(self, dry_run: bool = False, recursive: bool = True, 
                     use_concurrent: bool = True) -> Dict[str, List]:
        """
        批量处理图片文件
        
        Args:
            dry_run: 是否为试运行模式
            recursive: 是否递归扫描子目录
            use_concurrent: 是否使用并发处理
            
        Returns:
            批量处理结果统计
        """
        # 扫描图片文件
        image_files = self.scan_images(recursive)
        
        results = {
            'processed_files': [],
            'successful_files': [],
            'failed_files': [],
            'skipped_files': [],
            'total_count': len(image_files),
            'success_count': 0,
            'failure_count': 0,
            'skipped_count': 0
        }
        
        if use_concurrent and len(image_files) > 1:
            # 使用并发处理
            logger.info(f"使用并发处理模式，最大工作线程数: {self.max_workers}")
            processed_results = self.process_images_concurrent(image_files, dry_run)
            results['processed_files'] = processed_results
        else:
            # 使用顺序处理
            logger.info("使用顺序处理模式")
            for i, image_path in enumerate(image_files, 1):
                logger.info(f"处理进度: {i}/{len(image_files)} - {image_path.name}")
                
                # 处理单个图片
                result = self.process_single_image(image_path, dry_run)
                results['processed_files'].append(result)
        
        # 统计结果
        for result in results['processed_files']:
            if result.get('skipped', False):
                results['skipped_files'].append(result)
                results['skipped_count'] += 1
            elif result['success']:
                results['successful_files'].append(result)
                results['success_count'] += 1
            else:
                results['failed_files'].append(result)
                results['failure_count'] += 1
            
            # 添加延迟避免API限制
            time.sleep(1)
        
        return results
    
    def print_results(self, results: Dict[str, List]):
        """
        打印处理结果统计
        
        Args:
            results: 处理结果
        """
        print("\n" + "="*60)
        print("图片批量处理结果统计")
        print("="*60)
        
        print(f"待处理文件数量: {results['total_count']}")
        print(f"成功处理: {results['success_count']}")
        print(f"处理失败: {results['failure_count']}")
        print(f"跳过处理: {results['skipped_count']}")
        
        if results['successful_files']:
            print(f"\n成功处理的文件:")
            for result in results['successful_files']:
                print(f"  {Path(result['file']).name}")
                print(f"    标题: {result['title']}")
                print(f"    新文件名: {result['new_filename']}")
                print(f"    Markdown文件: {Path(result['md_file']).name}")
                print()
        
        if results['skipped_files']:
            print(f"\n跳过处理的文件:")
            for result in results['skipped_files']:
                print(f"  {Path(result['file']).name}")
                print(f"    跳过原因: {result['skip_reason']}")
                print()
        
        if results['failed_files']:
            print(f"\n处理失败的文件:")
            for result in results['failed_files']:
                print(f"  {Path(result['file']).name}")
                print(f"    错误: {result['error']}")
                print()
        
        print("="*60)

def main(source_dir, api_key, model, dry_run, recursive, prompt, 
         max_workers=4, max_requests_per_second=2.0, use_concurrent=True, max_tokens=1024, temperature=0.95, enable_token_estimation=True):
    """主函数"""
    
    try:
        # 创建批量处理器
        processor = ImageBatchProcessor(source_dir, api_key, model, prompt, 
                                      max_workers=max_workers, 
                                      max_requests_per_second=max_requests_per_second,
                                      max_tokens=max_tokens,
                                      temperature=temperature,
                                      enable_token_estimation=enable_token_estimation)
        
        print(f"源目录: {processor.source_dir}")
        print(f"使用模型: {model}")
        if dry_run:
            print("模式: 试运行（不会实际处理文件）")
        else:
            print("模式: 实际执行")
        if recursive:
            print("扫描模式: 递归扫描子目录")
        else:
            print("扫描模式: 仅扫描当前目录")
        
        # 执行批量处理
        results = processor.process_batch(dry_run=dry_run, recursive=recursive, 
                                        use_concurrent=use_concurrent)
        
        # 打印结果
        processor.print_results(results)
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    
    # ========== 配置区域 - 请在这里修改配置 ==========
    # 源目录路径（要处理的图片文件夹）
    SOURCE_DIR = r"H:\BaiduSyncdisk\个人图片及视频\手机截图\归档"
    
    # GLM API密钥（从.env文件读取）
    GLM_API_KEY = os.getenv("GLM_API_KEY", "your_glm_api_key_here")
    
    # 检查API密钥是否为默认值
    if GLM_API_KEY == "your_glm_api_key_here":
        print("警告: 请在.env文件中设置您的GLM_API_KEY")
        print("当前使用的是默认API密钥，可能无法正常工作")
        print("请在.env文件中将 'your_glm_api_key_here' 替换为您的实际API密钥")

    # Prompt
    PROMPT = """请读取图片文本，输出标题和完整正文：
1. 标题概括自图片文本，简明扼要，包含关键信息，应少于100字；
2. 正文来自OCR完整原文，包含标题、原文段落、原文粗体格式（若有），markdown格式；
3. 不要添加解释说明，仅以json格式输出，仅包含一个标题和一项内容，示例：
{
    "title": "标题",
    "content": "# 标题\n正文内容"
}
"""

    # 模型配置（可选：glm-4.5v, glm-4v-plus-0111, glm-4v-flash, glm-4.1v-thinking-flashx, glm-4.1v-thinking-flash）
    # 支持img_url参数，img_url内容为base64
    # MODEL = "glm-4v-flash"  # 默认模型，MAX_TOKENS=1024
    # MAX_TOKENS = 1024  # 非thinking模型，MAX_TOKENS使用 1024
    # TEMPERATURE = 0.95
    
    # Token预估设置
    ENABLE_TOKEN_ESTIMATION = False  # 是否启用token预估功能（True=启用，False=禁用）
    # 启用时：会预先估算图片的token消耗，超过阈值时跳过处理，避免API调用失败
    # 禁用时：所有图片都会尝试调用API，可能因数据量过大导致失败
    # 注意：当图片数据量接近MAX_TOKENS的80%时，程序会自动跳过处理该图片，避免API调用失败
    # Token估算基于图片像素尺寸：每个512×512像素块约消耗170个tokens，基础token数为85个  

    MODEL = "glm-4.1v-thinking-flashx"  
    MAX_TOKENS = 4096  # thinking模型使用 4096
    TEMPERATURE = 0.95  
    
    # 是否试运行模式（True=只预览不实际处理文件，False=实际执行）
    DRY_RUN = False  # 建议先设为True预览结果，确认无误后改为False
    
    # 是否递归扫描子目录（True=扫描所有子目录，False=仅扫描当前目录）
    RECURSIVE = True  # 设为True可以扫描所有子目录中的图片
    
    # 并发处理配置
    MAX_WORKERS = 10  # 最大并发工作线程数
    MAX_REQUESTS_PER_SECOND = 10  # 每秒最大请求数（建议2-5之间）
    USE_CONCURRENT = True  # 是否使用并发处理（True=并发，False=顺序）
    # ================================================
    main(SOURCE_DIR, GLM_API_KEY, MODEL, DRY_RUN, RECURSIVE, PROMPT, 
         MAX_WORKERS, MAX_REQUESTS_PER_SECOND, USE_CONCURRENT, MAX_TOKENS, TEMPERATURE, ENABLE_TOKEN_ESTIMATION)