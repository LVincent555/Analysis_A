#!/usr/bin/env python3
"""
DPRS Review 初始化脚本

在目标项目中创建 review 目录结构，并复制模板文件。

用法:
    python init.py /path/to/project
    python init.py /path/to/project --name docs/review
    python init.py /path/to/project --no-meta  # 不复制 META 内容
"""

import argparse
import shutil
import sys
from pathlib import Path

# 脚本所在目录（套件根目录）
TOOLKIT_DIR = Path(__file__).parent.resolve()


def create_directory_structure(target_dir: Path, include_meta: bool = True) -> None:
    """创建 review 目录结构"""

    # 核心目录
    directories = ["PRB", "SUG", "DEC", "RES"]
    if include_meta:
        directories.insert(0, "META")

    for dir_name in directories:
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

    print(f"✓ 创建目录结构: {', '.join(directories)}")


def copy_meta_files(target_dir: Path) -> None:
    """复制 META 规范文件"""

    meta_source = TOOLKIT_DIR / "META"
    meta_target = target_dir / "META"

    if not meta_source.exists():
        print("⚠ 警告: 找不到 META 源目录，跳过复制")
        return

    files_copied = []
    for src_file in meta_source.glob("*.md"):
        dst_file = meta_target / src_file.name
        if not dst_file.exists():
            shutil.copy2(src_file, dst_file)
            files_copied.append(src_file.name)

    if files_copied:
        print(f"✓ 复制 META 文件: {', '.join(files_copied)}")
    else:
        print("✓ META 文件已存在，跳过复制")


def copy_templates(target_dir: Path) -> None:
    """复制模板文件到 templates 子目录（可选）"""

    templates_source = TOOLKIT_DIR / "templates"
    templates_target = target_dir / "templates"

    if not templates_source.exists():
        print("⚠ 警告: 找不到 templates 源目录，跳过复制")
        return

    templates_target.mkdir(parents=True, exist_ok=True)

    files_copied = []
    for src_file in templates_source.glob("*.md"):
        dst_file = templates_target / src_file.name
        if not dst_file.exists():
            shutil.copy2(src_file, dst_file)
            files_copied.append(src_file.name)

    if files_copied:
        print(f"✓ 复制模板文件: {', '.join(files_copied)}")
    else:
        print("✓ 模板文件已存在，跳过复制")


def main():
    parser = argparse.ArgumentParser(
        description="在目标项目中初始化 DPRS Review 目录结构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python init.py /path/to/my-project
  python init.py /path/to/my-project --name docs/review
  python init.py . --no-templates
        """
    )

    parser.add_argument(
        "target",
        type=str,
        help="目标项目路径"
    )

    parser.add_argument(
        "--name", "-n",
        type=str,
        default="review",
        help="review 目录名称（默认: review）"
    )

    parser.add_argument(
        "--no-meta",
        action="store_true",
        help="不复制 META 规范文件"
    )

    parser.add_argument(
        "--no-templates",
        action="store_true",
        help="不复制 templates 模板文件"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制覆盖已存在的文件"
    )

    args = parser.parse_args()

    # 解析目标路径
    target_base = Path(args.target).resolve()
    if not target_base.exists():
        print(f"✗ 错误: 目标路径不存在: {target_base}")
        sys.exit(1)

    target_dir = target_base / args.name

    print(f"\n📁 DPRS Review 初始化")
    print(f"   目标路径: {target_dir}\n")

    # 检查是否已存在
    if target_dir.exists() and not args.force:
        print(f"⚠ 目录已存在: {target_dir}")
        response = input("是否继续？(y/N): ").strip().lower()
        if response != 'y':
            print("已取消")
            sys.exit(0)

    # 创建目录结构
    include_meta = not args.no_meta
    create_directory_structure(target_dir, include_meta=include_meta)

    # 复制 META 文件
    if include_meta:
        copy_meta_files(target_dir)

    # 复制模板文件
    if not args.no_templates:
        copy_templates(target_dir)

    print(f"\n✅ 初始化完成！")
    print(f"\n下一步:")
    print(f"  1. 编辑 {target_dir}/META/INDEX.md 添加项目信息")
    print(f"  2. 使用 templates/ 中的模板创建新文档")
    print(f"  3. 遵循 PRB → SUG → DEC → RES 流程")


if __name__ == "__main__":
    main()
