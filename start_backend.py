#!/usr/bin/env python3
"""
股票分析系统 - 后端启动脚本
跨平台启动脚本，自动检查和安装依赖
"""

import os
import sys
import subprocess
import platform

def print_header():
    """打印启动信息"""
    print("=" * 50)
    print("🚀 启动股票分析系统 - 后端服务")
    print("=" * 50)
    print()

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")

def check_dependencies():
    """检查是否需要安装依赖"""
    try:
        import fastapi
        print("✓ 依赖已安装")
        return False
    except ImportError:
        print("⚠ 需要安装依赖")
        return True

def install_dependencies():
    """安装Python依赖"""
    print("\n正在安装Python依赖...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    requirements_file = os.path.join(backend_dir, 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print(f"❌ 错误: 找不到 {requirements_file}")
        sys.exit(1)
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
        print("✓ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        sys.exit(1)

def start_backend():
    """启动后端服务"""
    print("\n" + "=" * 50)
    print("🌟 启动后端服务器...")
    print("=" * 50)
    
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    if not os.path.exists(backend_dir):
        print(f"❌ 错误: 找不到backend目录: {backend_dir}")
        sys.exit(1)
    
    # 切换到backend目录
    os.chdir(backend_dir)
    
    print(f"\n📍 工作目录: {os.getcwd()}")
    print(f"🌐 API地址: http://localhost:8000")
    print(f"📚 API文档: http://localhost:8000/docs")
    print(f"\n💡 按 Ctrl+C 停止服务器")
    print("=" * 50)
    print()
    
    try:
        # 启动uvicorn服务器
        subprocess.run([
            sys.executable, '-m', 'uvicorn',
            'app.main:app',
            '--reload',
            '--host', '0.0.0.0',
            '--port', '8000'
        ])
    except KeyboardInterrupt:
        print("\n\n✓ 后端服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print_header()
    check_python_version()
    
    if check_dependencies():
        install_dependencies()
    
    start_backend()

if __name__ == '__main__':
    main()
