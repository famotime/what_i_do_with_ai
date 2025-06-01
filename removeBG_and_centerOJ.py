"""
将指定目录或指定的图像文件，去除背景后识别主体并使其居中，保存为背景透明的png文件
"""

import io
import sys
from pathlib import Path
from PIL import Image, ImageChops
import numpy as np

try:
    from rembg import remove
except ImportError as e:
    print("rembg库导入失败，可能的解决方案：")
    print("1. 安装Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    print("2. 重新安装onnxruntime: pip uninstall onnxruntime && pip install onnxruntime")
    print("3. 使用conda安装: conda install -c conda-forge onnxruntime")
    print(f"详细错误: {e}")
    sys.exit(1)


def find_object_bounds(image):
    """
    找到图像中非透明区域的边界
    返回: (left, top, right, bottom)
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    alpha = image.split()[-1]
    alpha_array = np.array(alpha)
    non_transparent = np.where(alpha_array > 0)
    if len(non_transparent[0]) == 0:
        return 0, 0, image.width, image.height
    top = non_transparent[0].min()
    bottom = non_transparent[0].max() + 1
    left = non_transparent[1].min()
    right = non_transparent[1].max() + 1
    return left, top, right, bottom


def center_object(image, target_size=None, fit_mode='contain', padding_ratio=0.1):
    """
    将对象居中，避免裁剪
    Args:
        image: PIL图像对象
        target_size: 目标尺寸 (width, height)，如果为None则使用原图片尺寸
        fit_mode: 'contain' 保持完整对象不裁剪, 'cover' 填满画布可能裁剪, 'exact' 强制尺寸可能变形
        padding_ratio: 边距比例，0.1表示10%的边距
    Returns:
        居中后的PIL图像对象
    """
    left, top, right, bottom = find_object_bounds(image)
    cropped = image.crop((left, top, right, bottom))
    obj_width = right - left
    obj_height = bottom - top

    print(f"  对象尺寸: {obj_width}x{obj_height}")

    if target_size is None:
        # 使用原图片尺寸
        canvas_width = image.width
        canvas_height = image.height
        final_obj = cropped
        print(f"  使用原图尺寸: {canvas_width}x{canvas_height}")
    else:
        canvas_width, canvas_height = target_size
        print(f"  目标画布尺寸: {canvas_width}x{canvas_height}")

        if fit_mode == 'contain':
            # 保持对象完整，可能会有空白区域
            # 计算可用空间（扣除边距）
            available_width = canvas_width * (1 - 2 * padding_ratio)
            available_height = canvas_height * (1 - 2 * padding_ratio)

            # 计算缩放比例，保持宽高比
            scale_w = available_width / obj_width if obj_width > 0 else 1
            scale_h = available_height / obj_height if obj_height > 0 else 1
            scale = min(scale_w, scale_h, 1.0)  # 不放大，只缩小

            new_width = max(1, int(obj_width * scale))
            new_height = max(1, int(obj_height * scale))
            final_obj = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"  缩放后尺寸: {new_width}x{new_height}, 缩放比例: {scale:.2f}")

        elif fit_mode == 'cover':
            # 填满画布，可能会裁剪对象
            scale_w = canvas_width / obj_width if obj_width > 0 else 1
            scale_h = canvas_height / obj_height if obj_height > 0 else 1
            scale = max(scale_w, scale_h)

            new_width = max(1, int(obj_width * scale))
            new_height = max(1, int(obj_height * scale))
            resized = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 裁剪到画布大小
            left_crop = max(0, (new_width - canvas_width) // 2)
            top_crop = max(0, (new_height - canvas_height) // 2)
            right_crop = min(new_width, left_crop + canvas_width)
            bottom_crop = min(new_height, top_crop + canvas_height)

            final_obj = resized.crop((left_crop, top_crop, right_crop, bottom_crop))
            print(f"  缩放后尺寸: {new_width}x{new_height}, 裁剪后: {final_obj.width}x{final_obj.height}")
        else:  # exact
            # 强制拉伸到目标尺寸
            final_obj = cropped.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            print(f"  强制拉伸到: {canvas_width}x{canvas_height}")

    # 创建透明画布
    centered_image = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

    # 计算粘贴位置（居中）
    paste_x = (canvas_width - final_obj.width) // 2
    paste_y = (canvas_height - final_obj.height) // 2

    print(f"  粘贴位置: ({paste_x}, {paste_y})")

    # 粘贴对象
    centered_image.paste(final_obj, (paste_x, paste_y), final_obj)

    return centered_image


def remove_background_by_color(image, target_color=(0, 0, 0), tolerance=30, edge_smooth=True):
    """
    基于颜色容限去除背景
    Args:
        image: PIL图像对象
        target_color: 目标背景颜色 (R, G, B)，默认为黑色
        tolerance: 颜色容限 (0-255)，数值越大容限越大
        edge_smooth: 是否对边缘进行平滑处理
    Returns:
        去除背景后的RGBA图像
    """
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # 转换为numpy数组处理
    img_array = np.array(image)
    height, width, channels = img_array.shape

    # 计算每个像素与目标颜色的欧几里得距离
    target_color = np.array(target_color)
    diff = img_array - target_color
    distances = np.sqrt(np.sum(diff ** 2, axis=2))

    # 创建alpha通道
    alpha = np.ones((height, width), dtype=np.uint8) * 255

    if edge_smooth and tolerance > 0:
        # 平滑边缘：在容限范围内使用渐变透明度
        smooth_zone = tolerance * 0.3  # 平滑区域为容限的30%

        # 完全透明区域
        alpha[distances <= tolerance - smooth_zone] = 0

        # 渐变区域
        gradient_mask = (distances > tolerance - smooth_zone) & (distances <= tolerance + smooth_zone)
        if np.any(gradient_mask):
            gradient_distances = distances[gradient_mask]
            # 计算渐变透明度
            gradient_alpha = ((gradient_distances - (tolerance - smooth_zone)) / (2 * smooth_zone)) * 255
            gradient_alpha = np.clip(gradient_alpha, 0, 255).astype(np.uint8)
            alpha[gradient_mask] = gradient_alpha
    else:
        # 简单的阈值处理
        alpha[distances <= tolerance] = 0

    # 创建RGBA图像
    rgba_array = np.zeros((height, width, 4), dtype=np.uint8)
    rgba_array[:, :, :3] = img_array
    rgba_array[:, :, 3] = alpha

    return Image.fromarray(rgba_array, 'RGBA')


def calculate_color_distance(color1, color2):
    """计算两个颜色之间的欧几里得距离"""
    return np.sqrt(sum([(c1 - c2) ** 2 for c1, c2 in zip(color1, color2)]))


def auto_detect_background_color(image, sample_size=50):
    """
    自动检测背景颜色（基于图像四个角落的像素）
    Args:
        image: PIL图像对象
        sample_size: 采样区域大小
    Returns:
        检测到的背景颜色 (R, G, B)
    """
    if image.mode != 'RGB':
        image = image.convert('RGB')

    width, height = image.size
    sample_size = min(sample_size, width // 4, height // 4)

    # 采样四个角落
    corners = [
        (0, 0, sample_size, sample_size),  # 左上
        (width - sample_size, 0, width, sample_size),  # 右上
        (0, height - sample_size, sample_size, height),  # 左下
        (width - sample_size, height - sample_size, width, height)  # 右下
    ]

    corner_colors = []
    for corner in corners:
        crop = image.crop(corner)
        # 获取该区域的主要颜色
        colors = crop.getcolors(maxcolors=256*256*256)
        if colors:
            # 选择出现最频繁的颜色
            most_common_color = max(colors, key=lambda x: x[0])[1]
            corner_colors.append(most_common_color)

    if corner_colors:
        # 计算平均颜色
        avg_color = tuple(int(sum(c[i] for c in corner_colors) / len(corner_colors)) for i in range(3))
        return avg_color

    return (0, 0, 0)  # 默认返回黑色


def remove_background_and_center(input_path, output_path, target_size=None, fit_mode='contain', padding_ratio=0.1,
                                use_color_removal=False, target_color=None, color_tolerance=30, edge_smooth=True, auto_detect_bg=False):
    """
    去除背景并将主体居中
    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        target_size: 目标尺寸 (width, height)
        fit_mode: 适应模式
        padding_ratio: 边距比例
        use_color_removal: 是否使用颜色去除而不是rembg
        target_color: 目标背景颜色 (R, G, B)，默认为黑色
        color_tolerance: 颜色容限 (0-255)
        edge_smooth: 是否对边缘进行平滑处理
        auto_detect_bg: 是否自动检测背景颜色
    """
    try:
        print(f"正在处理: {input_path.name}")

        if use_color_removal:
            # 使用颜色去除方法
            print("  使用颜色容限去除背景...")
            image = Image.open(input_path)

            if auto_detect_bg:
                detected_color = auto_detect_background_color(image)
                print(f"  自动检测的背景颜色: RGB{detected_color}")
                target_color = detected_color
            elif target_color is None:
                target_color = (0, 0, 0)  # 默认黑色

            print(f"  目标背景颜色: RGB{target_color}, 容限: {color_tolerance}")
            image = remove_background_by_color(image, target_color, color_tolerance, edge_smooth)
        else:
            # 使用rembg方法
            print("  使用AI模型去除背景...")
            with open(input_path, 'rb') as f:
                input_data = f.read()
            output_data = remove(input_data)
            image = Image.open(io.BytesIO(output_data))

        print(f"  原始尺寸: {image.width}x{image.height}")

        print("  居中处理中...")
        centered_image = center_object(image, target_size, fit_mode, padding_ratio)

        print("  保存文件中...")
        centered_image.save(output_path, 'PNG')
        print(f"✓ 处理完成: {output_path.name}\n")
    except Exception as e:
        print(f"✗ 处理 {input_path} 时出错: {str(e)}\n")


def process_single_file(input_file, output_dir=None, target_size=None, fit_mode='contain', padding_ratio=0.1,
                       use_color_removal=False, target_color=None, color_tolerance=30, edge_smooth=True, auto_detect_bg=False):
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"文件不存在: {input_path}")
        return
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    if input_path.suffix.lower() not in supported_formats:
        print(f"不支持的文件格式: {input_path}")
        return
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_no_bg_centered.png"
    else:
        output_path = input_path.parent / f"{input_path.stem}_no_bg_centered.png"
    remove_background_and_center(input_path, output_path, target_size, fit_mode, padding_ratio,
                                use_color_removal, target_color, color_tolerance, edge_smooth, auto_detect_bg)


def process_directory(input_dir, output_dir=None, target_size=None, fit_mode='contain', padding_ratio=0.1,
                     use_color_removal=False, target_color=None, color_tolerance=30, edge_smooth=True, auto_detect_bg=False):
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"目录不存在: {input_path}")
        return

    # 支持的图像格式
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    # 使用set避免重复文件
    image_files = set()
    for file_path in input_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_formats:
            image_files.add(file_path)

    # 转换为排序的列表
    image_files = sorted(list(image_files))

    if not image_files:
        print(f"在目录 {input_path} 中未找到支持的图像文件")
        return

    print(f"找到 {len(image_files)} 个图像文件")

    # 创建输出目录
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = input_path / "no_bg_centered"

    output_path.mkdir(parents=True, exist_ok=True)

    # 处理每个文件
    for i, img_file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}]", end=" ")
        output_file = output_path / f"{img_file.stem}.png"

        # 检查输出文件是否已存在
        if output_file.exists():
            print(f"跳过已存在的文件: {output_file.name}")
            continue

        remove_background_and_center(img_file, output_file, target_size, fit_mode, padding_ratio,
                                   use_color_removal, target_color, color_tolerance, edge_smooth, auto_detect_bg)


def main():
    """
    主函数 - 在这里配置你的处理参数
    """
    # ================ 配置区域 ================
    # 输入路径（可以是文件或目录）
    input_path = r".\input\icons"  # 修改为你的输入路径

    # 输出目录（可选）
    output_dir = None  # 设为 None 则在输入目录下创建子目录

    # 目标尺寸（可选，格式: (width, height)）
    target_size = None  # 例如: (512, 512) 或 None 表示自动计算

    # 适应模式：
    # 'contain' - 保持完整对象不裁剪（推荐）
    # 'cover' - 填满画布可能裁剪对象
    # 'exact' - 强制拉伸到目标尺寸
    fit_mode = 'contain'

    # 边距比例 (0.0-0.5)，0.1表示10%的边距
    padding_ratio = 0.1

    # ============ 新增：颜色去除配置 ============
    # 是否使用颜色去除（而不是AI模型rembg）
    use_color_removal = True  # 设为True启用颜色去除功能

    # 目标背景颜色 (R, G, B)，None则使用自动检测或默认黑色
    target_color = (0, 0, 0)  # 黑色，可以修改为其他颜色如 (255, 255, 255) 白色

    # 颜色容限 (0-255)，数值越大容限越大，能去除更多相近颜色
    color_tolerance = 50  # 推荐值：30-80，可根据效果调整

    # 是否对边缘进行平滑处理（减少锯齿）
    edge_smooth = True

    # 是否自动检测背景颜色（基于图像四角）
    auto_detect_bg = False  # 设为True会自动检测背景颜色

    # ========================================

    input_path_obj = Path(input_path)
    if input_path_obj.is_file():
        print(f"处理单个文件: {input_path}")
        if use_color_removal:
            print(f"使用颜色去除模式 - 目标颜色: RGB{target_color}, 容限: {color_tolerance}")
        else:
            print("使用AI模型去除背景")
        process_single_file(input_path, output_dir, target_size, fit_mode, padding_ratio,
                           use_color_removal, target_color, color_tolerance, edge_smooth, auto_detect_bg)
    elif input_path_obj.is_dir():
        print(f"处理目录: {input_path}")
        if use_color_removal:
            print(f"使用颜色去除模式 - 目标颜色: RGB{target_color}, 容限: {color_tolerance}")
        else:
            print("使用AI模型去除背景")
        process_directory(input_path, output_dir, target_size, fit_mode, padding_ratio,
                         use_color_removal, target_color, color_tolerance, edge_smooth, auto_detect_bg)
    else:
        print(f"输入路径无效: {input_path}")
        print("请在main()函数中修改 input_path 变量")


if __name__ == "__main__":
    main()
