#!/usr/bin/env python3
"""
智能部署脚本 - 支持开发模式和生产模式
使用方法：
    python deploy_smart.py dev     # 开发模式（推荐）
    python deploy_smart.py prod    # 生产模式（需要Nginx）
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional

class SmartDeployer:
    """智能部署器"""
    
    # 你的服务器配置
    CONFIG = {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'db_20251106_analysis_a',
        'DB_USER': 'postgres',
        'DB_PASSWORD': '3.1415926',
        'SERVER_IP': '60.205.251.109',
        'BACKEND_PORT': '8000',
        'FRONTEND_PORT': '3000'
    }
    
    def __init__(self, project_root: str, mode: str):
        self.project_root = Path(project_root)
        self.mode = mode.lower()
        self.backend_dir = self.project_root / 'backend'
        self.frontend_dir = self.project_root / 'frontend'
        self.data_dir = self.project_root / 'data'
        
    def print_header(self):
        """打印头部"""
        print("=" * 70)
        print(f"🚀 智能部署脚本 - {self.mode.upper()}模式")
        print("=" * 70)
        print()
        
    def check_mode(self) -> bool:
        """检查模式是否有效"""
        if self.mode not in ['dev', 'prod']:
            print("❌ 错误：无效的模式")
            print()
            print("使用方法：")
            print("  python deploy_smart.py dev     # 开发模式")
            print("  python deploy_smart.py prod    # 生产模式")
            return False
        return True
    
    def check_system(self):
        """检查系统依赖"""
        print("📋 检查系统依赖...")
        
        # Python
        try:
            version = subprocess.check_output(['python3', '--version'], text=True).strip()
            print(f"  ✓ {version}")
        except:
            print("  ❌ Python3 未安装")
            return False
        
        # Node.js
        try:
            version = subprocess.check_output(['node', '--version'], text=True).strip()
            print(f"  ✓ Node.js {version}")
        except:
            print("  ❌ Node.js 未安装")
            return False
        
        # PostgreSQL (检查客户端)
        try:
            subprocess.check_output(['psql', '--version'], text=True, stderr=subprocess.DEVNULL)
            print(f"  ✓ PostgreSQL 客户端已安装")
        except:
            print("  ⚠ PostgreSQL客户端未安装（数据库在本机时需要）")
        
        # Nginx (仅生产模式需要)
        if self.mode == 'prod':
            try:
                version = subprocess.check_output(['nginx', '-v'], text=True, stderr=subprocess.STDOUT).strip()
                print(f"  ✓ {version}")
            except:
                print("  ❌ Nginx 未安装（生产模式需要）")
                print("     安装: sudo apt install nginx")
                return False
        
        print()
        return True
    
    def check_backend_config(self) -> bool:
        """检查并配置后端"""
        print("🔧 配置后端...")
        
        env_file = self.backend_dir / '.env'
        env_example = self.backend_dir / '.env.example'
        
        # 检查.env文件
        if env_file.exists():
            print("  ✓ .env 文件已存在")
            # 读取现有配置检查是否正确
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查关键配置
            need_update = False
            for key, value in self.CONFIG.items():
                if key.startswith('DB_') or key == 'SERVER_IP':
                    if f"{key}=" not in content or f"{key}={value}" not in content:
                        need_update = True
                        break
            
            if need_update:
                print("  ⚠ .env配置需要更新")
                self._update_env_file(env_file)
            else:
                print("  ✓ .env配置正确")
        else:
            print("  ⚠ .env文件不存在，创建中...")
            if env_example.exists():
                self._create_env_file(env_file)
            else:
                print("  ❌ .env.example 不存在")
                return False
        
        # 检查虚拟环境
        venv_dir = self.backend_dir / 'venv'
        if not venv_dir.exists():
            print("  ⚠ 创建Python虚拟环境...")
            subprocess.run(['python3', '-m', 'venv', 'venv'], cwd=self.backend_dir, check=True)
            print("  ✓ 虚拟环境已创建")
        else:
            print("  ✓ 虚拟环境已存在")
        
        # 安装依赖
        print("  📦 安装Python依赖...")
        pip_path = venv_dir / 'bin' / 'pip'
        subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'], 
                      cwd=self.backend_dir, capture_output=True)
        subprocess.run([str(pip_path), 'install', '-r', 'requirements.txt'], 
                      cwd=self.backend_dir, check=True)
        print("  ✓ Python依赖已安装")
        
        print()
        return True
    
    def _create_env_file(self, env_file: Path):
        """创建.env文件"""
        content = f"""# 数据库配置
DB_HOST={self.CONFIG['DB_HOST']}
DB_PORT={self.CONFIG['DB_PORT']}
DB_NAME={self.CONFIG['DB_NAME']}
DB_USER={self.CONFIG['DB_USER']}
DB_PASSWORD={self.CONFIG['DB_PASSWORD']}

# API配置
API_PORT={self.CONFIG['BACKEND_PORT']}
DEBUG=True
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✓ .env文件已创建")
    
    def _update_env_file(self, env_file: Path):
        """更新.env文件"""
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        updated = []
        keys_found = set()
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in self.CONFIG:
                    updated.append(f"{key}={self.CONFIG[key]}\n")
                    keys_found.add(key)
                else:
                    updated.append(line)
            else:
                updated.append(line)
        
        # 添加缺失的配置
        for key, value in self.CONFIG.items():
            if key.startswith('DB_') and key not in keys_found:
                updated.append(f"{key}={value}\n")
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated)
        print("  ✓ .env文件已更新")
    
    def check_database(self) -> bool:
        """检查数据库连接和数据"""
        print("🗄️  检查数据库...")
        
        # 测试连接
        python_path = self.backend_dir / 'venv' / 'bin' / 'python'
        test_code = "from app.database import test_connection; import sys; sys.exit(0 if test_connection() else 1)"
        
        result = subprocess.run(
            [str(python_path), '-c', test_code],
            cwd=self.backend_dir,
            capture_output=True
        )
        
        if result.returncode != 0:
            print("  ❌ 数据库连接失败")
            print("  请检查：")
            print("    1. PostgreSQL是否运行: sudo systemctl status postgresql")
            print("    2. 数据库是否存在: psql -U postgres -l")
            print(f"    3. .env配置是否正确")
            return False
        
        print("  ✓ 数据库连接成功")
        
        # 检查是否已有数据
        state_file = self.data_dir / 'data_import_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                imported_dates = [k for k, v in state.get('files', {}).items() 
                                if v.get('status') == 'success']
                if imported_dates:
                    print(f"  ✓ 数据已导入 ({len(imported_dates)} 个日期)")
                    print(f"    最新日期: {max(imported_dates)}")
                    return True
            except:
                pass
        
        # 检查数据库中的记录数
        count_code = """
from app.database import SessionLocal
from app.db_models import DailyStockData
db = SessionLocal()
count = db.query(DailyStockData).count()
db.close()
print(count)
"""
        result = subprocess.run(
            [str(python_path), '-c', count_code],
            cwd=self.backend_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            count = int(result.stdout.strip())
            if count > 0:
                print(f"  ✓ 数据库已有数据 ({count:,} 条记录)")
            else:
                print("  ⚠ 数据库为空，需要导入数据")
                return self._import_data()
        
        print()
        return True
    
    def _import_data(self) -> bool:
        """导入数据"""
        xlsx_files = list(self.data_dir.glob('*.xlsx'))
        if not xlsx_files:
            print("  ⚠ data目录中没有Excel文件，跳过导入")
            return True
        
        print(f"  📊 发现 {len(xlsx_files)} 个Excel文件")
        response = input("  是否导入数据？(y/n): ").strip().lower()
        
        if response == 'y':
            print("  🔄 开始导入数据...")
            python_path = self.backend_dir / 'venv' / 'bin' / 'python'
            result = subprocess.run(
                [str(python_path), 'scripts/import_data_robust.py'],
                cwd=self.backend_dir
            )
            if result.returncode == 0:
                print("  ✓ 数据导入完成")
                return True
            else:
                print("  ❌ 数据导入失败")
                return False
        else:
            print("  ⏭️  跳过数据导入")
            return True
    
    def check_frontend(self) -> bool:
        """检查并配置前端"""
        print("🎨 配置前端...")
        
        node_modules = self.frontend_dir / 'node_modules'
        if not node_modules.exists():
            print("  📦 安装npm依赖...")
            subprocess.run(['npm', 'install'], cwd=self.frontend_dir, check=True)
            print("  ✓ npm依赖已安装")
        else:
            print("  ✓ npm依赖已存在")
        
        if self.mode == 'prod':
            build_dir = self.frontend_dir / 'build'
            if not build_dir.exists() or input("  重新构建前端？(y/n): ").strip().lower() == 'y':
                print("  🔨 构建前端生产版本...")
                subprocess.run(['npm', 'run', 'build'], cwd=self.frontend_dir, check=True)
                print("  ✓ 前端构建完成")
            else:
                print("  ✓ 使用现有构建")
        
        print()
        return True
    
    def deploy_dev_mode(self):
        """部署开发模式"""
        print("=" * 70)
        print("🎯 开发模式部署")
        print("=" * 70)
        print()
        
        # 创建启动脚本
        self._create_dev_scripts()
        
        print("✅ 开发模式部署完成！")
        print()
        print("🚀 启动服务：")
        print()
        print("  方式1：前后台分别启动（推荐用screen/tmux）")
        print("    ./start_backend.sh    # 后端")
        print("    ./start_frontend.sh   # 前端")
        print()
        print("  方式2：后台运行")
        print("    nohup ./start_backend.sh > backend.log 2>&1 &")
        print("    nohup ./start_frontend.sh > frontend.log 2>&1 &")
        print()
        print("🌐 访问地址：")
        print(f"  前端：http://{self.CONFIG['SERVER_IP']}:{self.CONFIG['FRONTEND_PORT']}")
        print(f"  API： http://{self.CONFIG['SERVER_IP']}:{self.CONFIG['BACKEND_PORT']}/docs")
        print()
        print("💡 提示：开发模式适合测试和调试，服务需要保持运行")
        print()
    
    def deploy_prod_mode(self):
        """部署生产模式"""
        print("=" * 70)
        print("🏭 生产模式部署")
        print("=" * 70)
        print()
        
        # 配置Systemd
        self._setup_systemd()
        
        # 配置Nginx
        self._setup_nginx()
        
        print()
        print("✅ 生产模式部署完成！")
        print()
        print("🌐 访问地址：")
        print(f"  统一入口：http://{self.CONFIG['SERVER_IP']}/")
        print(f"  API文档： http://{self.CONFIG['SERVER_IP']}/api/docs")
        print()
        print("🔧 管理命令：")
        print("  sudo systemctl status stock-backend   # 查看状态")
        print("  sudo systemctl restart stock-backend  # 重启后端")
        print("  sudo systemctl restart nginx          # 重启Nginx")
        print("  journalctl -u stock-backend -f        # 查看日志")
        print()
    
    def _create_dev_scripts(self):
        """创建开发模式启动脚本"""
        # 后端启动脚本
        backend_script = self.project_root / 'start_backend.sh'
        backend_content = f"""#!/bin/bash
cd "{self.backend_dir}"
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port {self.CONFIG['BACKEND_PORT']} --reload
"""
        backend_script.write_text(backend_content)
        backend_script.chmod(0o755)
        print(f"  ✓ 创建 start_backend.sh")
        
        # 前端启动脚本
        frontend_script = self.project_root / 'start_frontend.sh'
        frontend_content = f"""#!/bin/bash
cd "{self.frontend_dir}"
PORT={self.CONFIG['FRONTEND_PORT']} npm start
"""
        frontend_script.write_text(frontend_content)
        frontend_script.chmod(0o755)
        print(f"  ✓ 创建 start_frontend.sh")
    
    def _setup_systemd(self):
        """配置Systemd服务"""
        print("⚙️  配置Systemd服务...")
        
        service_content = f"""[Unit]
Description=Stock Analysis Backend API
After=network.target postgresql.service

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={self.backend_dir}
Environment="PATH={self.backend_dir}/venv/bin"
ExecStart={self.backend_dir}/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port {self.CONFIG['BACKEND_PORT']}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = self.project_root / 'deploy' / 'stock-backend.service'
        service_file.parent.mkdir(exist_ok=True)
        service_file.write_text(service_content)
        
        print(f"  ✓ 服务文件已生成: {service_file}")
        print()
        print("  执行以下命令安装服务：")
        print(f"    sudo cp {service_file} /etc/systemd/system/")
        print("    sudo systemctl daemon-reload")
        print("    sudo systemctl start stock-backend")
        print("    sudo systemctl enable stock-backend")
    
    def _setup_nginx(self):
        """配置Nginx"""
        print()
        print("⚙️  配置Nginx...")
        
        nginx_content = f"""server {{
    listen 80;
    server_name {self.CONFIG['SERVER_IP']};
    
    # 前端静态文件
    location / {{
        root {self.frontend_dir}/build;
        try_files $uri $uri/ /index.html;
    }}
    
    # API反向代理
    location /api {{
        proxy_pass http://localhost:{self.CONFIG['BACKEND_PORT']};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""
        
        nginx_file = self.project_root / 'deploy' / 'nginx-stock-analysis.conf'
        nginx_file.write_text(nginx_content)
        
        print(f"  ✓ Nginx配置已生成: {nginx_file}")
        print()
        print("  执行以下命令安装配置：")
        print(f"    sudo cp {nginx_file} /etc/nginx/sites-available/stock-analysis")
        print("    sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/")
        print("    sudo nginx -t")
        print("    sudo systemctl restart nginx")
    
    def run(self):
        """运行部署"""
        self.print_header()
        
        if not self.check_mode():
            sys.exit(1)
        
        if not self.check_system():
            sys.exit(1)
        
        if not self.check_backend_config():
            sys.exit(1)
        
        if not self.check_database():
            sys.exit(1)
        
        if not self.check_frontend():
            sys.exit(1)
        
        if self.mode == 'dev':
            self.deploy_dev_mode()
        else:
            self.deploy_prod_mode()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法：")
        print("  python deploy_smart.py dev     # 开发模式（推荐）")
        print("  python deploy_smart.py prod    # 生产模式（需要Nginx）")
        print()
        print("说明：")
        print("  dev模式  - 快速部署，前端3000端口，后端8000端口，适合测试")
        print("  prod模式 - 生产部署，使用Nginx统一80端口，需要额外配置")
        sys.exit(1)
    
    mode = sys.argv[1]
    project_root = Path(__file__).parent
    
    deployer = SmartDeployer(str(project_root), mode)
    deployer.run()


if __name__ == '__main__':
    main()
