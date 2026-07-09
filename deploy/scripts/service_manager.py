#!/usr/bin/env python3
"""
股票分析系统 - 服务管理器
功能：启动、停止、重启、监控所有服务
支持：完整日志、自动重启、状态监控
"""

import os
import sys
import time
import signal
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

class ServiceManager:
    """服务管理器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.log_dir = self.project_root / 'logs'
        self.pid_dir = self.project_root / '.pids'
        self.config_file = self.project_root / 'service_config.json'
        
        # 创建必要目录
        self.log_dir.mkdir(exist_ok=True)
        self.pid_dir.mkdir(exist_ok=True)
        
        # 配置日志
        self.setup_logging()
        
        # 服务配置
        self.services = {
            'backend': {
                'name': '后端API服务',
                'cwd': str(self.project_root / 'backend'),
                'command': 'if [ -d .venv ]; then source .venv/bin/activate; elif [ -d venv ]; then source venv/bin/activate; fi; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000',
                'shell': True,
                'port': 8000,
                'log_file': 'backend.log',
                'pid_file': 'backend.pid',
                'health_check': 'http://localhost:8000/api/dates'
            },
            'frontend': {
                'name': '前端Web服务',
                'cwd': str(self.project_root / 'frontend-client'),
                'command': 'npm start',
                'shell': True,
                'port': 3000,
                'log_file': 'frontend.log',
                'pid_file': 'frontend.pid',
                'health_check': 'http://localhost:3000'
            }
        }
        
        # 加载配置
        self.load_config()
    
    def setup_logging(self):
        """配置日志系统"""
        log_file = self.log_dir / f'manager_{datetime.now().strftime("%Y%m%d")}.log'
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置logger
        self.logger = logging.getLogger('ServiceManager')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                # 合并自定义配置
                for service, config in custom_config.items():
                    if service in self.services:
                        self.services[service].update(config)
    
    def save_config(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.services, f, indent=2, ensure_ascii=False)
    
    def get_pid(self, service: str) -> Optional[int]:
        """获取服务PID"""
        pid_file = self.pid_dir / self.services[service]['pid_file']
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # 检查进程是否存在
                os.kill(pid, 0)
                return pid
            except (ProcessLookupError, ValueError):
                pid_file.unlink()
        return None
    
    def save_pid(self, service: str, pid: int):
        """保存PID"""
        pid_file = self.pid_dir / self.services[service]['pid_file']
        pid_file.write_text(str(pid))
    
    def is_running(self, service: str) -> bool:
        """检查服务是否运行"""
        return self.get_pid(service) is not None
    
    def start_service(self, service: str) -> bool:
        """启动服务"""
        if self.is_running(service):
            self.logger.warning(f"{self.services[service]['name']} 已在运行")
            return False
        
        self.logger.info(f"启动 {self.services[service]['name']}...")
        
        config = self.services[service]
        log_file = self.log_dir / config['log_file']
        
        try:
            # 打开日志文件
            log_fd = open(log_file, 'a', encoding='utf-8')
            
            # 记录启动信息
            log_fd.write(f"\n{'='*60}\n")
            log_fd.write(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_fd.write(f"{'='*60}\n\n")
            log_fd.flush()
            
            # 启动进程
            process = subprocess.Popen(
                config['command'],
                shell=config.get('shell', False),
                cwd=config['cwd'],
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            
            # 保存PID
            self.save_pid(service, process.pid)
            
            self.logger.info(f"✓ {config['name']} 已启动 (PID: {process.pid})")
            self.logger.info(f"  日志文件: {log_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 启动失败: {e}")
            return False
    
    def stop_service(self, service: str, force: bool = False) -> bool:
        """停止服务"""
        pid = self.get_pid(service)
        if not pid:
            self.logger.warning(f"{self.services[service]['name']} 未运行")
            return False
        
        self.logger.info(f"停止 {self.services[service]['name']} (PID: {pid})...")
        
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGTERM)
            
            # 等待进程结束
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except ProcessLookupError:
                    break
            
            # 删除PID文件
            pid_file = self.pid_dir / self.services[service]['pid_file']
            if pid_file.exists():
                pid_file.unlink()
            
            self.logger.info(f"✓ {self.services[service]['name']} 已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 停止失败: {e}")
            return False
    
    def restart_service(self, service: str) -> bool:
        """重启服务"""
        self.logger.info(f"重启 {self.services[service]['name']}...")
        self.stop_service(service)
        time.sleep(2)
        return self.start_service(service)
    
    def status_service(self, service: str) -> Dict:
        """获取服务状态"""
        pid = self.get_pid(service)
        config = self.services[service]
        
        status = {
            'name': config['name'],
            'running': pid is not None,
            'pid': pid,
            'port': config.get('port'),
            'log_file': str(self.log_dir / config['log_file'])
        }
        
        if pid:
            try:
                # 获取进程信息
                import psutil
                proc = psutil.Process(pid)
                status['cpu_percent'] = proc.cpu_percent(interval=0.1)
                status['memory_mb'] = proc.memory_info().rss / 1024 / 1024
                status['start_time'] = datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        return status
    
    def show_status(self):
        """显示所有服务状态"""
        print("\n" + "="*70)
        print("📊 服务状态")
        print("="*70)
        
        for service in self.services:
            status = self.status_service(service)
            
            print(f"\n🔹 {status['name']}")
            print(f"   状态: {'✅ 运行中' if status['running'] else '❌ 未运行'}")
            
            if status['running']:
                print(f"   PID: {status['pid']}")
                print(f"   端口: {status.get('port', 'N/A')}")
                if 'cpu_percent' in status:
                    print(f"   CPU: {status['cpu_percent']:.1f}%")
                    print(f"   内存: {status['memory_mb']:.1f} MB")
                if 'start_time' in status:
                    print(f"   启动时间: {status['start_time']}")
            
            print(f"   日志: {status['log_file']}")
        
        print("\n" + "="*70)
    
    def start_all(self):
        """启动所有服务"""
        print("\n🚀 启动所有服务...\n")
        
        for service in ['backend', 'frontend']:
            self.start_service(service)
            time.sleep(2)
        
        time.sleep(3)
        self.show_status()
    
    def stop_all(self):
        """停止所有服务"""
        print("\n🛑 停止所有服务...\n")
        
        for service in ['frontend', 'backend']:
            self.stop_service(service)
        
        print("\n✓ 所有服务已停止")
    
    def restart_all(self):
        """重启所有服务"""
        print("\n🔄 重启所有服务...\n")
        self.stop_all()
        time.sleep(2)
        self.start_all()
    
    def tail_log(self, service: str, lines: int = 50):
        """查看日志"""
        log_file = self.log_dir / self.services[service]['log_file']
        
        if not log_file.exists():
            print(f"日志文件不存在: {log_file}")
            return
        
        print(f"\n{'='*70}")
        print(f"📋 {self.services[service]['name']} - 最近{lines}行日志")
        print(f"{'='*70}\n")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line, end='')
    
    def monitor(self, interval: int = 5):
        """监控服务"""
        print("\n🔍 开始监控服务 (按 Ctrl+C 停止)...\n")
        
        try:
            while True:
                os.system('clear' if os.name != 'nt' else 'cls')
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.show_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n✓ 监控已停止")


def main():
    """主函数"""
    project_root = Path(__file__).resolve().parents[2]
    manager = ServiceManager(str(project_root))
    
    if len(sys.argv) < 2:
        print("📖 股票分析系统 - 服务管理器")
        print("\n使用方法：")
        print("  python service_manager.py start [service]    # 启动服务")
        print("  python service_manager.py stop [service]     # 停止服务")
        print("  python service_manager.py restart [service]  # 重启服务")
        print("  python service_manager.py status             # 查看状态")
        print("  python service_manager.py logs <service>     # 查看日志")
        print("  python service_manager.py monitor            # 实时监控")
        print("\n服务名称: backend, frontend, all (所有服务)")
        print("\n示例：")
        print("  python service_manager.py start all          # 启动所有服务")
        print("  python service_manager.py status             # 查看状态")
        print("  python service_manager.py logs backend       # 查看后端日志")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    service = sys.argv[2].lower() if len(sys.argv) > 2 else 'all'
    
    if command == 'start':
        if service == 'all':
            manager.start_all()
        else:
            manager.start_service(service)
            time.sleep(2)
            manager.show_status()
    
    elif command == 'stop':
        if service == 'all':
            manager.stop_all()
        else:
            manager.stop_service(service)
    
    elif command == 'restart':
        if service == 'all':
            manager.restart_all()
        else:
            manager.restart_service(service)
            time.sleep(2)
            manager.show_status()
    
    elif command == 'status':
        manager.show_status()
    
    elif command == 'logs':
        if service == 'all':
            print("请指定服务: backend 或 frontend")
        else:
            lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            manager.tail_log(service, lines)
    
    elif command == 'monitor':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        manager.monitor(interval)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
