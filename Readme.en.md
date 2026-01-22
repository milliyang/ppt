# PPT - Paper Trade Platform

Lightweight paper trading platform with multi-account support, real-time quotes, trade simulation, performance analytics, and Webhook signal integration.

🚀 *Part of **ZuiLow** — One-stop AI quantitative trading platform, stay tuned!*

![Trading Interface](doc/pic/trade.png)

---

## Features

| Feature | Description |
|---------|-------------|
| Manual Trading | Web UI for buy/sell orders |
| Multi-Account | Create/switch/delete, multi-strategy support |
| Webhook | External signals, TradingView compatible |
| Trade Simulation | Slippage/commission/partial fills |
| Analytics | Sharpe ratio/max drawdown/win rate |
| Authentication | admin/viewer role-based access |

---

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
# Edit .env to set SECRET_KEY and WEBHOOK_TOKEN

# 2. Start server
./run_ppt_server.sh

# Or Docker deployment
./deploy_ppt_server.sh upd
```

**Access**: http://localhost:11182

**Default user**: ppt / ppt

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Features](doc/feature_comparison.md) | Full feature list |
| [API Usage](doc/api.usage.md) | API endpoints and examples |
| [Webhook](doc/webhook.md) | External signal integration |
| [Deployment](doc/docker_setup.md) | Docker setup details |
| [Roadmap](doc/plan.md) | Feature status and plans |

---

## Tech Stack

Flask / SQLite / yfinance / Docker

### License

No License
