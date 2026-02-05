# PPT 功能概览

> Paper Trade 功能状态与设计决策
> 
> 更新时间: 2026-01-22 (v2)

## 功能矩阵

| 功能分类 | 功能项 | 状态 | 说明 |
|----------|--------|------|------|
| **订单** | 市价单 | ✅ | |
| | 限价单 | ✅ | |
| | 止损/止盈 | ❌ | 策略层处理 |
| **模拟** | 滑点 | ✅ | 百分比/固定/随机 |
| | 手续费 | ✅ | 百分比/固定/阶梯 |
| | 部分成交 | ✅ | 可配置 |
| | 延迟 | ✅ | 可配置 |
| **分析** | 收益曲线 | ✅ | |
| | 夏普比率 | ✅ | |
| | 最大回撤 | ✅ | |
| | 胜率/盈亏比 | ✅ | |
| | 持仓分析 | ✅ | HHI 集中度 |
| **账户** | 多账户 | ✅ | |
| | 导出 CSV | ✅ | |
| **接口** | REST API | ✅ | |
| | Webhook | ✅ | TradingView 兼容 |
| **安全** | 用户登录 | ✅ | admin/viewer 角色 |
| | API 权限 | ✅ | 按角色控制 |
| | Webhook Token | ✅ | 可选认证 |
| **数据** | 行情查询 | ✅ | ZuiLow（模拟/真实同一逻辑） |
| | 股票代码格式 | ✅ | 股票代码 + 富途格式 |
| | 定时更新净值 | ✅ | APScheduler 内置 |
| | 行情监控 | ✅ | Watchlist + 服务状态 |

---

## 新增功能 (2026-01)

### 富途股票代码支持

支持两种格式，自动转换：

| 市场 | 标准格式 | 富途格式 |
|------|--------------|---------|
| 美股 | `AAPL` | `US.AAPL` |
| 港股 | `0700.HK` | `HK.0700` |
| A股(沪) | `600519.SS` | `SH.600519` |
| A股(深) | `000001.SZ` | `SZ.000001` |

### 净值自动更新

内置 APScheduler 定时任务，自动用实时价格更新净值：

```bash
# .env 配置
EQUITY_UPDATE_SCHEDULE=5:0,21:30,0:0   # 美股时间 (默认)
EQUITY_UPDATE_SCHEDULE=9:30,12:0,16:0  # 港股时间
EQUITY_UPDATE_SCHEDULE=off              # 禁用
```

也可手动调用 API：
```bash
curl -X POST http://localhost:11182/api/equity/update
```

### 行情监控 (Watchlist)

管理关注股票列表，监控 ZuiLow 行情服务：

**Web 界面**: http://localhost:11182/watchlist

```bash
# 测试服务状态
curl http://localhost:11182/api/watchlist/test

# 添加关注
curl -X POST http://localhost:11182/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL"}'

# 刷新行情
curl -X POST http://localhost:11182/api/watchlist/refresh
```

### 收益曲线图表增强

- **X 轴日期标签**: 显示日期刻度
- **鼠标悬浮交互**: 显示详细信息（日期、净值、收益率）
- **高亮指示线**: 悬浮时显示垂直参考线和数据点

### 性能优化

- **Analytics 按需计算**: 绩效分析不再每 30 秒自动刷新
- **快速刷新模式**: 30 秒自动刷新仅更新基本数据（账户、持仓、成交、图表）
- **测试数据支持**: 100+ 天数据也能快速响应

### 用户认证

基于文件配置的简单用户系统：

**角色权限**:
| 功能 | admin | viewer |
|------|-------|--------|
| 查看持仓/订单/成交 | ✅ | ✅ |
| 导出 CSV | ✅ | ✅ |
| 下单 | ✅ | ❌ |
| 账户管理 | ✅ | ❌ |
| 行情监控 | ✅ | ❌ |
| 测试页面 | ✅ | ❌ |

**配置文件**: `config/users.yaml`
```yaml
users:
  leo:
    password: "pbkdf2:sha256:..."  # werkzeug 哈希
    role: admin
  guest:
    password: "pbkdf2:sha256:..."
    role: viewer
```

**生成密码哈希**:
```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your_password'))"
```

---

## 设计决策

**有意不实现的功能：**

| 功能 | 原因 |
|------|------|
| 止损/止盈订单 | 保持简洁，策略层自行处理 |
| 风控规则 | 由调用方控制 |
| WebSocket 推送 | 轮询 30s 足够，避免复杂度 |
| Python SDK | requests 直接调用即可 |
| 回测引擎 | ZuiLow 已提供 |
| 历史 K 线 | ZuiLow 提供 |

**设计原则：** 保持简单、够用即可，避免过度工程化。

---

## 配置文件

| 文件 | 用途 |
|------|------|
| `config/users.yaml` | 用户配置 (用户名/密码/角色) |
| `config/simulation.yaml` | 交易模拟参数 (滑点/手续费/部分成交) |
| `.env` | 环境变量 (端口/Token/定时任务) |

---

## 参考项目

| 项目 | 链接 |
|------|------|
| PaperBroker | github.com/philipodonnell/paperbroker |
| QuantConnect | quantconnect.com |
