# 股票重复出现分析系统

一个前后端分离的Web应用，用于分析股票数据表格中重复出现的个股。

## 项目结构

```
stock_analysis_app/
├── backend/              # FastAPI后端
│   ├── main.py          # API主程序
│   └── requirements.txt # Python依赖
├── frontend/            # React前端
│   ├── public/         # 静态资源
│   ├── src/            # React源码
│   │   ├── App.js     # 主应用组件
│   │   ├── index.js   # 入口文件
│   │   └── index.css  # 样式文件
│   ├── package.json   # Node依赖
│   ├── tailwind.config.js
│   └── postcss.config.js
└── README.md
```

## 功能特性

### 后端 (FastAPI)
- ✅ RESTful API 设计
- ✅ 自动扫描Excel数据文件
- ✅ 支持主板和双创两种模式
- ✅ 支持2/3/5/7/14天多时间周期分析
- ✅ CORS支持
- ✅ 数据验证

### 前端 (React + TailwindCSS)
- ✅ 现代化响应式UI设计
- ✅ 实时数据展示
- ✅ 交互式周期和板块切换
- ✅ 美观的表格和数据可视化
- ✅ 加载状态和错误处理

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 1. 后端安装和启动

```bash
# 进入后端目录
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 启动后端服务器 (默认端口: 8000)
python main.py
```

后端API将在 http://localhost:8000 启动

API文档: http://localhost:8000/docs

### 2. 前端安装和启动

```bash
# 进入前端目录
cd frontend

# 安装Node依赖
npm install

# 启动开发服务器 (默认端口: 3000)
npm start
```

前端应用将在 http://localhost:3000 启动

## API接口说明

### 获取可用日期
```
GET /api/dates
```

### 分析指定周期
```
GET /api/analyze/{period}?board_type={main|all}
```
参数:
- `period`: 2, 3, 5, 7, 14
- `board_type`: main (主板) 或 all (含双创)

### 获取所有周期分析
```
GET /api/analyze/all/{board_type}
```

## 数据文件要求

数据文件必须放在项目根目录的上一级，文件命名格式：
```
YYYYMMDD_data_sma_feature_color.xlsx
```

例如：
- `20251103_data_sma_feature_color.xlsx`
- `20251104_data_sma_feature_color.xlsx`
- `20251105_data_sma_feature_color.xlsx`

## 分析规则

### 2天和3天周期
- 股票必须在最近N天**连续出现**（恰好N次）

### 5天、7天和14天周期
- 股票在**最新一天出现**
- 且在最近N天内**至少再出现1次**（总共至少2次）
- **不要求连续出现**

### 主板 vs 双创
- **主板模式**: 排除 300/301/688/920 开头的股票
- **双创模式**: 包含所有股票（创业板、科创板）

## 技术栈

### 后端
- FastAPI - 现代化Python Web框架
- Pandas - 数据处理
- Uvicorn - ASGI服务器
- Pydantic - 数据验证

### 前端
- React 18 - UI框架
- TailwindCSS - CSS框架
- Axios - HTTP客户端
- Lucide React - 图标库

## 开发说明

### 后端开发
```bash
# 开发模式启动（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发
```bash
# 开发模式
npm start

# 生产构建
npm run build
```

## 生产部署

### 后端部署
```bash
# 使用gunicorn + uvicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### 前端部署
```bash
# 构建生产版本
npm run build

# 将 build/ 目录部署到静态文件服务器（如Nginx）
```

## 注意事项

1. **CORS配置**: 生产环境请修改后端 `allow_origins` 为具体域名
2. **数据路径**: 确保数据文件在正确的位置
3. **端口冲突**: 如果端口被占用，请修改配置
4. **Excel文件**: 运行前请关闭所有Excel文件

## 截图

（前端界面包含）
- 板块类型选择（主板/双创）
- 分析周期选择（2/3/5/7/14天）
- 实时数据表格展示
- 股票代码、出现次数、排名信息
- 响应式设计，支持移动端

## 许可证

MIT License

## 版本历史

### v1.0.0 (2025-11-05)
- ✨ 初始版本发布
- ✨ 前后端分离架构
- ✨ 支持多周期分析
- ✨ 主板和双创两种模式
