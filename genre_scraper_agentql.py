"""使用Playwright+AgentQL自动化爬取所有音乐风格详情信息：
1. 获取所有音乐风格卡片；
2. 通过卡片点击展示详情；
3. 获取所有音乐风格详情；
4. 保存为JSON和CSV文件。

支持设置每个批次的数量，获取所有音乐卡片后，如果数量大于设置的数量，则分批获取：
每批先获取设置数量的卡片，然后点击卡片展示详情，再获取详情；再次点击这一批的卡片关闭详情，再获取下一批次。
"""

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

def save_to_json(data, output_file):
    """将数据保存为JSON文件

    Args:
        data: 要保存的数据
        output_file: 输出文件路径
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"music_styles": data}, f, ensure_ascii=False, indent=2)
    print(f"\n所有风格详情已保存到: {output_file}")

def save_to_csv(data, output_file):
    """将数据保存为CSV文件

    Args:
        data: 要保存的数据
        output_file: 输出文件路径
    """
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
        writer.writerow(headers_map.values())
        for style in data:
            writer.writerow(style.values())
    print(f"所有风格详情已保存到: {output_file}")

def process_batch(page, cards, start_idx, batch_size):
    """处理一批音乐风格卡片

    Args:
        page: Playwright页面对象
        cards: 所有音乐风格卡片列表
        start_idx: 起始索引
        batch_size: 批次大小

    Returns:
        list: 当前批次处理的所有音乐风格详情
    """
    end_idx = min(start_idx + batch_size, len(cards))
    batch_cards = cards[start_idx:end_idx]

    # 点击当前批次的所有卡片
    for i, card in enumerate(batch_cards):
        try:
            print(f"正在点击第{start_idx + i + 1}/{len(cards)}个风格卡片...")
            card.click()
            page.wait_for_timeout(200)  # 增加等待时间确保详情加载完成
        except Exception as e:
            print(f"警告：点击第{start_idx + i + 1}个风格卡片时出错: {str(e)}")
            continue

    # 获取当前批次的详情
    try:
        detail = page.query_data(DETAIL_QUERY)
        return detail.get("music_styles", [])
    except Exception as e:
        print(f"警告：获取第{start_idx + 1}到{end_idx}个风格详情时出错: {str(e)}")
        return []
    finally:
        # 关闭当前批次的所有卡片详情
        for card in batch_cards:
            try:
                card.click()
                page.wait_for_timeout(100)
            except Exception as e:
                print(f"警告：关闭卡片详情时出错: {str(e)}")
                continue

def main(output_dir, batch_size=5, max_count=None):
    api_key = os.getenv("AGENTQL_API_KEY")
    if not api_key:
        raise ValueError("请在.env文件中设置AGENTQL_API_KEY")

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    all_genres = []

    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        page = agentql.wrap(browser.new_page())
        page.goto(URL)
        page.wait_for_timeout(1000)  # 等待页面完全加载

        # 定位所有风格卡片div
        genre_cards = page.query_elements(GENRE_CARD_QUERY)
        cards = genre_cards.music_styles
        total_count = len(cards) or 0

        if max_count is not None:
            total_count = min(total_count, max_count)
            cards = cards[:total_count]

        print(f"总共找到{total_count}个音乐风格卡片，每批处理{batch_size}个")

        # 分批处理所有卡片
        for start_idx in range(0, total_count, batch_size):
            print(f"\n开始处理第{start_idx//batch_size + 1}批，共{(total_count + batch_size - 1)//batch_size}批")
            batch_genres = process_batch(page, cards, start_idx, batch_size)
            all_genres.extend(batch_genres)
            print(f"第{start_idx//batch_size + 1}批处理完成，当前已获取{len(all_genres)}个风格详情")
            page.wait_for_timeout(500)  # 批次之间稍作等待

        # 保存数据
        save_to_json(all_genres, output_dir / "music_genre_details.json")
        save_to_csv(all_genres, output_dir / "music_genre_details.csv")

if __name__ == "__main__":
    output_dir = "output"
    main(output_dir, batch_size=3, max_count=None)
