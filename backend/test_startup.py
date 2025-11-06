"""
测试启动检查
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.core import run_startup_checks

if __name__ == "__main__":
    print("\n测试启动检查...\n")
    result = run_startup_checks()
    print(f"\n启动检查结果: {'通过' if result else '失败'}\n")
