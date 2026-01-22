# Paper Trade API 使用说明

> 更新时间: 2026-01-22

## 认证与权限

### 网页登录

所有网页和 API（除健康检查和 Webhook）都需要登录。

**角色权限**:
| 功能 | admin | viewer |
|------|-------|--------|
| 查看持仓/订单/成交 | ✅ | ✅ |
| 导出 CSV | ✅ | ✅ |
| 下单 | ✅ | ❌ |
| 账户管理 (创建/删除/重置) | ✅ | ❌ |
| 行情监控页面 | ✅ | ❌ |
| 测试页面 | ✅ | ❌ |
| 系统配置 | ✅ | ❌ |

### Webhook 认证

Webhook 使用独立的 Token 认证，**不受网页登录影响**：

```bash
# 设置环境变量后启用
export WEBHOOK_TOKEN=your-secret-token

# 请求时带 Token
curl -X POST http://localhost:11182/api/webhook \
  -H "X-Webhook-Token: your-secret-token" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'
```

### API 权限标记

| 标记 | 说明 |
|------|------|
| 🔓 | 无需认证 |
| 🔐 | 需要登录 |
| 👑 | 需要 admin |
| 🔑 | 需要 Webhook Token |

---

## 目录

- [基础 API](#基础-api)
  - [账户](#账户)
  - [交易](#交易)
  - [导出](#导出)
- [绩效分析 API](#绩效分析-api)
- [模拟配置 API](#模拟配置-api)
- [Webhook API](#webhook-api)
  - [标准格式](#标准格式)
  - [TradingView 格式](#tradingview-格式)
  - [指定账户](#指定账户)
  - [带认证](#带认证-设置-webhook_token-后)
- [多策略部署](#多策略部署)
  - [方案1: 多账户](#方案1-多账户推荐)
  - [方案2: 多实例](#方案2-多实例完全隔离)
- [Python 示例](#python-示例)
- [TradingView 警报配置](#tradingview-警报配置)
- [参数说明](#参数说明)

---

## 基础 API

### 账户

```bash
# 获取当前账户
curl http://localhost:11182/api/account

# 账户列表
curl http://localhost:11182/api/accounts

# 创建账户
curl -X POST http://localhost:11182/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"name":"策略A","capital":500000}'

# 切换账户
curl -X POST http://localhost:11182/api/accounts/switch \
  -H "Content-Type: application/json" \
  -d '{"name":"策略A"}'

# 重置账户
curl -X POST http://localhost:11182/api/account/reset
```

### 交易

```bash
# 下单
curl -X POST http://localhost:11182/api/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'

# 持仓列表
curl http://localhost:11182/api/positions

# 订单历史
curl http://localhost:11182/api/orders

# 成交记录
curl http://localhost:11182/api/trades
```

### 净值更新

```bash
# 用实时市价更新当天净值 (影子账户必用)
curl -X POST http://localhost:11182/api/equity/update
```

**响应示例：**
```json
{
  "message": "已更新 2 个账户",
  "results": [
    {"account": "default", "status": "ok", "positions": 3, "quote_failed": []},
    {"account": "策略A", "status": "ok", "positions": 1, "quote_failed": ["INVALID"]}
  ],
  "failed_symbols": ["INVALID"],
  "tip": "获取失败的股票将使用成本价计算"
}
```

**内置定时器（推荐）：**

应用启动时自动运行，通过环境变量配置：

```bash
# .env 文件
# 格式: "时:分,时:分,时:分"
EQUITY_UPDATE_SCHEDULE=5:0,21:30,0:0   # 美股 (默认)
EQUITY_UPDATE_SCHEDULE=9:30,12:0,16:0  # 港股
EQUITY_UPDATE_SCHEDULE=off              # 禁用定时器
```

启动日志：
```
[Scheduler] 添加定时任务: 5:0
[Scheduler] 添加定时任务: 21:30
[Scheduler] 添加定时任务: 0:0
[Scheduler] 定时任务已启动
```

**备选：系统 cron**
```bash
# 美股：每天 3 次 (北京时间)
30 21 * * 1-5 curl -s -X POST http://localhost:11182/api/equity/update
0 0 * * 2-6 curl -s -X POST http://localhost:11182/api/equity/update
0 5 * * 2-6 curl -s -X POST http://localhost:11182/api/equity/update
```

### 导出

```bash
# 导出交易记录
curl -O http://localhost:11182/api/export/trades

# 导出净值历史
curl -O http://localhost:11182/api/export/equity
```

---

## 绩效分析 API

```bash
# 完整分析 (包含所有指标)
curl http://localhost:11182/api/analytics

# 夏普比率
curl http://localhost:11182/api/analytics/sharpe

# 最大回撤
curl http://localhost:11182/api/analytics/drawdown

# 交易统计 (胜率/盈亏比)
curl http://localhost:11182/api/analytics/trades

# 持仓分析 (集中度)
curl http://localhost:11182/api/analytics/positions
```

**完整分析响应示例**
```json
{
  "sharpe": {
    "sharpe_ratio": 1.25,
    "annual_return": 15.5,
    "volatility": 12.4,
    "data_days": 30
  },
  "drawdown": {
    "max_drawdown": 8.5,
    "max_drawdown_amount": 85000,
    "peak_date": "2026-01-10",
    "trough_date": "2026-01-15",
    "current_drawdown": 2.3
  },
  "trade_stats": {
    "total_trades": 25,
    "win_trades": 15,
    "lose_trades": 10,
    "win_rate": 60.0,
    "profit_factor": 1.8,
    "avg_win": 1200,
    "avg_loss": -800,
    "net_profit": 10000
  },
  "positions": {
    "total_positions": 5,
    "position_pct": 75.5,
    "concentration": {
      "top1": 35.2,
      "top3": 72.5,
      "hhi": 2150
    }
  }
}
```

---

## 模拟配置 API

```bash
# 获取当前模拟配置
curl http://localhost:11182/api/simulation

# 重载配置文件
curl -X POST http://localhost:11182/api/simulation/reload
```

**响应示例**
```json
{
  "preset": "us_retail",
  "slippage": {
    "enabled": true,
    "mode": "percentage",
    "value": 0.05
  },
  "commission": {
    "enabled": true,
    "mode": "percentage",
    "rate": 0.001,
    "minimum": 1.0
  },
  "partial_fill": {
    "enabled": false,
    "threshold": 10000
  },
  "latency": {
    "enabled": true,
    "min_ms": 50,
    "max_ms": 200
  }
}
```

---

## 行情监控 API (Watchlist)

管理关注列表，监控 yfinance 服务状态。

**Web 界面**: http://localhost:11182/watchlist

### 基本操作

```bash
# 获取关注列表
curl http://localhost:11182/api/watchlist

# 添加到关注列表
curl -X POST http://localhost:11182/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL"}'

# 从关注列表移除
curl -X DELETE http://localhost:11182/api/watchlist/AAPL

# 清空关注列表
curl -X POST http://localhost:11182/api/watchlist/clear
```

### 行情刷新

```bash
# 刷新所有关注股票行情
curl -X POST http://localhost:11182/api/watchlist/refresh

# 测试 yfinance 服务状态
curl http://localhost:11182/api/watchlist/test
```

**刷新响应示例：**
```json
{
  "message": "刷新完成: 3 成功, 1 失败",
  "ok": 3,
  "fail": 1,
  "results": [
    {"symbol": "AAPL", "status": "ok", "price": 185.5, "name": "Apple Inc."},
    {"symbol": "INVALID", "status": "error", "error": "无效代码"}
  ]
}
```

**服务测试响应：**
```json
{
  "status": "ok",
  "message": "yfinance 服务正常",
  "test_symbol": "AAPL",
  "price": 185.5,
  "latency_ms": 320
}
```

---

## Webhook API

### 标准格式

```bash
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'
```

### TradingView 格式

```bash
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","action":"buy","contracts":100,"price":185}'
```

### 指定账户

```bash
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185,"account":"策略A"}'
```

### 带认证 (设置 WEBHOOK_TOKEN 后)

```bash
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: your-secret" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'
```

---

## 多策略部署

### 方案1: 多账户（推荐）

多个策略共享一个服务，通过 Webhook 的 `account` 参数区分：

```bash
# 1. 创建策略账户
curl -X POST http://localhost:11182/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"name":"均线策略","capital":500000}'

curl -X POST http://localhost:11182/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"name":"动量策略","capital":500000}'

# 2. 策略信号指定账户（不影响其他账户）
# 均线策略 → 均线策略账户
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185,"account":"均线策略"}'

# 动量策略 → 动量策略账户
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"TSLA","side":"buy","qty":50,"price":250,"account":"动量策略"}'
```

**特点**：
- 共享一个服务、一个数据文件
- Webhook 指定 `account` 不会切换全局当前账户
- Web UI 切换账户查看不同策略

### 方案2: 多实例（完全隔离）

不同策略运行独立的服务实例，完全隔离：

```bash
# 创建数据目录
mkdir -p db/strategy_a db/strategy_b

# 策略 A - 端口 11182
DATA_FILE=db/strategy_a/paper_trade.json PORT=11182 python app.py

# 策略 B - 端口 11183
DATA_FILE=db/strategy_b/paper_trade.json PORT=11183 python app.py
```

**Docker 方式**：

```yaml
# docker-compose.multi.yml
version: '3.8'

services:
  strategy-a:
    build: .
    ports:
      - "11182:11182"
    environment:
      - PORT=11182
      - DATA_FILE=db/strategy_a.json
    volumes:
      - ./db:/app/db

  strategy-b:
    build: .
    ports:
      - "11183:11182"
    environment:
      - PORT=11182
      - DATA_FILE=db/strategy_b.json
    volumes:
      - ./db:/app/db
```

```bash
docker-compose -f docker-compose.multi.yml up -d
```

**特点**：
- 完全独立的数据文件
- 独立的 Web UI（不同端口）
- 可独立重启、重置

| 对比 | 方案1 多账户 | 方案2 多实例 |
|------|-------------|-------------|
| 资源占用 | 低 | 较高 |
| 数据隔离 | 逻辑隔离 | 物理隔离 |
| 管理复杂度 | 简单 | 较复杂 |
| 适用场景 | 日常多策略 | 完全独立运行 |

---

## Python 示例

```python
import requests

BASE_URL = 'http://localhost:11182'

# 下单
def place_order(symbol, side, qty, price):
    return requests.post(f'{BASE_URL}/api/orders', json={
        'symbol': symbol,
        'side': side,
        'qty': qty,
        'price': price
    }).json()

# Webhook 信号
def send_signal(symbol, side, qty, price, account=None):
    data = {'symbol': symbol, 'side': side, 'qty': qty, 'price': price}
    if account:
        data['account'] = account
    return requests.post(f'{BASE_URL}/api/webhook', json=data).json()

# 获取持仓
def get_positions():
    return requests.get(f'{BASE_URL}/api/positions').json()

# 获取账户
def get_account():
    return requests.get(f'{BASE_URL}/api/account').json()

# 使用示例
print(place_order('AAPL', 'buy', 100, 185))
print(get_positions())
```

---

## TradingView 警报配置

**Webhook URL:**
```
http://your-server:11182/api/webhook
```

**消息内容:**
```json
{
  "ticker": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "contracts": {{strategy.order.contracts}},
  "price": {{close}}
}
```

---

## 参数说明

| 参数 | 别名 | 说明 |
|------|------|------|
| symbol | ticker | 股票代码 (见下方格式) |
| side | action | buy/sell |
| qty | contracts, quantity | 数量 |
| price | limit_price | 价格 |
| account | - | 指定账户 (可选) |
| token | X-Webhook-Token | 认证令牌 (可选) |

---

## 股票代码格式

支持 **yfinance 格式** 和 **富途格式**，内部统一转换为 yfinance 格式：

| 市场 | yfinance 格式 | 富途格式 |
|------|--------------|---------|
| 美股 | `AAPL` | `US.AAPL` |
| 港股 | `0700.HK` | `HK.0700` |
| A股(沪) | `600519.SS` | `SH.600519` |
| A股(深) | `000001.SZ` | `SZ.000001` |

**示例：**
```bash
# 美股 - 两种写法都支持
curl "http://localhost:11182/api/quote/AAPL"
curl "http://localhost:11182/api/quote/US.AAPL"

# 港股
curl "http://localhost:11182/api/quote/0700.HK"
curl "http://localhost:11182/api/quote/HK.0700"
```
