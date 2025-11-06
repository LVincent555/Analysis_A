# 📝 Stock Analysis App - Claude配置指南

> **给Claude Code或其他AI助手的特别说明**

---

## 🎯 你的任务

帮助用户在**2核2G Linux服务器**上使用Docker部署这个股票分析系统。

---

## 📚 必读文档

在开始之前，请先阅读这些文档以理解项目：

1. **PROJECT_OVERVIEW.md** ⭐️ 最重要
   - 完整的项目说明
   - 技术架构
   - 数据库设计
   - API端点
   
2. **QUICK_START.md**
   - 5分钟快速部署流程
   
3. **README_DEPLOY.md**
   - 详细部署文档
   - 故障排查

---

## 🏗️ 系统架构（快速了解）

```
3个Docker容器：
┌──────────────┐
│ Nginx:80     │  前端React + 反向代理
└──────┬───────┘
       │
┌──────┴───────┐
│ Backend:8000 │  FastAPI + Python
└──────┬───────┘
       │
┌──────┴───────┐
│ Postgres:5432│  PostgreSQL数据库
└──────────────┘
```

---

## 📁 关键文件位置

### 部署配置
- `docker-compose.yml` - Docker编排
- `.env.example` - 环境变量模板（需复制为.env）
- `deploy.sh` - 一键部署脚本
- `backup.sh` - 备份脚本

### 代码
- `backend/` - Python后端代码
- `frontend/` - React前端代码
- `docker/nginx/` - Nginx配置

### 数据
- `data/` - Excel数据文件目录
- `sql/` - 数据库初始化脚本

---

## 🚀 标准部署流程

### 1. 环境检查

```bash
# 检查Docker
docker --version  # 需要20.10+
docker-compose --version  # 需要2.0+

# 检查内存
free -h  # 至少2G
```

### 2. 配置.env

```bash
cp .env.example .env
nano .env
```

**必须修改**:
```env
DATABASE_PASSWORD=设置一个强密码
```

### 3. 准备数据

```bash
# 将Excel文件放到data目录
# 文件格式: 20251106_data_sma_feature_color.xlsx
ls -la data/
```

### 4. 执行部署

```bash
chmod +x deploy.sh backup.sh
./deploy.sh
# 选择 1 (全新部署)
```

### 5. 验证

```bash
# 检查容器状态
docker-compose ps

# 检查日志
docker-compose logs -f

# 测试访问
curl http://localhost/api/dates
curl http://localhost
```

---

## 🔧 常见问题处理

### 问题1: 端口被占用

**现象**: 80端口已被使用

**解决**:
```bash
# 编辑.env
nano .env
# 修改: WEB_PORT=8080

# 重新部署
./deploy.sh
```

### 问题2: 内存不足

**现象**: 容器被OOM Kill

**解决**:
```bash
# 添加Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 问题3: 数据未导入

**现象**: 前端显示"无数据"

**解决**:
```bash
# 进入后端容器
docker-compose exec backend bash

# 手动导入
python scripts/import_data_robust.py

# 退出
exit
```

### 问题4: 前端404

**现象**: Nginx返回404

**原因**: 前端构建失败

**解决**:
```bash
# 重新构建
docker-compose down
docker-compose build --no-cache nginx
docker-compose up -d
```

### 问题5: 数据库连接失败

**解决**:
```bash
# 检查数据库
docker-compose exec postgres pg_isready -U stock_user

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

---

## 📊 配置文件说明

### docker-compose.yml 关键配置

```yaml
services:
  postgres:
    mem_limit: 600m        # 内存限制
    environment:
      POSTGRES_SHARED_BUFFERS: "256MB"  # 可调整
      
  backend:
    mem_limit: 500m        # 内存限制
    depends_on:
      postgres:
        condition: service_healthy  # 等待DB就绪
        
  nginx:
    mem_limit: 100m        # 内存限制
    ports:
      - "${WEB_PORT:-80}:80"  # 端口映射
```

### backend/Dockerfile 关键点

```dockerfile
# 使用轻量镜像
FROM python:3.10-slim

# 2个Gunicorn worker（针对2核）
CMD ["gunicorn", "-w", "2", ...]
```

### docker-entrypoint.sh 启动逻辑

```bash
1. 等待PostgreSQL就绪
2. 检查是否需要导入数据
3. 清除旧缓存
4. 启动应用
```

---

## 🛠️ 手动操作

### 进入容器

```bash
# 后端
docker-compose exec backend bash

# 数据库
docker-compose exec postgres psql -U stock_user stock_analysis

# Nginx
docker-compose exec nginx sh
```

### 清除缓存

```bash
docker-compose exec backend python clear_cache.py
```

### 导入新数据

```bash
# 复制Excel到容器
docker cp new_file.xlsx stock_api:/app/data/

# 执行导入
docker-compose exec backend python scripts/import_data_robust.py
```

### 备份还原

```bash
# 备份
./backup.sh

# 还原
gunzip -c backups/stock_analysis_backup_YYYYMMDD.sql.gz | \
  docker-compose exec -T postgres psql -U stock_user stock_analysis
```

---

## 📝 代码修改指南

### 修改后端API

1. 编辑 `backend/app/routers/*.py`
2. 重新构建: `docker-compose build backend`
3. 重启: `docker-compose restart backend`

### 修改前端

1. 编辑 `frontend/src/App.js`
2. 重新构建: `docker-compose build nginx`
3. 重启: `docker-compose restart nginx`

### 修改数据库

1. 编辑 `backend/app/db_models.py`
2. 删除旧数据: `docker-compose down -v`
3. 重新部署: `./deploy.sh` 选择1

---

## 🔍 调试技巧

### 查看详细日志

```bash
# 后端日志
docker-compose logs -f backend | grep -i error

# 数据库日志
docker-compose logs postgres | tail -100

# Nginx访问日志
docker-compose exec nginx cat /var/log/nginx/access.log
```

### 监控资源

```bash
# 实时监控
docker stats

# 查看磁盘
docker system df
```

### 测试API

```bash
# 获取日期
curl http://localhost/api/dates

# 热点分析
curl "http://localhost/api/analysis/period?period=3&board_type=main"

# 健康检查
curl http://localhost/api/docs
```

---

## ⚠️ 重要提醒

### 1. 内存管理
- 总内存限制: ~1.2GB (留800MB给系统)
- 如果OOM，优先添加Swap

### 2. 数据安全
- 定期备份: `./backup.sh`
- 数据在Docker卷: `postgres_data`
- Excel文件在: `./data`

### 3. 性能优化
- Worker数量 = CPU核数 (当前2个)
- 数据库缓存已优化为2G内存
- Nginx已启用Gzip

### 4. 升级策略
```bash
# 无数据丢失升级
git pull
docker-compose build
docker-compose up -d
```

---

## 🎯 部署检查清单

部署前：
- [ ] Docker已安装 (20.10+)
- [ ] Docker Compose已安装 (2.0+)
- [ ] `.env`已配置密码
- [ ] Excel文件已放入`./data`
- [ ] 端口80可用
- [ ] 至少2G内存可用

部署后：
- [ ] 3个容器都是"Up"状态
- [ ] `curl http://localhost`返回HTML
- [ ] `curl http://localhost/api/dates`返回JSON
- [ ] 前端页面可正常访问
- [ ] 数据已导入（查看日志）

---

## 💡 快速命令参考

```bash
# 部署
./deploy.sh

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启
docker-compose restart

# 停止
docker-compose down

# 备份
./backup.sh

# 进入容器
docker-compose exec backend bash

# 清除缓存
docker-compose exec backend python clear_cache.py

# 监控资源
docker stats
```

---

## 📞 需要帮助时

1. 先查看日志: `docker-compose logs -f`
2. 检查容器状态: `docker-compose ps`
3. 查看系统资源: `free -h` 和 `df -h`
4. 参考 README_DEPLOY.md 故障排查章节

---

**最后建议**: 按照 QUICK_START.md 的5步流程操作，遇到问题查询 README_DEPLOY.md 的故障排查部分。

**祝部署顺利！🚀**
