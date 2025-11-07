# 🐚 Shell脚本使用指南

## 📋 启动脚本说明

项目提供了完整的Shell和Python两套启动方案，可以根据需要选择。

---

## 🚀 Shell版本（推荐Linux服务器使用）

### 1. start_all.sh - 一键启动所有服务 ⭐

**最常用的脚本！一个命令启动前后端所有服务。**

```bash
chmod +x start_all.sh
./start_all.sh
```

**功能：**
- ✅ 自动后台启动后端和前端
- ✅ 自动创建logs目录并记录日志
- ✅ 显示服务PID和状态
- ✅ 提供访问地址和管理命令
- ✅ 服务在后台运行，不占用终端

**输出示例：**
```
============================================================
🚀 一键启动股票分析系统
============================================================

📍 项目目录: /root/DA/Analysis_A
📋 将启动以下服务:
   1️⃣  后端API  (http://localhost:8000)
   2️⃣  前端应用 (http://localhost:3000)

============================================================

▶ 启动后端服务...
✓ 后端已启动 (PID: 12345)
  日志: /root/DA/Analysis_A/logs/backend.log

▶ 启动前端服务...
✓ 前端已启动 (PID: 12346)
  日志: /root/DA/Analysis_A/logs/frontend.log

⏳ 等待服务完全启动...

============================================================
✅ 所有服务已启动！
============================================================

🌐 访问地址:
  • 后端API:  http://localhost:8000
  • API文档:  http://localhost:8000/docs
  • 前端应用: http://localhost:3000
```

### 2. start_backend.sh - 启动后端

**单独启动后端服务（前台运行）**

```bash
chmod +x start_backend.sh
./start_backend.sh
```

**用途：**
- 开发调试时单独启动后端
- 前台运行，可以直接看到日志
- Ctrl+C 可以停止

### 3. start_frontend.sh - 启动前端

**单独启动前端服务（前台运行）**

```bash
chmod +x start_frontend.sh
./start_frontend.sh
```

**用途：**
- 开发调试时单独启动前端
- 前台运行，可以直接看到日志
- Ctrl+C 可以停止

---

## 🐍 Python版本（跨平台，Windows/Linux都可用）

### 1. start_all.py - 一键启动

```bash
# Linux/Mac
python3 start_all.py

# Windows
python start_all.py
```

### 2. start_backend.py - 启动后端

```bash
python3 start_backend.py  # Linux/Mac
python start_backend.py   # Windows
```

### 3. start_frontend.py - 启动前端

```bash
python3 start_frontend.py  # Linux/Mac
python start_frontend.py   # Windows
```

---

## 🎯 使用建议

### Linux服务器 → 使用Shell版本

```bash
# 一键启动（后台运行）
./start_all.sh

# 查看日志
tail -f logs/backend.log
tail -f logs/frontend.log

# 停止服务
./stop.sh
```

**优势：**
- ✅ 服务自动后台运行
- ✅ 不占用终端
- ✅ 自动记录日志
- ✅ 断开SSH也继续运行

### Windows本地开发 → 使用Python版本

```bash
python start_all.py
```

**优势：**
- ✅ 跨平台兼容
- ✅ 自动打开新窗口（Windows）
- ✅ 便于调试

---

## 🔧 完整的服务管理命令

### 快捷命令（根目录）

```bash
./start_all.sh   # 一键启动
./stop.sh        # 停止服务
./restart.sh     # 重启服务
./status.sh      # 查看状态
./logs.sh backend  # 查看后端日志
./logs.sh frontend # 查看前端日志
```

### 完整管理（服务管理器）

```bash
# 使用服务管理器
python3 deploy/scripts/service_manager.py start all
python3 deploy/scripts/service_manager.py stop all
python3 deploy/scripts/service_manager.py status
python3 deploy/scripts/service_manager.py logs backend
python3 deploy/scripts/service_manager.py monitor

# 快捷方式
./service.sh start all
./service.sh status
```

---

## 📊 对比总结

| 功能 | start_all.sh | start_all.py | service_manager.py |
|------|-------------|-------------|-------------------|
| **后台运行** | ✅ 是 | ❌ 否 | ✅ 是 |
| **日志管理** | ✅ 自动 | ❌ 手动 | ✅ 完整 |
| **Windows支持** | ❌ 否 | ✅ 是 | ❌ 否 |
| **状态监控** | ⚠️ 基础 | ❌ 无 | ✅ 完整 |
| **PID管理** | ⚠️ 显示 | ❌ 无 | ✅ 完整 |
| **启动速度** | ⚡ 快 | ⚡ 快 | ⏱️ 稍慢 |
| **功能完整性** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 💡 最佳实践

### 开发阶段
```bash
# 方式1: 前台运行（便于调试）
./start_backend.sh   # 终端1
./start_frontend.sh  # 终端2

# 方式2: Python版本
python3 start_all.py
```

### 测试阶段
```bash
# 快速启动测试
./start_all.sh
./stop.sh
```

### 生产环境
```bash
# 使用服务管理器
./service.sh start all
./service.sh status
./service.sh monitor  # 实时监控
```

---

## 🆘 常见问题

### Q1: Shell脚本没有执行权限？

```bash
chmod +x *.sh
```

### Q2: start_all.sh启动后如何查看日志？

```bash
tail -f logs/backend.log
tail -f logs/frontend.log

# 或使用
./logs.sh backend
./logs.sh frontend
```

### Q3: 如何确认服务是否启动？

```bash
./status.sh

# 或者
ps aux | grep -E "uvicorn|node"
netstat -tlnp | grep -E "3000|8000"
```

### Q4: start_all.sh启动后如何停止？

```bash
./stop.sh

# 或手动
kill <PID>
```

### Q5: 服务启动失败怎么办？

```bash
# 查看日志
cat logs/backend.log
cat logs/frontend.log

# 检查端口占用
netstat -tlnp | grep -E "3000|8000"

# 杀死占用进程
sudo kill -9 <PID>
```

---

## 🎓 高级用法

### 1. 修改启动端口

编辑 `start_all.sh`:
```bash
# 修改这一行
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. 使用screen保持后台

```bash
screen -S stock
./start_all.sh
# Ctrl+A+D 分离
screen -r stock  # 重新连接
```

### 3. 设置开机自启

添加到crontab:
```bash
crontab -e

# 添加
@reboot cd /path/to/project && ./start_all.sh >> logs/startup.log 2>&1
```

---

## 📚 相关文档

- **服务管理**: `服务管理手册.md`
- **部署指南**: `部署使用手册.md`
- **脚本清单**: `SCRIPTS_LIST.md`

---

**💡 推荐**: Linux服务器使用 `./start_all.sh`，简单直接高效！
