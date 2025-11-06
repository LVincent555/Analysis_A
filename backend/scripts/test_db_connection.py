"""
测试数据库连接和查看数据文件
"""
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.database import test_connection, DB_HOST, DB_PORT, DB_NAME
from app.config import DATA_DIR, FILE_PATTERN
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """测试数据库连接和数据文件"""
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    print(f"数据库地址: {DB_HOST}:{DB_PORT}")
    print(f"数据库名称: {DB_NAME}")
    print()
    
    # 测试连接
    if test_connection():
        print("✅ 数据库连接成功！")
    else:
        print("❌ 数据库连接失败！请检查配置")
        print("提示：请确保 backend/.env 文件中配置了正确的数据库密码")
        return
    
    print()
    print("=" * 60)
    print("数据文件检查")
    print("=" * 60)
    print(f"数据目录: {DATA_DIR}")
    
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return
    
    files = sorted(data_dir.glob(FILE_PATTERN))
    print(f"找到 {len(files)} 个数据文件:\n")
    
    for i, file in enumerate(files, 1):
        file_size = file.stat().st_size / 1024 / 1024  # MB
        print(f"{i:3d}. {file.name:40s} ({file_size:6.2f} MB)")
    
    print()
    print("=" * 60)
    print("准备就绪！可以运行 import_data.bat 开始导入数据")
    print("=" * 60)


if __name__ == "__main__":
    main()
