# Paper Trade 开发计划

> 更新时间: 2026-01-22

## 项目状态: **Ready for Deploy** 🚀

---

## 功能状态

### 核心功能 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 手动下单 | ✅ | 买入/卖出界面 |
| 账户概览 | ✅ | 现金、持仓市值、盈亏 |
| 持仓管理 | ✅ | 持仓列表、成本价、实时市值 |
| 交易记录 | ✅ | 成交历史 |
| 数据持久化 | ✅ | SQLite 数据库 |

### 增强功能 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 多账户 | ✅ | 创建/切换/删除账户 |
| 收益曲线 | ✅ | 每日净值图表 (平滑曲线+渐变) |
| 导出 CSV | ✅ | 交易记录/净值导出 |
| 实时行情 | ✅ | ZuiLow 取价（模拟/真实同一逻辑） |
| Webhook | ✅ | 接收外部信号自动下单 |
| 股票代码格式 | ✅ | 支持标准格式 + 富途格式 |
| 定时更新净值 | ✅ | APScheduler 内置定时器 |
| 行情监控 | ✅ | Watchlist 管理 + 服务状态检测 |
| 图表交互 | ✅ | 悬浮显示详情 (日期/净值/收益) |
| 性能优化 | ✅ | Analytics 按需计算，100天数据秒响应 |
| **用户认证** | ✅ | admin/viewer 角色，文件配置 |

### 交易模拟 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 滑点模拟 | ✅ | 支持百分比/固定/随机模式 |
| 手续费模拟 | ✅ | 支持百分比/固定/阶梯费率 |
| 部分成交 | ✅ | 大单可配置分批成交 |
| 延迟模拟 | ✅ | 可配置响应延迟 |
| 配置文件 | ✅ | `config/simulation.yaml` |
| 预设模板 | ✅ | 理想/美股/港股/高波动 |

### 绩效分析 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 夏普比率 | ✅ | 风险调整收益指标 |
| 最大回撤 | ✅ | 峰谷回撤计算 |
| 胜率/盈亏比 | ✅ | 交易效率指标 |
| 持仓分析 | ✅ | 集中度/HHI 指数 |

### 不提供

| 功能 | 原因 |
|------|------|
| 止损/止盈订单 | 保持简洁 |
| WebSocket 推送 | 轮询足够 |
| Python SDK | 直接用 requests |
| 回测引擎 | ZuiLow 提供 |

---

## 部署清单 ✅

### 文件检查

| 文件/目录 | 状态 | 说明 |
|------|------|------|
| `app.py` | ✅ | 主入口 (~250 行) |
| `core/` | ✅ | 核心模块 (db, analytics, simulation, utils, auth) |
| `api/` | ✅ | API Blueprint 模块 (account, trade, watchlist 等) |
| `docker/` | ✅ | Docker 相关 (Dockerfile, docker-compose.yml) |
| `config/simulation.yaml` | ✅ | 模拟配置 |
| `config/users.yaml` | ✅ | 用户配置 (admin/viewer) |
| `static/` | ✅ | 前端文件 |
| `requirements.txt` | ✅ | Python 依赖 |
| `start_ppt.sh` | ✅ | 本地启动脚本 (Linux/Mac) |
| `deploy_ppt_server.sh` | ✅ | Docker 部署脚本 |
| `env.example` | ✅ | 环境变量模板 |

### 部署命令

```bash
# 1. 复制环境配置
cp env.example .env

# 2. 修改配置 (可选)
vim .env

# 3. Docker 部署
./deploy_ppt_server.sh upd

# 4. 验证
curl http://localhost:11182/api/health
```

### 生产环境建议

| 项目 | 建议 |
|------|------|
| 用户 | 修改 `config/users.yaml` 密码 |
| Webhook | 设置 `WEBHOOK_TOKEN` |
| 调试 | `FLASK_DEBUG=False` |
| 日志 | 配置 `LOG_FILE` |
| 数据 | 挂载 `db/` 目录到宿主机 |
| 备份 | 定期备份 SQLite 数据库 |

---

## API 端点

### 账户

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/account` | 账户信息 |
| POST | `/api/account/reset` | 重置账户 |
| GET | `/api/accounts` | 账户列表 |
| POST | `/api/accounts` | 创建账户 |
| POST | `/api/accounts/switch` | 切换账户 |
| DELETE | `/api/accounts/{name}` | 删除账户 |

### 交易

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/positions` | 持仓列表 |
| GET | `/api/orders` | 订单历史 |
| POST | `/api/orders` | 下单 |
| GET | `/api/trades` | 成交记录 |

### 行情

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/quote/{symbol}` | 单个股票行情 |
| GET | `/api/quotes?symbols=A,B` | 批量行情 |

### 数据

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/equity` | 净值历史 |
| GET | `/api/export/trades` | 导出交易 CSV |
| GET | `/api/export/equity` | 导出净值 CSV |

### 绩效分析

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/analytics` | 完整绩效分析 |
| GET | `/api/analytics/sharpe` | 夏普比率 |
| GET | `/api/analytics/drawdown` | 最大回撤 |
| GET | `/api/analytics/trades` | 交易统计 |
| GET | `/api/analytics/positions` | 持仓分析 |

### 模拟配置

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/simulation` | 当前配置 |
| POST | `/api/simulation/reload` | 重载配置 |

### Webhook

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/webhook` | 接收外部信号 |

**Webhook 请求格式**
```json
{
  "symbol": "AAPL",
  "action": "buy",
  "qty": 100,
  "price": 185.0,
  "token": "可选认证令牌"
}
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Flask + Gunicorn + Eventlet |
| 实时通信 | Flask-SocketIO |
| 数据存储 | SQLite |
| 行情数据 | ZuiLow |
| 部署 | Docker |
| 端口 | 11182 |

---

## 部署

```bash
# 本地启动
./start_ppt.sh   # 或 Windows: .\start_ppt.ps1

# Docker 部署
./deploy_ppt_server.sh upd
```

访问: http://localhost:11182
