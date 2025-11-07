#!/usr/bin/env python3
"""
股票分析系统 - 前端启动脚本
跨平台启动脚本，自动检查和安装依赖
"""

import os
import sys
import subprocess
import shutil
import platform

def print_header():
    """打印启动信息"""
    print("=" * 50)
    print("🚀 启动股票分析系统 - 前端应用")
    print("=" * 50)
    print()

def check_node_installed():
    """检查Node.js是否安装"""
    if shutil.which('node') is None:
        print("❌ 错误: 未找到Node.js")
        print("   请先安装Node.js (推荐版本 16+)")
        print("   下载地址: https://nodejs.org/")
        sys.exit(1)
    
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"✓ Node.js版本: {version}")
    except Exception as e:
        print(f"❌ 无法获取Node.js版本: {e}")
        sys.exit(1)

def check_npm_installed():
    """检查npm是否安装"""
    npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
    
    if shutil.which(npm_cmd) is None:
        print("❌ 错误: 未找到npm")
        print("   npm通常随Node.js一起安装")
        sys.exit(1)
    
    try:
        result = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True, shell=True)
        version = result.stdout.strip()
        print(f"✓ npm版本: {version}")
    except Exception as e:
        print(f"⚠ 无法获取npm版本，但将继续尝试: {e}")
        # 不退出，继续尝试

def check_dependencies():
    """检查是否需要安装依赖"""
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    node_modules = os.path.join(frontend_dir, 'node_modules')
    
    if not os.path.exists(node_modules):
        print("⚠ 需要安装依赖")
        return True
    
    print("✓ 依赖已安装")
    return False

def install_dependencies():
    """安装前端依赖"""
    print("\n正在安装前端依赖...")
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    
    if not os.path.exists(frontend_dir):
        print(f"❌ 错误: 找不到frontend目录: {frontend_dir}")
        sys.exit(1)
    
    try:
        npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
        subprocess.check_call([npm_cmd, 'install'], cwd=frontend_dir, shell=True)
        print("✓ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        sys.exit(1)

def start_frontend():
    """启动前端服务"""
    print("\n" + "=" * 50)
    print("🌟 启动前端开发服务器...")
    print("=" * 50)
    
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    
    if not os.path.exists(frontend_dir):
        print(f"❌ 错误: 找不到frontend目录: {frontend_dir}")
        sys.exit(1)
    
    print(f"\n📍 工作目录: {frontend_dir}")
    print(f"🌐 应用地址: http://localhost:3000")
    print(f"\n💡 浏览器将自动打开应用")
    print(f"💡 按 Ctrl+C 停止服务器")
    print("=" * 50)
    print()
    
    try:
        npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
        subprocess.run([npm_cmd, 'start'], cwd=frontend_dir, shell=True)
    except KeyboardInterrupt:
        print("\n\n✓ 前端服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print_header()
    check_node_installed()
    check_npm_installed()
    
    if check_dependencies():
        install_dependencies()
    
    start_frontend()

if __name__ == '__main__':
    main()
