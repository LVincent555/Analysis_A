# 🚀 Stock Analysis App - Docker 部署文档

## 📋 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [运维管理](#运维管理)
- [故障排查](#故障排查)

---

## 🖥️ 系统要求

### 最低配置
- **CPU**: 2核
- **内存**: 2GB
- **存储**: 10GB
- **系统**: Linux (Ubuntu 20.04+, CentOS 8+)

### 软件依赖
- Docker 20.10+
- Docker Compose 2.0+

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd stock_analysis_app
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**必须修改的配置：**
```env
DATABASE_PASSWORD=your_strong_password_here
```

### 3. 准备数据文件

将Excel数据文件放到 `./data` 目录：

```bash
mkdir -p data
cp /path/to/your/*.xlsx ./data/
```

### 4. 一键部署

```bash
# 给脚本执行权限
chmod +x deploy.sh backup.sh

# 执行部署
./deploy.sh
```

选择 **选项1** 进行全新部署。

### 5. 访问应用

- **前端**: http://your-server-ip
- **API文档**: http://your-server-ip/api/docs
- **数据库**: your-server-ip:5432

---

## ⚙️ 详细配置

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_NAME | 数据库名称 | stock_analysis |
| DATABASE_USER | 数据库用户 | stock_user |
| DATABASE_PASSWORD | 数据库密码 | *必须设置* |
| WEB_PORT | Web服务端口 | 80 |

### 手动部署步骤

如果不使用 `deploy.sh`，可以手动执行：

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 查看状态
docker-compose ps
```

### 服务说明

#### PostgreSQL (stock_db)
- **端口**: 5432
- **数据卷**: postgres_data
- **内存限制**: 600MB
- **配置优化**: 适配2G内存

#### Backend (stock_api)
- **端口**: 8000 (内部)
- **Workers**: 2个Gunicorn worker
- **内存限制**: 500MB
- **自动功能**:
  - 等待数据库就绪
  - 自动导入Excel数据（首次）
  - 预加载缓存

#### Nginx (stock_web)
- **端口**: 80
- **功能**:
  - 静态文件服务
  - API反向代理
  - Gzip压缩
- **内存限制**: 100MB

---

## 🔧 运维管理

### 日常操作

#### 查看服务状态
```bash
docker-compose ps
```

#### 查看日志
```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f nginx
```

#### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

#### 停止服务
```bash
# 停止服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除所有（包括数据）
docker-compose down -v
```

### 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建
docker-compose build

# 3. 重启服务
docker-compose up -d
```

### 数据管理

#### 导入新数据

```bash
# 1. 将新的Excel文件复制到data目录
cp /path/to/new/*.xlsx ./data/

# 2. 进入后端容器
docker-compose exec backend bash

# 3. 执行导入脚本
python scripts/import_data_robust.py

# 4. 清除缓存
python clear_cache.py

# 5. 退出容器
exit
```

#### 备份数据库

```bash
# 执行备份脚本
./backup.sh

# 备份文件保存在 ./backups 目录
```

#### 恢复数据库

```bash
# 从备份恢复
gunzip -c ./backups/stock_analysis_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T postgres psql -U stock_user stock_analysis
```

### 监控

#### 资源使用

```bash
# 查看容器资源占用
docker stats

# 查看磁盘使用
docker system df
```

#### 健康检查

```bash
# 检查所有服务健康状态
docker-compose ps

# 测试API
curl http://localhost/api/dates

# 测试前端
curl http://localhost
```

---

## 🐛 故障排查

### 服务无法启动

#### 1. 检查端口占用

```bash
# 检查80端口
sudo netstat -tulpn | grep :80

# 检查5432端口
sudo netstat -tulpn | grep :5432
```

**解决方案**: 修改 `.env` 中的 `WEB_PORT`

#### 2. 检查内存

```bash
free -h
```

**解决方案**: 
- 添加Swap分区
- 减少worker数量（修改 `backend/Dockerfile`）

#### 3. 查看容器日志

```bash
docker-compose logs --tail=100 backend
```

### 数据库连接失败

#### 检查数据库状态

```bash
docker-compose exec postgres pg_isready -U stock_user
```

#### 检查网络

```bash
docker network ls
docker network inspect stock_analysis_app_stock_network
```

### 前端无法访问

#### 检查Nginx配置

```bash
# 进入容器
docker-compose exec nginx sh

# 测试配置
nginx -t

# 查看日志
cat /var/log/nginx/error.log
```

### 后端API错误

#### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 手动运行Python脚本测试
python -c "from app.database import SessionLocal; db = SessionLocal(); print('DB OK')"

# 查看环境变量
env | grep DATABASE
```

### 清理Docker资源

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes
```

---

## 📊 性能优化

### PostgreSQL优化

编辑 `docker-compose.yml` 中的环境变量：

```yaml
environment:
  POSTGRES_SHARED_BUFFERS: "512MB"  # 增加缓冲
  POSTGRES_EFFECTIVE_CACHE_SIZE: "1.5GB"
```

### Backend优化

修改 `backend/Dockerfile` 中的workers数量：

```dockerfile
CMD ["gunicorn", "-w", "4", ...]  # 增加到4个worker
```

### 添加Swap分区

```bash
# 创建2G swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 🔒 安全建议

1. **修改默认密码**: 使用强密码
2. **限制端口访问**: 配置防火墙规则
3. **启用HTTPS**: 使用Let's Encrypt证书
4. **定期备份**: 设置cron自动备份
5. **监控日志**: 定期检查异常访问

---

## 📞 技术支持

- **项目文档**: 查看 `PROJECT_OVERVIEW.md`
- **API文档**: http://your-server-ip/api/docs
- **日志位置**: `docker-compose logs`

---

## 📝 常用命令速查

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 进入容器
docker-compose exec backend bash

# 备份数据
./backup.sh

# 更新部署
./deploy.sh
```
