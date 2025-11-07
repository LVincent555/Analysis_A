# 股票分析系统 v0.2.2

## ⚠️ 重要警告

**部署前必读：**
1. **backend/app/database.py 包含数据库配置，绝对不能提交到Git！**
2. **data/*.json 文件包含服务器特定状态，不能覆盖！**
3. **所有.md文档说明都应放在 docs/ 目录，保持根目录整洁！**
4. **详细说明请阅读：[配置文件管理和常见错误](docs/⚠️重要-配置文件管理和常见错误.md)**

---

## 📋 项目简介

A股股票数据分析系统，支持多种分析功能和可视化展示。

### 主要功能

- ✅ 最新热点分析（支持前100/200/400/600/800/1000个股票选择）
- ✅ 股票查询
- ✅ 行业趋势分析（支持前1000/2000/3000/5000名选择）
- ✅ 排名跳变（支持搜索）
- ✅ 稳步上升（支持搜索）

---

## 🚀 快速开始

### 本地开发

```bash
# 1. 克隆项目
git clone <repository-url>
cd stock_analysis_app

# 2. 配置数据库
cd backend/app
cp database.py.example database.py
nano database.py  # 修改数据库配置

# 3. 启动后端
cd ../..
bash start_all.sh dev

# 4. 访问
# 前端: http://localhost:3000
# 后端: http://localhost:8000
```

### 服务器部署

**⚠️ 部署前必须先备份服务器配置！**

```bash
# 1. 备份配置
cp backend/app/database.py ~/database.py.backup
cp data/data_import_state.json ~/data_import_state.json.backup

# 2. 拉取代码
git pull origin main

# 3. 恢复配置（如果需要）
cp ~/database.py.backup backend/app/database.py

# 4. 启动服务
bash start_all.sh  # 默认生产模式
```

详细部署指南：[服务器部署指南](docs/服务器部署指南.md)

---

## 📚 文档

### 必读文档
- [配置文件管理和常见错误](docs/⚠️重要-配置文件管理和常见错误.md) ⭐️ 必读
- [数据管理使用指南](docs/数据管理使用指南.md) ⭐️ 数据导入必读

### 部署相关
- [服务器部署指南](docs/服务器部署指南.md)
- [更新日志](CHANGELOG.md)

### 功能说明
- [前N个股票选择功能](docs/最新热点前N个股票选择功能.md)
- [行业趋势前N名功能](docs/行业分析前N名选择功能.md)
- [去重机制技术说明](docs/去重机制技术说明.md)

### 技术详解
- [智能去重技术详解](docs/智能去重技术详解.md) ⭐️ 推荐阅读

---

## 🔧 配置说明

### 数据库配置

**方法1：使用 database.py（简单）**

```bash
cd backend/app
cp database.py.example database.py
nano database.py
```

修改：
```python
DB_HOST = "localhost"              # 数据库地址
DB_PORT = "5432"                   # 端口
DB_NAME = "stock_analysis"         # 数据库名
DB_USER = "postgres"               # 用户名
DB_PASSWORD = "your_password"      # 密码
```

**方法2：使用环境变量（推荐）**

```bash
cd backend
cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_analysis
DB_USER=postgres
DB_PASSWORD=your_password
EOF
```

---

## 🛠️ 技术栈

### 后端
- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Uvicorn

### 前端
- React 18
- TailwindCSS
- Recharts
- Lucide Icons
- Axios

---

## 📦 项目结构

```
stock_analysis_app/
├── backend/              # 后端代码
│   ├── app/
│   │   ├── database.py.example    # 数据库配置模板 ⚠️
│   │   ├── database.py            # 数据库配置（不提交）⚠️
│   │   ├── routers/              # API路由
│   │   ├── services/             # 业务逻辑
│   │   └── models/               # 数据模型
│   └── requirements.txt
├── frontend/             # 前端代码
│   ├── build/           # 编译后的文件（提交到Git）
│   └── src/
├── data/                # 数据文件（不提交）⚠️
├── docs/                # 文档
├── deploy/              # 部署配置
└── README.md
```

---

## 🔐 安全注意事项

### 绝对不能提交到Git的文件

- ❌ `backend/app/database.py` - 包含数据库密码
- ❌ `backend/.env` - 环境变量
- ❌ `data/*.json` - 服务器状态文件
- ❌ `logs/` - 日志文件

### 检查方法

```bash
# 部署前检查
git status

# 应该看不到上述文件
```

---

## 🐛 故障排查

### 服务无法启动

```bash
# 查看日志
tail -100 logs/backend.log

# 测试数据库连接
cd backend
python3 -c "from app.database import test_connection; test_connection()"
```

### 数据库连接失败

1. 检查 `backend/app/database.py` 配置
2. 测试数据库连接：`psql -h <host> -U <user> -d <database>`
3. 检查防火墙和网络

---

## 📄 License

MIT

---

## 👥 贡献

欢迎提交Issue和Pull Request

---

**再次提醒：部署前必读 [配置文件管理和常见错误](docs/⚠️重要-配置文件管理和常见错误.md)**
