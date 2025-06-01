"""
将指定目录或指定的图像文件，按照N*N的网格，分割成多个小图像，并保存到指定目录
"""

from pathlib import Path
from PIL import Image


def split_image_to_icons(image_path: Path, output_dir: Path, grid: int):
    img = Image.open(image_path)
    w, h = img.size
    icon_w, icon_h = w // grid, h // grid
    output_dir.mkdir(parents=True, exist_ok=True)
    for i in range(grid):
        for j in range(grid):
            left = j * icon_w
            upper = i * icon_h
            right = left + icon_w
            lower = upper + icon_h
            icon = img.crop((left, upper, right, lower))
            icon_file = output_dir / f"{image_path.stem}_{i}_{j}.png"
            icon.save(icon_file, format='PNG')

def main(input_path: Path, output_dir: Path, grid: int):
    if input_path.is_file():
        split_image_to_icons(input_path, output_dir, grid)
    elif input_path.is_dir():
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp']:
            for img_file in input_path.glob(ext):
                split_image_to_icons(img_file, output_dir, grid)
    else:
        print(f"输入路径 {input_path} 无效")


if __name__ == '__main__':
    input_path = Path('../images')
    output_dir = input_path / 'icons'
    grid = 4  # 网格数N*N
    main(input_path, output_dir, grid)
