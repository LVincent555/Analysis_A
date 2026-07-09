#!/usr/bin/env python3
"""
安全的Git提交和推送脚本
使用前会检查是否有敏感文件被暴露
"""

import os
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd):
    """运行命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def check_git_installed():
    """检查Git是否安装"""
    success, _, _ = run_cmd('git --version')
    if not success:
        print("❌ Git未安装")
        return False
    print("✓ Git已安装")
    return True

def check_gitignore():
    """检查.gitignore是否正确"""
    print("\n🔍 检查.gitignore...")
    
    if not Path('.gitignore').exists():
        print("❌ .gitignore不存在")
        return False
    
    with open('.gitignore', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_patterns = [
        'node_modules/',
        'venv/',
        '.env',
        '*.pyc',
        '__pycache__/',
        'data/*.xlsx',
        'data/data_import_state.json'
    ]
    
    missing = []
    for pattern in required_patterns:
        if pattern not in content:
            missing.append(pattern)
    
    if missing:
        print("⚠ .gitignore缺少以下模式:")
        for p in missing:
            print(f"  - {p}")
        print("\n正在更新.gitignore...")
        return update_gitignore()
    
    print("✓ .gitignore配置正确")
    return True

def update_gitignore():
    """更新.gitignore"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# React
frontend-client/build/
frontend-client/.env.local
frontend-client/.env.development.local
frontend-client/.env.test.local
frontend-client/.env.production.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Excel
~$*.xlsx
*.tmp

# Logs
*.log

# Environment files
.env
*.env
!.env.example

# Data files
data/*.xlsx
data/*.xls
data/data_import_state.json
!data/.gitkeep

# Database
*.db
*.sqlite
*.sql.backup

# Cache
backend/cache/
cache/

# Build outputs
frontend-client/build/
dist/

# Deployment specific
deploy/*.service.bak
deploy/*.conf.bak
*.sh.backup
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    print("✓ .gitignore已更新")
    return True

def check_staged_files():
    """检查将要提交的文件"""
    print("\n📋 检查暂存区文件...")
    
    success, stdout, _ = run_cmd('git status --porcelain')
    if not success:
        return True
    
    # 危险文件模式
    dangerous_patterns = [
        'node_modules/',
        'venv/',
        '__pycache__/',
        '.env',
        'data_import_state.json',
        '.xlsx',
        '.pyc'
    ]
    
    lines = stdout.strip().split('\n') if stdout.strip() else []
    dangerous_files = []
    
    for line in lines:
        if len(line) < 3:
            continue
        file_path = line[3:].strip()
        for pattern in dangerous_patterns:
            if pattern in file_path:
                dangerous_files.append(file_path)
                break
    
    if dangerous_files:
        print("\n⚠️  警告：发现可能不应该提交的文件：")
        for f in dangerous_files[:10]:  # 只显示前10个
            print(f"  - {f}")
        if len(dangerous_files) > 10:
            print(f"  ... 还有 {len(dangerous_files) - 10} 个文件")
        print("\n建议：检查.gitignore是否正确")
        return False
    
    print("✓ 暂存区文件安全")
    return True

def clear_git_cache():
    """清理Git缓存"""
    print("\n🧹 清理Git缓存...")
    
    # 删除已跟踪但应该被忽略的文件
    patterns_to_remove = [
        'frontend-client/node_modules',
        'backend/venv',
        'backend/__pycache__',
        'data/*.xlsx',
        'data/data_import_state.json'
    ]
    
    for pattern in patterns_to_remove:
        run_cmd(f'git rm -rf --cached "{pattern}" 2>/dev/null')
    
    print("✓ Git缓存已清理")

def show_status():
    """显示Git状态"""
    print("\n📊 当前Git状态:")
    print("=" * 60)
    os.system('git status')
    print("=" * 60)

def commit_and_push():
    """提交并推送"""
    print("\n💾 准备提交...")
    
    # 显示将要提交的文件
    print("\n将要提交的文件：")
    os.system('git status --short')
    print()
    
    # 询问提交信息
    commit_msg = input("📝 输入提交信息 (回车使用默认): ").strip()
    if not commit_msg:
        commit_msg = "chore: 更新代码，准备部署到Linux服务器"
    
    # 添加所有更改
    print("\n添加文件...")
    run_cmd('git add .')
    
    # 再次检查
    if not check_staged_files():
        response = input("\n⚠️  发现可能的问题，是否继续？(y/n): ").strip().lower()
        if response != 'y':
            print("❌ 提交已取消")
            return False
    
    # 提交
    print(f"\n提交: {commit_msg}")
    success, stdout, stderr = run_cmd(f'git commit -m "{commit_msg}"')
    
    if not success:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            print("✓ 没有需要提交的更改")
            return True
        else:
            print(f"❌ 提交失败: {stderr}")
            return False
    
    print("✓ 提交成功")
    
    # 询问是否推送
    response = input("\n🚀 是否推送到远程？(y/n): ").strip().lower()
    if response != 'y':
        print("⏭️  跳过推送")
        return True
    
    # 获取当前分支
    success, branch, _ = run_cmd('git branch --show-current')
    if not success:
        branch = 'main'
    else:
        branch = branch.strip()
    
    print(f"\n推送到远程分支: {branch}")
    success, stdout, stderr = run_cmd(f'git push origin {branch}')
    
    if success:
        print("✓ 推送成功")
        return True
    else:
        print(f"❌ 推送失败: {stderr}")
        if "rejected" in stderr:
            print("\n💡 提示：可能需要先拉取远程更新:")
            print(f"   git pull origin {branch}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Git提交和推送脚本")
    print("=" * 60)
    
    # 切换到项目根目录
    os.chdir(Path(__file__).parent)
    
    # 检查Git
    if not check_git_installed():
        sys.exit(1)
    
    # 检查是否是Git仓库
    success, _, _ = run_cmd('git rev-parse --git-dir')
    if not success:
        print("❌ 当前目录不是Git仓库")
        sys.exit(1)
    
    # 检查.gitignore
    if not check_gitignore():
        response = input("\n是否继续？(y/n): ").strip().lower()
        if response != 'y':
            sys.exit(0)
    
    # 清理Git缓存
    clear_git_cache()
    
    # 显示状态
    show_status()
    
    # 提交和推送
    if commit_and_push():
        print("\n" + "=" * 60)
        print("✅ 完成！")
        print("=" * 60)
        print("\n📝 下一步（在服务器上）：")
        print("   1. SSH登录服务器")
        print("   2. cd /root/stock_analysis_app")
        print("   3. git pull origin main")
        print("   4. python3 deploy_smart.py dev")
        print()
    else:
        print("\n❌ 操作失败")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
