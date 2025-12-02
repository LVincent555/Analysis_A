#!/usr/bin/env python3
"""
最终整理脚本
1. 移动工具脚本到deploy/scripts
2. 移动所有MD文档到docs（除了README.md）
"""

import shutil
from pathlib import Path

class FinalOrganizer:
    """最终整理器"""
    
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.moves = []
    
    def move_utility_scripts(self):
        """移动工具脚本到deploy/scripts"""
        print("\n📦 移动工具脚本到 deploy/scripts/...")
        
        # 要移动的工具脚本
        utility_scripts = [
            'cleanup_and_organize.py',
            'cleanup_old_files.py', 
            'cleanup_redundant_files.py',
            'reorganize_project.py',
            'final_organize.py'  # 自己也移动过去
        ]
        
        for script in utility_scripts:
            source = self.root / script
            if source.exists():
                target = self.root / 'deploy' / 'scripts' / script
                if not target.exists():
                    shutil.move(str(source), str(target))
                    print(f"  ✓ {script} -> deploy/scripts/")
                    self.moves.append((script, 'deploy/scripts/'))
    
    def move_docs_to_docs(self):
        """移动MD文档到docs（除了README.md）"""
        print("\n📚 移动文档到 docs/...")
        
        # 获取根目录所有md文件
        md_files = list(self.root.glob('*.md'))
        
        for md_file in md_files:
            # 跳过README.md
            if md_file.name == 'README.md':
                continue
            
            target = self.root / 'docs' / md_file.name
            if not target.exists():
                shutil.move(str(md_file), str(target))
                print(f"  ✓ {md_file.name} -> docs/")
                self.moves.append((md_file.name, 'docs/'))
    
    def update_docs_readme(self):
        """更新docs/README.md"""
        print("\n📝 更新 docs/README.md...")
        
        readme_path = self.root / 'docs' / 'README.md'
        
        # 添加新移动过来的文档
        additional_docs = """

### 🐳 Docker部署文档
- `README_DEPLOY.md` - Docker部署完整指南

### 📋 其他文档
根目录的所有文档已整理到此目录。
"""
        
        if readme_path.exists():
            content = readme_path.read_text(encoding='utf-8')
            if 'README_DEPLOY.md' not in content:
                content += additional_docs
                readme_path.write_text(content, encoding='utf-8')
                print("  ✓ 已更新 docs/README.md")
    
    def create_scripts_list(self):
        """创建脚本清单"""
        print("\n📋 创建脚本清单...")
        
        scripts_doc = """# 🔧 项目脚本清单

## 📍 启动脚本（根目录）

| 脚本 | 说明 | 用途 |
|------|------|------|
| `start_backend.py` | 启动后端 | 开发/测试 |
| `start_frontend.py` | 启动前端 | 开发/测试 |
| `start_all.py` | 一键启动所有 | 开发/测试 |

## 🔧 工具脚本（deploy/scripts/）

| 脚本 | 说明 | 用途 |
|------|------|------|
| `deploy_smart.py` | 智能部署 | 部署 |
| `service_manager.py` | 服务管理 | 运维 |
| `git_commit_push.py` | Git提交 | 开发 |
| `clean_git_history.py` | Git历史清理 | 维护 |
| `prepare_linux_deploy.py` | 部署检查 | 部署 |
| `setup_linux.sh` | Linux环境配置 | 部署 |
| `cleanup_and_organize.py` | 项目清理 | 维护 |
| `cleanup_old_files.py` | 清理旧文件 | 维护 |
| `cleanup_redundant_files.py` | 清理冗余文件 | 维护 |
| `reorganize_project.py` | 项目重组 | 维护 |

## ⚡ 快捷命令（根目录 .sh）

| 命令 | 说明 | 等同于 |
|------|------|--------|
| `./service.sh` | 服务管理 | `python3 deploy/scripts/service_manager.py` |
| `./deploy.sh` | 智能部署 | `python3 deploy/scripts/deploy_smart.py` |
| `./start.sh` | 启动服务 | `service_manager.py start all` |
| `./stop.sh` | 停止服务 | `service_manager.py stop all` |
| `./restart.sh` | 重启服务 | `service_manager.py restart all` |
| `./status.sh` | 查看状态 | `service_manager.py status` |
| `./logs.sh` | 查看日志 | `service_manager.py logs` |

## 🎯 使用建议

### 开发阶段
- 使用 `start_*.py` 启动服务
- 使用 `test_backend.py` 测试后端

### 部署阶段
- 使用 `deploy/scripts/deploy_smart.py` 智能部署
- 使用 `deploy/scripts/service_manager.py` 管理服务

### 维护阶段
- 使用 `.sh` 快捷命令日常管理
- 使用工具脚本进行维护清理

---

**💡 提示**: 所有 `.sh` 文件都是快捷命令，实际调用 `deploy/scripts/` 中的Python脚本。
"""
        
        doc_path = self.root / 'docs' / 'SCRIPTS_LIST.md'
        doc_path.write_text(scripts_doc, encoding='utf-8')
        print("  ✓ docs/SCRIPTS_LIST.md")
    
    def generate_report(self):
        """生成整理报告"""
        print("\n" + "="*70)
        print("📊 最终整理完成")
        print("="*70)
        
        print(f"\n✅ 移动了 {len(self.moves)} 个文件")
        
        if self.moves:
            print("\n📋 移动记录:")
            for filename, target in self.moves:
                print(f"  • {filename} -> {target}")
        
        print("\n📁 最终结构:")
        print("""
stock_analysis_app/
├── deploy/
│   ├── scripts/         ← 所有脚本（部署+工具）
│   └── configs/         ← 所有配置
├── docs/                ← 所有文档
├── backend/             ← 后端代码
├── frontend/            ← 前端代码
├── data/                ← 数据文件
├── start_*.py           ← 启动脚本（仅3个）
└── *.sh                 ← 快捷命令（仅7个）
        """)
        
        print("\n🎯 保留在根目录的文件:")
        print("  • README.md            # 项目主文档")
        print("  • start_backend.py     # 启动后端")
        print("  • start_frontend.py    # 启动前端")  
        print("  • start_all.py         # 一键启动")
        print("  • test_backend.py      # 后端测试")
        print("  • *.sh                 # 快捷命令（7个）")
        
        print("\n📚 整理到 deploy/scripts/ 的脚本:")
        print("  • deploy_smart.py")
        print("  • service_manager.py")
        print("  • git_commit_push.py")
        print("  • clean_git_history.py")
        print("  • prepare_linux_deploy.py")
        print("  • cleanup_and_organize.py")
        print("  • cleanup_old_files.py")
        print("  • cleanup_redundant_files.py")
        print("  • reorganize_project.py")
        print("  • setup_linux.sh")
        
        print("\n📖 整理到 docs/ 的文档:")
        print("  • 所有 .md 文件（除了 README.md）")
        
        print("\n📝 下一步:")
        print("  git add .")
        print("  git commit -m 'refactor: 最终整理，所有脚本和文档归位'")
        print("  git push origin main")
        
        print("="*70 + "\n")
    
    def run(self):
        """执行整理"""
        print("="*70)
        print("🎯 最终项目整理")
        print("="*70)
        
        print("\n将会执行:")
        print("  1. 移动工具脚本到 deploy/scripts/")
        print("  2. 移动所有MD文档到 docs/（除了README.md）")
        print("  3. 更新文档")
        
        response = input("\n是否继续? (y/n): ").strip().lower()
        if response != 'y':
            print("\n❌ 操作已取消")
            return
        
        self.move_utility_scripts()
        self.move_docs_to_docs()
        self.update_docs_readme()
        self.create_scripts_list()
        self.generate_report()


def main():
    """主函数"""
    project_root = Path(__file__).parent
    organizer = FinalOrganizer(str(project_root))
    organizer.run()


if __name__ == '__main__':
    main()
