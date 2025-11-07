#!/usr/bin/env python3
"""
项目结构重组脚本
自动将文件归类到合适的目录
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List

class ProjectReorganizer:
    """项目重组器"""
    
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.moves = []  # 记录移动操作
        
        # 定义新的目录结构
        self.structure = {
            'deploy': {
                'desc': '部署相关文件',
                'subdirs': {
                    'scripts': '部署脚本',
                    'configs': '配置模板'
                }
            },
            'docs': {
                'desc': '项目文档',
                'subdirs': {}
            }
        }
        
        # 定义文件分类规则
        self.file_rules = {
            # 部署脚本（移到 deploy/scripts/）
            'deploy/scripts': [
                'deploy_smart.py',
                'prepare_linux_deploy.py',
                'git_commit_push.py',
                'clean_git_history.py',
                'service_manager.py',
                'service.sh',
                'check_and_deploy.sh',
                'quick_start.sh',
                'fix_frontend.sh'
            ],
            
            # 部署配置（移到 deploy/configs/）
            'deploy/configs': [
                'stock-backend.service',
                'nginx-stock-analysis.conf',
                'init_database.sql'
            ],
            
            # 项目文档（移到 docs/）
            'docs': [
                'START_HERE.md',
                '部署使用手册.md',
                '服务器更新指南.md',
                '服务管理手册.md',
                'LINUX_DEPLOY_GUIDE.md',
                'LINUX_DEPLOY_SUMMARY.md',
                'README_LINUX.md',
                'DEPLOY_CHECKLIST.md',
                '部署总结.txt',
                'PROJECT_OVERVIEW.md',
                'README_FOR_CLAUDE.md',
                'REFACTORING.md',
                'SCRIPTS_GUIDE.md',
                'TEST_REPORT.md',
                'VERSION.md',
                'CHANGELOG.md',
                '快速开始.md',
                'DEPLOYMENT_SUMMARY.md',
                'CLAUDE.md'
            ],
            
            # 工具脚本（保留在根目录）
            'root': [
                'start_backend.py',
                'start_frontend.py',
                'start_all.py',
                'test_backend.py',
                'cleanup_old_files.py',
                'cleanup_redundant_files.py'
            ]
        }
    
    def create_directories(self):
        """创建新目录结构"""
        print("\n📁 创建目录结构...")
        
        for dir_name, info in self.structure.items():
            dir_path = self.root / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"  ✓ {dir_name}/ - {info['desc']}")
            
            for subdir, desc in info['subdirs'].items():
                subdir_path = dir_path / subdir
                subdir_path.mkdir(exist_ok=True)
                print(f"    ✓ {dir_name}/{subdir}/ - {desc}")
        
        # deploy目录已存在，只需要创建子目录
        deploy_scripts = self.root / 'deploy' / 'scripts'
        deploy_configs = self.root / 'deploy' / 'configs'
        deploy_scripts.mkdir(exist_ok=True)
        deploy_configs.mkdir(exist_ok=True)
        print(f"  ✓ deploy/scripts/ - 部署脚本")
        print(f"  ✓ deploy/configs/ - 配置模板")
    
    def move_file(self, filename: str, target_dir: str) -> bool:
        """移动单个文件"""
        source = self.root / filename
        
        # 处理已经在deploy目录中的文件
        if target_dir.startswith('deploy/') and filename.startswith('deploy/'):
            # 文件已经在deploy目录，可能需要移动到子目录
            source = self.root / filename
            subdir = target_dir.split('/', 1)[1] if '/' in target_dir else ''
            if subdir:
                target = self.root / 'deploy' / subdir / Path(filename).name
            else:
                return False  # 已经在正确位置
        else:
            target = self.root / target_dir / filename
        
        if not source.exists():
            return False
        
        if source == target:
            return False
        
        try:
            # 如果目标已存在，先删除
            if target.exists():
                target.unlink()
            
            shutil.move(str(source), str(target))
            self.moves.append((filename, target_dir))
            return True
        except Exception as e:
            print(f"  ⚠ 移动失败 {filename}: {e}")
            return False
    
    def reorganize(self):
        """执行重组"""
        print("\n🔄 开始重组项目...")
        
        moved_count = 0
        
        for target_dir, files in self.file_rules.items():
            if target_dir == 'root':
                continue  # 跳过根目录文件
            
            print(f"\n📦 处理 {target_dir}/")
            for filename in files:
                if self.move_file(filename, target_dir):
                    print(f"  ✓ {filename} -> {target_dir}/")
                    moved_count += 1
        
        # 处理deploy目录下已存在的文件
        print(f"\n📦 整理 deploy/ 目录")
        deploy_dir = self.root / 'deploy'
        if deploy_dir.exists():
            # 移动 README.md 到 docs
            deploy_readme = deploy_dir / 'README.md'
            if deploy_readme.exists():
                target = self.root / 'docs' / 'DEPLOY_README.md'
                shutil.move(str(deploy_readme), str(target))
                print(f"  ✓ deploy/README.md -> docs/DEPLOY_README.md")
                moved_count += 1
            
            # 移动配置文件到 configs
            for config_file in ['stock-backend.service', 'nginx-stock-analysis.conf', 'init_database.sql']:
                source = deploy_dir / config_file
                if source.exists():
                    target = deploy_dir / 'configs' / config_file
                    shutil.move(str(source), str(target))
                    print(f"  ✓ {config_file} -> deploy/configs/")
                    moved_count += 1
            
            # 移动脚本到 scripts
            for script_file in ['setup_linux.sh']:
                source = deploy_dir / script_file
                if source.exists():
                    target = deploy_dir / 'scripts' / script_file
                    shutil.move(str(source), str(target))
                    print(f"  ✓ {script_file} -> deploy/scripts/")
                    moved_count += 1
        
        return moved_count
    
    def create_readme(self):
        """创建各目录的README"""
        print("\n📝 创建README文件...")
        
        # deploy/README.md
        deploy_readme = self.root / 'deploy' / 'README.md'
        deploy_content = """# 📦 部署目录

本目录包含所有部署相关的文件和脚本。

## 📁 目录结构

```
deploy/
├── scripts/              # 部署脚本
│   ├── deploy_smart.py  # 智能部署主脚本
│   ├── service_manager.py # 服务管理器
│   ├── setup_linux.sh   # Linux环境配置
│   └── ...
├── configs/             # 配置模板
│   ├── stock-backend.service  # Systemd服务配置
│   ├── nginx-stock-analysis.conf # Nginx配置
│   └── init_database.sql # 数据库初始化
└── README.md           # 本文件

## 🚀 快速开始

### 开发模式部署
```bash
python3 deploy/scripts/deploy_smart.py dev
```

### 服务管理
```bash
python3 deploy/scripts/service_manager.py start all
python3 deploy/scripts/service_manager.py status
```

## 📖 详细文档

查看 `docs/` 目录获取完整文档：
- `docs/部署使用手册.md` - 完整部署教程
- `docs/服务管理手册.md` - 服务管理说明
- `docs/服务器更新指南.md` - 更新流程

## 💡 提示

所有部署脚本都在 `scripts/` 子目录中，配置模板在 `configs/` 子目录中。
"""
        deploy_readme.write_text(deploy_content, encoding='utf-8')
        print("  ✓ deploy/README.md")
        
        # docs/README.md
        docs_readme = self.root / 'docs' / 'README.md'
        docs_content = """# 📚 项目文档

本目录包含所有项目文档。

## 📖 文档分类

### 🚀 部署文档
- `START_HERE.md` - 从这里开始（文档导航）
- `部署使用手册.md` - 完整部署教程
- `服务器更新指南.md` - 更新流程
- `服务管理手册.md` - 服务管理
- `LINUX_DEPLOY_GUIDE.md` - Linux部署指南
- `LINUX_DEPLOY_SUMMARY.md` - 部署总结
- `README_LINUX.md` - Linux快速参考
- `DEPLOY_CHECKLIST.md` - 部署检查清单
- `部署总结.txt` - 快速参考

### 📋 项目文档
- `PROJECT_OVERVIEW.md` - 项目总览
- `README_FOR_CLAUDE.md` - 开发文档
- `REFACTORING.md` - 重构记录
- `SCRIPTS_GUIDE.md` - 脚本使用指南
- `VERSION.md` - 版本历史
- `CHANGELOG.md` - 更新日志

### 🧪 测试文档
- `TEST_REPORT.md` - 测试报告

## 🎯 推荐阅读顺序

1. **新手入门**: `START_HERE.md`
2. **部署系统**: `部署使用手册.md`
3. **管理服务**: `服务管理手册.md`
4. **项目了解**: `PROJECT_OVERVIEW.md`

## 💡 快速查找

- **部署问题**: 查看 `部署使用手册.md` 的"故障排查"部分
- **更新代码**: 查看 `服务器更新指南.md`
- **管理服务**: 查看 `服务管理手册.md`
"""
        docs_readme.write_text(docs_content, encoding='utf-8')
        print("  ✓ docs/README.md")
    
    def update_main_readme(self):
        """更新主README"""
        print("\n📝 更新主README...")
        
        main_readme = self.root / 'README.md'
        if not main_readme.exists():
            return
        
        # 在README开头添加目录结构说明
        content = main_readme.read_text(encoding='utf-8')
        
        if '## 📁 项目结构' not in content:
            structure_section = """
## 📁 项目结构

```
stock_analysis_app/
├── backend/              # 后端FastAPI应用
├── frontend/             # 前端React应用
├── data/                 # 数据文件
├── deploy/              # 🆕 部署相关
│   ├── scripts/        # 部署脚本
│   ├── configs/        # 配置模板
│   └── README.md
├── docs/                # 🆕 项目文档
│   ├── START_HERE.md   # 从这里开始
│   ├── 部署使用手册.md
│   ├── 服务管理手册.md
│   └── README.md
├── logs/                # 服务日志（运行时生成）
├── .pids/               # 进程PID（运行时生成）
├── start_backend.py     # 启动后端
├── start_frontend.py    # 启动前端
├── start_all.py         # 一键启动
└── README.md           # 本文件
```

## 🚀 快速开始

### 本地开发（Windows/Mac/Linux）
```bash
python start_all.py
```

### 服务器部署（Linux）
```bash
# 1. 部署
python3 deploy/scripts/deploy_smart.py dev

# 2. 启动服务
python3 deploy/scripts/service_manager.py start all

# 3. 查看状态
python3 deploy/scripts/service_manager.py status
```

### 📖 详细文档
- **新手**: 查看 `docs/START_HERE.md`
- **部署**: 查看 `docs/部署使用手册.md`
- **管理**: 查看 `docs/服务管理手册.md`

---

"""
            # 在第一个##之前插入
            parts = content.split('\n## ', 1)
            if len(parts) == 2:
                content = parts[0] + '\n' + structure_section + '\n## ' + parts[1]
            else:
                content = content + '\n' + structure_section
            
            main_readme.write_text(content, encoding='utf-8')
            print("  ✓ 已更新 README.md")
    
    def generate_report(self, moved_count: int):
        """生成重组报告"""
        print("\n" + "="*70)
        print("📊 重组完成报告")
        print("="*70)
        print(f"\n✅ 成功移动 {moved_count} 个文件")
        
        if self.moves:
            print("\n📋 文件移动记录:")
            for filename, target_dir in self.moves:
                print(f"  • {filename} -> {target_dir}/")
        
        print("\n📁 新的目录结构:")
        print("""
stock_analysis_app/
├── deploy/              ← 部署相关
│   ├── scripts/        ← 所有部署脚本
│   ├── configs/        ← 配置模板
│   └── README.md
├── docs/                ← 项目文档
│   ├── START_HERE.md
│   ├── 部署使用手册.md
│   ├── 服务管理手册.md
│   └── README.md
├── backend/             ← 后端代码
├── frontend/            ← 前端代码
├── data/                ← 数据文件
├── logs/                ← 服务日志（自动生成）
└── start_*.py           ← 快速启动脚本
        """)
        
        print("\n💡 提示:")
        print("  1. 部署脚本移动到: deploy/scripts/")
        print("  2. 配置文件移动到: deploy/configs/")
        print("  3. 文档移动到: docs/")
        print("  4. 快速启动脚本保留在根目录")
        
        print("\n🚀 下一步:")
        print("  1. 测试新结构: python3 deploy/scripts/service_manager.py status")
        print("  2. 提交更改: git add . && git commit -m 'refactor: 重组项目结构'")
        print("  3. 推送到远程: git push origin main")
        print("="*70 + "\n")
    
    def run(self):
        """执行重组"""
        print("="*70)
        print("🔧 项目结构重组工具")
        print("="*70)
        
        # 确认
        print("\n⚠️  此操作将重新组织项目文件结构")
        print("\n将会:")
        print("  • 创建 deploy/scripts/ 和 deploy/configs/ 目录")
        print("  • 创建 docs/ 目录")
        print("  • 移动部署脚本到 deploy/scripts/")
        print("  • 移动配置文件到 deploy/configs/")
        print("  • 移动文档到 docs/")
        print("  • 保留启动脚本在根目录")
        
        response = input("\n是否继续? (y/n): ").strip().lower()
        if response != 'y':
            print("\n❌ 操作已取消")
            return
        
        # 执行重组
        self.create_directories()
        moved_count = self.reorganize()
        self.create_readme()
        self.update_main_readme()
        self.generate_report(moved_count)


def main():
    """主函数"""
    project_root = Path(__file__).parent
    reorganizer = ProjectReorganizer(str(project_root))
    reorganizer.run()


if __name__ == '__main__':
    main()
