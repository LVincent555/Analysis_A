# DPRS Review 通用套件

> **DPRS**: Problem → Suggestion → Decision → Result
> 一套轻量级的决策流程管理系统，适用于研究项目、软件开发、团队协作等场景。

---

## 什么是 DPRS？

DPRS 是一个四阶段决策流程框架：

| 阶段 | 缩写 | 用途 |
|------|------|------|
| **Problem** | PRB | 记录问题现象、影响、初步假设，不做方案 |
| **Suggestion** | SUG | 提出备选方案，拆解步骤、成本、风险 |
| **Decision** | DEC | 明确选择的方案、范围、责任、时间 |
| **Result** | RES | 记录执行结果、回归、遗留风险 |

### 核心原则

1. **状态透明**：每个文档头部标注状态（OPEN/SOLVED/DEFERRED 等）
2. **单向流转**：PRB → SUG → DEC → RES，失败可回 SUG 补充
3. **证据优先**：PRB 记录事实，RES 附指标/日志
4. **小步快迭代**：避免长时间停留在"开放问题"

---

## 快速开始

### 方式一：使用初始化脚本

```bash
# 在新项目中创建 review 目录结构
python init.py /path/to/your/project

# 可选：指定自定义目录名
python init.py /path/to/your/project --name docs/review
```

### 方式二：手动复制

1. 将本套件复制到你的项目中
2. 重命名为 `review/`（或你喜欢的名字）
3. 删除 `init.py` 和 `README.md`（如果不需要）
4. 根据项目需要编辑 `META/INDEX.md`

---

## 目录结构

```
review/
├── META/                    # 元信息目录
│   ├── INDEX.md             # 文档索引
│   ├── SKILL-DPRS.md        # DPRS 核心规范
│   └── 规范-PRB-引用提问流.md  # 外部咨询规范（可选）
│
├── PRB/                     # 问题记录
├── SUG/                     # 方案建议
├── DEC/                     # 决策记录
└── RES/                     # 结果/复盘
```

---

## 文档模板

所有模板位于 `templates/` 目录：

- `PRB.md` - 问题陈述模板
- `SUG.md` - 方案建议模板
- `DEC.md` - 决策模板
- `RES.md` - 结果/复盘模板
- `INDEX.md` - 文档索引模板

---

## 状态枚举

```
[OPEN]      - 进行中
[SOLVED]    - 已解决
[DEFERRED]  - 延后处理
[OBSERVED]  - 观察中
[OBSOLETE]  - 已废弃
[ACTIVE]    - 持续生效
```

---

## 推荐标签集

```
{实验} {架构} {理论} {写作} {审稿} {数据} {自动化} {研究方向} {引用}
```

---

## 双层架构（可选）

对于大型项目，可采用双层 Review 架构：

- **顶层 Review**：处理跨模块/跨子项目的通用问题
- **子项目 Review**：处理单个模块内部的具体问题

详见 [SKILL-DPRS.md](./META/SKILL-DPRS.md)。

---

## 许可

MIT License - 自由使用、修改、分发。
