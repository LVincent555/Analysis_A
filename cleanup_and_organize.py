#!/usr/bin/env python3
"""
清理和整理项目脚本
1. 移动SQL文件到deploy目录
2. 删除backend/sql目录
3. 删除项目外旧版本文件
4. 生成对应的sh脚本
"""

import os
import shutil
from pathlib import Path

class ProjectCleaner:
    """项目清理器"""
    
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.parent = self.root.parent
        
    def move_sql_files(self):
        """移动SQL文件到deploy"""
        print("\n📦 处理SQL文件...")
        
        # 1. 移动根目录的sql到deploy/configs
        root_sql = self.root / 'sql'
        if root_sql.exists():
            for sql_file in root_sql.glob('*.sql'):
                target = self.root / 'deploy' / 'configs' / sql_file.name
                if not target.exists():
                    shutil.copy2(sql_file, target)
                    print(f"  ✓ {sql_file.name} -> deploy/configs/")
            
            # 删除根目录的sql文件夹
            shutil.rmtree(root_sql)
            print(f"  ✓ 已删除 sql/ 目录")
        
        # 2. 处理backend/sql
        backend_sql = self.root / 'backend' / 'sql'
        if backend_sql.exists():
            # 复制有用的SQL文件到deploy/configs
            for sql_file in backend_sql.glob('*.sql'):
                target = self.root / 'deploy' / 'configs' / sql_file.name
                if not target.exists():
                    shutil.copy2(sql_file, target)
                    print(f"  ✓ backend/sql/{sql_file.name} -> deploy/configs/")
            
            # 删除backend/sql目录
            shutil.rmtree(backend_sql)
            print(f"  ✓ 已删除 backend/sql/ 目录")
    
    def clean_old_files(self):
        """清理项目外的旧版本文件"""
        print("\n🗑️  清理旧版本文件...")
        
        # 定义要删除的文件
        old_files = [
            'analyze_stocks_main_board.py',
            'analyze_stocks_with_growth.py',
            'stock_analysis_main_board.xlsx',
            'stock_analysis_with_growth.xlsx',
            'README_股票分析说明.md',
            '新建 文本文档.txt'
        ]
        
        deleted = []
        for filename in old_files:
            file_path = self.parent / filename
            if file_path.exists():
                if file_path.is_file():
                    file_path.unlink()
                    deleted.append(filename)
                    print(f"  ✓ 已删除 {filename}")
        
        if not deleted:
            print("  • 没有找到旧文件")
        
        return deleted
    
    def clean_root_sh_files(self):
        """清理根目录的Shell脚本"""
        print("\n🧹 清理根目录Shell脚本...")
        
        # 要保留的sh文件（如果有的话）
        keep_files = set()
        
        # 要删除的sh文件
        sh_files = list(self.root.glob('*.sh'))
        
        deleted = []
        for sh_file in sh_files:
            if sh_file.name not in keep_files:
                sh_file.unlink()
                deleted.append(sh_file.name)
                print(f"  ✓ 已删除 {sh_file.name}")
        
        if not deleted:
            print("  • 没有需要清理的sh文件")
    
    def create_service_shortcuts(self):
        """创建服务管理快捷脚本"""
        print("\n📝 创建快捷脚本...")
        
        # 根目录的快捷脚本
        shortcuts = {
            'service': {
                'content': '''#!/bin/bash
# 服务管理快捷命令
python3 deploy/scripts/service_manager.py "$@"
''',
                'desc': '服务管理'
            },
            'deploy': {
                'content': '''#!/bin/bash
# 部署快捷命令
python3 deploy/scripts/deploy_smart.py "$@"
''',
                'desc': '智能部署'
            },
            'status': {
                'content': '''#!/bin/bash
# 查看服务状态
python3 deploy/scripts/service_manager.py status
''',
                'desc': '查看状态'
            },
            'start': {
                'content': '''#!/bin/bash
# 启动所有服务
python3 deploy/scripts/service_manager.py start all
''',
                'desc': '启动服务'
            },
            'stop': {
                'content': '''#!/bin/bash
# 停止所有服务
python3 deploy/scripts/service_manager.py stop all
''',
                'desc': '停止服务'
            },
            'restart': {
                'content': '''#!/bin/bash
# 重启所有服务
python3 deploy/scripts/service_manager.py restart all
''',
                'desc': '重启服务'
            },
            'logs': {
                'content': '''#!/bin/bash
# 查看日志
SERVICE=${1:-backend}
python3 deploy/scripts/service_manager.py logs $SERVICE
''',
                'desc': '查看日志'
            }
        }
        
        for name, info in shortcuts.items():
            script_path = self.root / f'{name}.sh'
            script_path.write_text(info['content'], encoding='utf-8')
            script_path.chmod(0o755)
            print(f"  ✓ {name}.sh - {info['desc']}")
    
    def update_gitignore(self):
        """更新.gitignore"""
        print("\n📝 更新.gitignore...")
        
        gitignore_path = self.root / '.gitignore'
        
        additions = [
            '\n# Service management',
            'logs/',
            '.pids/',
            '*.pid',
            'service_config.json'
        ]
        
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding='utf-8')
            
            # 检查是否已存在
            if 'Service management' not in content:
                content += '\n' + '\n'.join(additions) + '\n'
                gitignore_path.write_text(content, encoding='utf-8')
                print("  ✓ 已更新 .gitignore")
            else:
                print("  • .gitignore 已是最新")
    
    def create_summary_doc(self):
        """创建项目结构说明"""
        print("\n📋 创建项目结构说明...")
        
        content = """# 📁 项目结构说明

## 目录组织

```
stock_analysis_app/
├── backend/              # 后端FastAPI应用
│   ├── app/             # 应用代码
│   ├── scripts/         # 工具脚本
│   ├── venv/            # Python虚拟环境
│   └── requirements.txt # Python依赖
│
├── frontend/            # 前端React应用
│   ├── src/            # 源代码
│   ├── public/         # 静态资源
│   └── package.json    # Node.js依赖
│
├── data/               # 数据文件
│   └── *.xlsx         # Excel数据文件
│
├── deploy/             # 部署相关
│   ├── scripts/       # 部署脚本
│   │   ├── deploy_smart.py      # 智能部署
│   │   ├── service_manager.py   # 服务管理
│   │   ├── git_commit_push.py   # Git提交
│   │   └── ...
│   ├── configs/       # 配置模板
│   │   ├── *.service          # Systemd配置
│   │   ├── *.conf             # Nginx配置
│   │   └── *.sql              # 数据库SQL
│   └── README.md
│
├── docs/              # 项目文档
│   ├── START_HERE.md         # 入门指南
│   ├── 部署使用手册.md       # 部署教程
│   ├── 服务管理手册.md       # 服务管理
│   └── ...
│
├── logs/              # 运行日志（自动生成）
├── .pids/             # 进程PID（自动生成）
│
├── start_*.py         # 快速启动脚本
├── *.sh              # Shell快捷命令
├── reorganize_project.py  # 项目重组脚本
└── README.md         # 项目主文档
```

## 快捷命令（Shell脚本）

| 脚本 | 说明 | 示例 |
|------|------|------|
| `./service.sh` | 服务管理 | `./service.sh start all` |
| `./deploy.sh` | 智能部署 | `./deploy.sh dev` |
| `./start.sh` | 启动服务 | `./start.sh` |
| `./stop.sh` | 停止服务 | `./stop.sh` |
| `./restart.sh` | 重启服务 | `./restart.sh` |
| `./status.sh` | 查看状态 | `./status.sh` |
| `./logs.sh` | 查看日志 | `./logs.sh backend` |

## Python快速启动

| 脚本 | 说明 |
|------|------|
| `start_backend.py` | 启动后端 |
| `start_frontend.py` | 启动前端 |
| `start_all.py` | 一键启动所有 |

## 部署相关

### 开发环境
```bash
python3 deploy/scripts/deploy_smart.py dev
python3 deploy/scripts/service_manager.py start all
```

### 生产环境
```bash
python3 deploy/scripts/deploy_smart.py prod
# 然后按提示配置Systemd和Nginx
```

## 文档导航

1. **新手入门**: `docs/START_HERE.md`
2. **部署系统**: `docs/部署使用手册.md`
3. **管理服务**: `docs/服务管理手册.md`
4. **更新代码**: `docs/服务器更新指南.md`
5. **项目总览**: `docs/PROJECT_OVERVIEW.md`

## 注意事项

### 已删除的内容
- ✅ 根目录 `sql/` 文件夹（已移至 `deploy/configs/`）
- ✅ `backend/sql/` 文件夹（已移至 `deploy/configs/`）
- ✅ 项目外的旧版本文件（已有Git管理，无需保留）
- ✅ 多余的Shell脚本（已整合为快捷命令）

### 配置文件位置
- SQL初始化脚本: `deploy/configs/*.sql`
- Systemd配置: `deploy/configs/*.service`
- Nginx配置: `deploy/configs/*.conf`
- 环境变量模板: `backend/.env.example`

### 日志文件
- 服务日志: `logs/backend.log`, `logs/frontend.log`
- 管理器日志: `logs/manager_YYYYMMDD.log`

### Git忽略
- `logs/` - 运行日志
- `.pids/` - 进程PID
- `data/*.xlsx` - 数据文件
- `backend/.env` - 数据库密码
- `node_modules/`, `venv/` - 依赖包

---

**📖 更多信息请查看各目录的README文件**
"""
        
        doc_path = self.root / 'docs' / 'PROJECT_STRUCTURE.md'
        doc_path.write_text(content, encoding='utf-8')
        print("  ✓ docs/PROJECT_STRUCTURE.md")
    
    def generate_report(self, deleted_files: list):
        """生成清理报告"""
        print("\n" + "="*70)
        print("📊 清理完成报告")
        print("="*70)
        
        print("\n✅ 已完成:")
        print("  • SQL文件已整合到 deploy/configs/")
        print("  • backend/sql/ 目录已删除")
        print(f"  • 清理了 {len(deleted_files)} 个旧版本文件")
        print("  • 创建了 7 个快捷Shell脚本")
        print("  • 更新了 .gitignore")
        print("  • 创建了项目结构说明文档")
        
        if deleted_files:
            print("\n🗑️  已删除的文件:")
            for f in deleted_files:
                print(f"  • {f}")
        
        print("\n📁 新的项目结构:")
        print("""
stock_analysis_app/
├── deploy/
│   ├── scripts/         ← 所有部署脚本
│   └── configs/         ← 所有配置（包括SQL）
├── docs/                ← 所有文档
├── backend/             ← 后端代码（无sql目录）
├── frontend/            ← 前端代码
├── data/                ← 数据文件
├── start_*.py           ← Python启动脚本
└── *.sh                 ← Shell快捷命令
        """)
        
        print("\n🚀 新的快捷命令:")
        print("  ./service.sh start all   # 启动服务")
        print("  ./status.sh              # 查看状态")
        print("  ./logs.sh backend        # 查看日志")
        print("  ./stop.sh                # 停止服务")
        
        print("\n📝 下一步:")
        print("  1. git add .")
        print("  2. git commit -m 'refactor: 清理和整合项目结构'")
        print("  3. git push origin main")
        
        print("="*70 + "\n")
    
    def run(self):
        """执行清理"""
        print("="*70)
        print("🧹 项目清理和整理工具")
        print("="*70)
        
        print("\n将会执行以下操作:")
        print("  1. 移动SQL文件到 deploy/configs/")
        print("  2. 删除 backend/sql/ 目录")
        print("  3. 删除项目外的旧版本文件")
        print("  4. 清理根目录多余的Shell脚本")
        print("  5. 创建统一的快捷Shell脚本")
        print("  6. 更新 .gitignore")
        print("  7. 创建项目结构说明文档")
        
        response = input("\n是否继续? (y/n): ").strip().lower()
        if response != 'y':
            print("\n❌ 操作已取消")
            return
        
        # 执行清理
        self.move_sql_files()
        deleted_files = self.clean_old_files()
        self.clean_root_sh_files()
        self.create_service_shortcuts()
        self.update_gitignore()
        self.create_summary_doc()
        self.generate_report(deleted_files)


def main():
    """主函数"""
    project_root = Path(__file__).parent
    cleaner = ProjectCleaner(str(project_root))
    cleaner.run()


if __name__ == '__main__':
    main()
