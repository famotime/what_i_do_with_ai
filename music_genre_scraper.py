"""使用Playwright+AgentQL自动化爬取所有音乐风格详情信息（通过卡片div点击展示详情）"""

import csv
import os
from pathlib import Path
import json
import agentql
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

URL = "https://music.molin.tech/"

GENRE_CARD_QUERY = """
{
    music_styles(limit: 10)[]
}
"""

DETAIL_QUERY = """
{
    music_styles[]{
        genre_name(音乐风格)
        genre_name_cn(中文翻译)
        origin(来源)
        features(特点)
        instruments(乐器)
        performance_style(演奏形式)
        emotion(适合表达的情感)
        bpm_range(推荐BPM范围)
    }
}
"""

def main(output_dir, max_count=None):
    api_key = os.getenv("AGENTQL_API_KEY")
    if not api_key:
        raise ValueError("请在.env文件中设置AGENTQL_API_KEY")

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        page = agentql.wrap(browser.new_page())
        page.goto(URL)

        # 定位所有风格卡片div
        genre_cards = page.query_elements(GENRE_CARD_QUERY)
        print(genre_cards)
        cards = genre_cards.music_styles  # 获取music_styles数组
        count = len(cards) or 0  # 如果count为None，则使用0
        if max_count is not None:
            count = min(count, max_count)
        for i in range(count):
            print(f"正在点击第{i+1}/{count}个风格卡片...")
            card = cards[i]
            # print(card)
            if card is None:
                print(f"警告：第{i+1}个风格卡片未找到，跳过")
                continue
            card.click()
            page.wait_for_timeout(100)  # 等待详情内容加载

        # 获取所有音乐风格详情
        detail = page.query_data(DETAIL_QUERY)

        # 保存为JSON
        output_file = output_dir / "music_genre_details.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        print(f"所有风格详情已保存到: {output_file}")

        # 保存为CSV
        output_file = output_dir / "music_genre_details.csv"
        # 定义表头映射
        headers_map = {
            "genre_name": "音乐风格",
            "genre_name_cn": "中文翻译",
            "origin": "来源",
            "features": "特点",
            "instruments": "乐器",
            "performance_style": "演奏形式",
            "emotion": "适合表达的情感",
            "bpm_range": "推荐BPM范围"
        }
        with open(output_file, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            # 写入中文表头
            writer.writerow(headers_map.values())
            # 写入数据行
            for style in detail["music_styles"]:
                writer.writerow(style.values())
        print(f"所有风格详情已保存到: {output_file}")

if __name__ == "__main__":
    output_dir = "output"
    main(output_dir, max_count=None)
