#!/usr/bin/env python3
"""
清理Git历史中的node_modules和Python包
警告：这会重写Git历史！
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """运行命令"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def check_git():
    """检查是否是Git仓库"""
    success, _, _ = run_command('git rev-parse --git-dir')
    return success

def backup_reminder():
    """备份提醒"""
    print("=" * 70)
    print("⚠️  警告：清理Git历史")
    print("=" * 70)
    print()
    print("此操作将：")
    print("  1. 从Git历史中删除node_modules和venv的所有记录")
    print("  2. 重写Git历史（不可逆）")
    print("  3. 如果已push到远程，需要强制推送")
    print()
    print("⚠️  强烈建议先备份：")
    print("     cp -r .git .git.backup")
    print()
    
    response = input("是否继续？(输入 YES 继续): ").strip()
    return response == "YES"

def clean_git_cache():
    """清理Git缓存"""
    print("\n📦 清理Git缓存...")
    
    # 要清理的路径
    patterns = [
        'frontend/node_modules/',
        'backend/venv/',
        'backend/__pycache__/',
        '**/__pycache__/',
        '*.pyc',
        '.Python',
    ]
    
    for pattern in patterns:
        print(f"  删除: {pattern}")
        run_command(f'git rm -rf --cached "{pattern}"', cwd='.')
    
    print("  ✓ Git缓存已清理")

def update_gitignore():
    """更新gitignore"""
    print("\n📝 更新 .gitignore...")
    
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
package-lock.json

# React
frontend/build/
frontend/.env.local
frontend/.env.development.local
frontend/.env.test.local
frontend/.env.production.local

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
!data/.gitkeep
data/data_import_state.json

# Database
*.db
*.sqlite
*.sql.backup

# Cache
backend/cache/
cache/

# Deployment specific
deploy/*.service.bak
deploy/*.conf.bak
*.sh.backup
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    print("  ✓ .gitignore 已更新")

def remove_from_history():
    """从历史中删除大文件"""
    print("\n🗑️  从Git历史中删除...")
    print("  ⏳ 这可能需要几分钟...")
    
    # 使用git filter-repo更安全（如果安装了）
    success, _, _ = run_command('which git-filter-repo')
    
    if success:
        print("  使用 git-filter-repo (推荐)...")
        patterns = [
            '--path', 'frontend/node_modules',
            '--path', 'backend/venv',
            '--path-glob', '**/__pycache__',
            '--invert-paths'
        ]
        cmd = f"git filter-repo {' '.join(patterns)}"
        success, stdout, stderr = run_command(cmd)
        if success:
            print("  ✓ 历史已清理")
        else:
            print(f"  ❌ 失败: {stderr}")
    else:
        print("  使用 git filter-branch (较慢)...")
        print("  提示：安装 git-filter-repo 更快: pip install git-filter-repo")
        
        cmd = """git filter-branch --force --index-filter \
'git rm -rf --cached --ignore-unmatch frontend/node_modules backend/venv' \
--prune-empty --tag-name-filter cat -- --all"""
        
        success, stdout, stderr = run_command(cmd)
        if success:
            print("  ✓ 历史已清理")
        else:
            print(f"  ❌ 失败: {stderr}")

def gc_and_cleanup():
    """垃圾回收和清理"""
    print("\n🧹 清理和优化仓库...")
    
    commands = [
        'git reflog expire --expire=now --all',
        'git gc --prune=now --aggressive'
    ]
    
    for cmd in commands:
        run_command(cmd)
    
    print("  ✓ 仓库已优化")

def show_size():
    """显示仓库大小"""
    success, stdout, _ = run_command('du -sh .git')
    if success:
        size = stdout.strip().split()[0]
        print(f"\n📊 .git 目录大小: {size}")

def main():
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print()
    
    # 检查Git
    if not check_git():
        print("❌ 错误：当前目录不是Git仓库")
        sys.exit(1)
    
    # 显示当前大小
    print("📊 清理前：")
    show_size()
    
    # 备份提醒
    if not backup_reminder():
        print("\n❌ 操作已取消")
        sys.exit(0)
    
    print("\n" + "=" * 70)
    print("开始清理...")
    print("=" * 70)
    
    # 更新gitignore
    update_gitignore()
    
    # 清理缓存
    clean_git_cache()
    
    # 提交gitignore
    print("\n💾 提交 .gitignore...")
    run_command('git add .gitignore')
    run_command('git commit -m "chore: 更新 .gitignore，排除node_modules和venv"')
    
    # 询问是否清理历史
    print("\n⚠️  是否从Git历史中彻底删除这些文件？")
    print("   （如果仓库很大或历史很长，建议执行）")
    response = input("清理历史？(y/n): ").strip().lower()
    
    if response == 'y':
        remove_from_history()
        gc_and_cleanup()
    
    # 显示清理后大小
    print("\n📊 清理后：")
    show_size()
    
    print("\n" + "=" * 70)
    print("✅ 清理完成！")
    print("=" * 70)
    print()
    print("📝 下一步：")
    print("  1. 检查仓库状态: git status")
    print("  2. 如果已推送到远程，需要强制推送:")
    print("     git push origin main --force")
    print("     ⚠️  警告：这会覆盖远程历史！")
    print()
    print("💡 提示：")
    print("  - 确保团队成员已备份")
    print("  - 通知团队成员重新clone仓库")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
