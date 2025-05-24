"""使用Playwright自动化爬取所有音乐风格详情信息：
1. 获取所有音乐风格卡片；
2. 通过卡片点击展示详情；
3. 获取所有音乐风格详情；
4. 保存为JSON和CSV文件。
"""

import csv
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://music.molin.tech/"

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

def extract_genre_details(page, card):
    """从页面提取音乐风格详情

    Args:
        page: Playwright页面对象
        card: 当前处理的卡片元素

    Returns:
        dict: 包含音乐风格详情的字典
    """
    details = {}

    # 获取表格中的所有行
    rows = card.locator("table tbody tr").all()

    for row in rows:
        # 获取每行的标题和内容
        title = row.locator("td").first.text_content().strip()
        content = row.locator("td").last.text_content().strip()

        # 根据标题映射到对应的字段
        if title == "音乐风格":
            details["genre_name"] = content
        elif title == "中文翻译":
            details["genre_name_cn"] = content
        elif title == "来源":
            details["origin"] = content
        elif title == "特点":
            details["features"] = content
        elif title == "乐器":
            details["instruments"] = content
        elif title == "演奏形式":
            details["performance_style"] = content
        elif title == "适合表达的情感":
            details["emotion"] = content
        elif title == "推荐BPM范围":
            details["bpm_range"] = content

    return details

def main(output_dir, max_count=None):
    """主函数

    Args:
        output_dir: 输出目录路径
        max_count: 最大获取数量，None表示获取所有
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    all_genres = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_timeout(1000)  # 等待页面完全加载

        # 获取所有风格卡片
        cards = page.locator("div.cursor-pointer.hover\\:bg-gray-700").all()
        total_count = len(cards)

        # 如果设置了最大数量，则限制处理数量
        if max_count is not None:
            total_count = min(total_count, max_count)
            cards = cards[:total_count]

        print(f"总共找到{len(cards)}个音乐风格卡片，将处理{total_count}个")

        # 处理每个卡片
        for i, card in enumerate(cards, 1):
            try:
                print(f"正在处理第{i}/{total_count}个风格卡片...")
                card.click()
                page.wait_for_timeout(200)  # 等待详情加载

                # 提取详情
                genre_details = extract_genre_details(page, card)
                all_genres.append(genre_details)

                # 关闭详情
                card.click()
                page.wait_for_timeout(100)

            except Exception as e:
                print(f"警告：处理第{i}个风格卡片时出错: {str(e)}")
                continue

        browser.close()

        # 保存数据
        save_to_json(all_genres, output_dir / "music_genre_details.json")
        save_to_csv(all_genres, output_dir / "music_genre_details.csv")

if __name__ == "__main__":
    output_dir = "output"
    # 设置max_count为None获取所有，或设置具体数字进行测试
    main(output_dir, max_count=None)
