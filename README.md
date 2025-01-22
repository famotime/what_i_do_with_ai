# What I Do With AI

这个项目记录了我使用AI（人工智能）完成的各种实用工具和有趣的尝试。

## 脚本文件说明

### `read_imges_with_zhipu.py`
- 使用智谱AI的GLM-4V模型进行图片文字识别
- 支持Base64编码图片处理
- 提供单图片处理和批量处理功能
- 需要配置智谱AI的API密钥

### `read_imges_with_doubao.py`
- 使用火山引擎抖报AI的视觉大模型进行图片文字识别
- 支持多种图片格式(jpg/jpeg/png/webp/gif/bmp)
- 提供高级的视觉理解能力
- 需要配置火山引擎ARK API密钥

### `read_images_with_doubao_ocr.py`
- 使用火山引擎OCR服务进行专业的文字识别
- 提供高精度的OCR识别功能
- 支持本地图片识别
- 需要配置火山引擎的AccessKey和SecretKey

### `text_classification_with_doubao.py`
- 使用火山引擎豆包模型进行文本分类
- 支持自定义分类规则和类别
- 可以处理大规模文本数据
- 生成分类结果报告

### `text_correction_with_doubao.py`
- 使用火山引擎豆包模型进行文本语法纠错和优化
- 支持长文本分段处理
- 保持原文结构进行语法改进
- 生成优化后的新文件

### `markdown-combiner.py`
- 合并多个Markdown文件
- 支持自定义分隔符
- 保持文件内容的组织结构
- 生成统一的输出文件

## 环境要求
- Python 3.6+
- zhipuai
- volcenginesdk

## 使用说明
1. 安装依赖：
```bash
pip install zhipuai
pip install volcengine-python-sdk[ark]
```

2. 配置API密钥：
在`../account/web_accounts.json`中配置相应的API密钥：
```json
{
    "zhipu": {
        "api_key": "your_api_key_here"
    },
    "huoshan": {
        "AccessKeyId": "your_access_key_id_here",
        "SecretAccessKey": "your_secret_access_key_here"
    }
}
```

## 注意事项
- API密钥文件已通过.gitignore排除，请妥善保管你的密钥信息
- 建议在使用前先测试单个文件，确认效果符合预期后再进行批量处理
- 对于大文件处理，建议先进行小规模测试
