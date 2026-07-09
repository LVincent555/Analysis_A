#!/usr/bin/env python3
"""
股票分析系统 - 一键启动脚本
同时启动前端和后端服务
"""

import os
import sys
import subprocess
import time
import platform

def print_header():
    """打印启动信息"""
    print("=" * 60)
    print("🚀 股票分析系统 - 一键启动")
    print("=" * 60)
    print()

def start_service(script_name, service_name):
    """启动服务"""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ 错误: 找不到启动脚本 {script_name}")
        return None
    
    print(f"▶ 启动{service_name}...")
    try:
        # 在新窗口中启动服务
        is_windows = platform.system() == 'Windows'
        
        if is_windows:
            # Windows: 使用start命令在新窗口中启动
            process = subprocess.Popen(
                f'start "股票分析-{service_name}" python "{script_path}"',
                shell=True
            )
        else:
            # Linux/Mac: 在后台启动
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print(f"✓ {service_name}启动中...")
        return process
    except Exception as e:
        print(f"❌ {service_name}启动失败: {e}")
        return None

def main():
    """主函数"""
    print_header()
    
    print("📋 启动顺序:")
    print("   1️⃣  后端服务 (http://localhost:8000)")
    print("   2️⃣  前端应用 (http://localhost:3000)")
    print()
    print("=" * 60)
    print()
    
    # 启动后端
    backend_process = start_service('start_backend.py', '后端')
    if backend_process:
        print("⏳ 等待后端服务启动...")
        time.sleep(3)
    
    # 启动前端
    frontend_process = start_service('start_frontend.py', '前端')
    if frontend_process:
        print("⏳ 等待前端服务启动...")
        time.sleep(2)
    
    print()
    print("=" * 60)
    print("✅ 所有服务已启动!")
    print()
    print("📌 服务地址:")
    print("   🔧 后端API: http://localhost:8000")
    print("   📚 API文档: http://localhost:8000/docs")
    print("   🌐 前端应用: http://localhost:3000")
    print()
    print("💡 提示:")
    print("   - 前端和后端在独立窗口中运行")
    print("   - 关闭对应窗口可停止服务")
    print("   - 或在窗口中按 Ctrl+C 停止")
    print("=" * 60)

if __name__ == '__main__':
    main()
