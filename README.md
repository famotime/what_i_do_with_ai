# What I Do With AI

这个项目记录了我使用AI（人工智能）完成的各种实用工具和有趣的尝试。

## 项目列表

### 1. 图片文字提取工具
- 使用智谱AI的GLM-4V模型提取图片中的文字内容
- 自动过滤手机截图中的时间戳、运营商等无关信息
- 支持批量处理整个目录的图片
- 将提取的文字保存为同名的txt文件

## 环境要求
- Python 3.6+
- zhipuai

## 使用说明
1. 安装依赖：
```bash
pip install zhipuai
```

2. 配置API密钥：
在`account/web_accounts.json`中配置智谱AI的API密钥：
```json
{
    "zhipu": {
        "api_key": "your_api_key_here"
    }
}
```

## 注意事项
- API密钥文件已通过.gitignore排除，请妥善保管你的密钥信息
- 建议在使用前先测试单个图片，确认效果符合预期后再进行批量处理
