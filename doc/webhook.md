# Webhook 技术说明

## 什么是 Webhook？

Webhook 是一种**反向 API**（也叫回调 URL）机制：

| 传统 API | Webhook |
|----------|---------|
| 客户端主动请求服务端 | 服务端主动推送到客户端 |
| 轮询模式（定时查询） | 事件驱动（有事件才通知） |
| 客户端 → 服务端 | 服务端 → 客户端 |

```
传统模式:
┌────────┐  请求   ┌────────┐
│ 客户端  │ ──────→ │ 服务端  │
│        │ ←────── │        │
└────────┘  响应   └────────┘

Webhook 模式:
┌────────┐  订阅   ┌────────┐
│ 我的服务 │ ←───── │ 第三方  │  (TradingView, 交易所等)
│ (接收端) │        │ (发送端) │
└────────┘ 当事件  └────────┘
           发生时
           POST 数据
```

## 工作原理

1. **注册** - 你告诉第三方你的接收地址（Webhook URL）
2. **等待** - 你的服务保持运行，监听该地址
3. **触发** - 当事件发生（如交易信号），第三方向你的地址发送 HTTP POST
4. **处理** - 你的服务收到数据后执行相应动作

## 交易场景应用

```
┌─────────────┐     信号触发      ┌─────────────┐
│ TradingView │  ─────────────→  │ Paper Trade │
│   策略警报   │   POST /webhook  │   自动下单   │
└─────────────┘                  └─────────────┘

┌─────────────┐     模型预测      ┌─────────────┐
│  量化模型   │  ─────────────→  │ Paper Trade │
│  (Python)   │   POST /webhook  │   自动下单   │
└─────────────┘                  └─────────────┘
```

---

## Paper Trade Webhook 接口

### 端点

```
POST /api/webhook
```

### 请求格式

支持多种格式，自动兼容：

**标准格式**
```json
{
  "symbol": "AAPL",
  "side": "buy",
  "qty": 100,
  "price": 185.50
}
```

**TradingView 格式**
```json
{
  "ticker": "AAPL",
  "action": "buy",
  "contracts": 100,
  "price": 185.50
}
```

**指定账户**
```json
{
  "symbol": "AAPL",
  "side": "buy",
  "qty": 100,
  "price": 185.50,
  "account": "策略A"
}
```

### 参数说明

| 参数 | 别名 | 必填 | 说明 |
|------|------|------|------|
| symbol | ticker | ✅ | 股票代码 |
| side | action | ✅ | `buy` / `sell` |
| qty | contracts, quantity | ❌ | 数量，默认 100 |
| price | limit_price | ✅ | 价格 |
| account | - | ❌ | 目标账户，默认当前账户 |
| token | - | ❌ | 认证令牌（如启用） |

**Side 映射**
| 输入值 | 映射为 |
|--------|--------|
| buy, long, buy_to_open | buy |
| sell, short, sell_to_close, close | sell |

### 响应

**成功** (含模拟信息)
```json
{
  "status": "ok",
  "order": {
    "id": 1,
    "symbol": "AAPL",
    "side": "buy",
    "requested_qty": 100,
    "filled_qty": 100,
    "requested_price": 185.50,
    "exec_price": 185.59,
    "value": 18559,
    "time": "2026-01-22T15:30:00",
    "status": "filled",
    "source": "webhook"
  },
  "simulation": {
    "slippage": 0.09,
    "commission": 18.56,
    "fill_rate": 1.0,
    "total_cost": 18577.56
  }
}
```

**失败**
```json
{
  "error": "资金不足: 需要 18577.56, 可用 10000"
}
```

### 认证机制

Webhook 使用**独立的 Token 认证**，与网页用户登录系统互不影响：

| 接口 | 认证方式 | 说明 |
|------|---------|------|
| `/api/webhook` | `WEBHOOK_TOKEN` | 独立 Token，策略专用 |
| `/api/orders` (POST) | 用户登录 + admin 角色 | 网页手动下单 |

> **重要**: 策略通过 Webhook 下单不需要用户登录，只需 Token 正确（或未设置 Token）即可执行。

**启用 Token 认证** (推荐生产环境)：

```bash
# 生成 Token (任选一种)
python -c "import secrets; print(secrets.token_urlsafe(32))"  # 推荐
openssl rand -base64 32
uuidgen

# .env 或环境变量
export WEBHOOK_TOKEN=your-secret-token
```

请求时带 Token：

```bash
# Header 方式 (推荐)
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: your-secret-token" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'

# Body 方式
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185,"token":"your-secret-token"}'
```

**未设置 Token**: 任何请求都可下单（仅限内网/测试环境）

---

## 使用示例

### Python 发送信号

```python
import requests

WEBHOOK_URL = 'http://localhost:11182/api/webhook'
WEBHOOK_TOKEN = 'your-secret-token'  # 可选，未设置 Token 则留空

def send_signal(symbol, side, qty, price, account=None):
    data = {
        'symbol': symbol,
        'side': side,
        'qty': qty,
        'price': price
    }
    if account:
        data['account'] = account
    
    headers = {'Content-Type': 'application/json'}
    if WEBHOOK_TOKEN:
        headers['X-Webhook-Token'] = WEBHOOK_TOKEN
    
    resp = requests.post(WEBHOOK_URL, json=data, headers=headers)
    return resp.json()

# 买入 AAPL
send_signal('AAPL', 'buy', 100, 185.50)

# 卖出到指定账户
send_signal('TSLA', 'sell', 50, 250, account='策略B')
```

### TradingView 警报配置

1. 创建策略警报
2. 设置 Webhook URL：
   ```
   http://your-server:11182/api/webhook
   ```
3. 消息内容：
   ```json
   {
     "ticker": "{{ticker}}",
     "action": "{{strategy.order.action}}",
     "contracts": {{strategy.order.contracts}},
     "price": {{close}}
   }
   ```

### curl 测试

```bash
# 买入
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"buy","qty":100,"price":185}'

# 卖出
curl -X POST http://localhost:11182/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","side":"sell","qty":100,"price":190}'
```

---

## 优缺点

### 优点

| 优点 | 说明 |
|------|------|
| 实时性 | 事件发生即刻通知，无延迟 |
| 低资源 | 不需要轮询，节省请求 |
| 解耦 | 信号源与执行端分离 |
| 通用 | HTTP 标准协议，任何语言可调用 |

### 注意事项

| 事项 | 说明 |
|------|------|
| 公网暴露 | 需有公网 IP 或内网穿透 |
| **安全** | **生产环境必须设置 `WEBHOOK_TOKEN`** |
| 幂等性 | 需处理重复请求 |
| 超时 | 发送方可能有超时限制 |
| 独立认证 | Webhook Token 与网页登录互不影响 |

---

## 相关资源

- [TradingView Webhook 文档](https://www.tradingview.com/support/solutions/43000529348-about-webhooks/)
- [Webhook.site](https://webhook.site/) - 在线测试工具
