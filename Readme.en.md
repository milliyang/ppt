# PPT - Paper Trade Platform

A lightweight paper trading platform supporting multi-account management, real-time market data, trade simulation, performance analytics, and webhook signal reception.

> Built from scratch due to lack of clean, decoupled, and well-architected existing solutions.

🚀 ***Sub-project of ZuiLow** all-in-one AI trading platform. Stay tuned!*

![Trading Interface](doc/pic/trade.png)

---

## Core Features

| Feature | Description |
|---------|-------------|
| Multi-Account | Create/switch/delete accounts, support multiple strategies |
| Webhook | Receive external signals, compatible with TradingView |
| Trade Simulation | Slippage/commission/partial fill simulation |
| Performance Analytics | Sharpe ratio/max drawdown/win rate |
| Blockchain Timestamps | OpenTimestamps integration for tamper-proof account/trade records. Prevents cheating |

---

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
# Edit .env to set SECRET_KEY and WEBHOOK_TOKEN

# 2. Start server
./run_ppt_server.sh

# Or deploy with Docker
./deploy_ppt_server.sh upd
```

**Access**: http://localhost:11182

**Default User**:
- admin : admin / admin123
- viewer: ppt / ppt

---

## Documentation

| Document | Description |
|----------|-------------|
| [Feature Overview](doc/feature_comparison.md) | Complete feature list |
| [API Usage](doc/api.usage.md) | API endpoints and examples |
| [Webhook](doc/webhook.md) | External signal integration |
| [Deployment Guide](doc/docker_setup.md) | Docker deployment details |
| [Development Plan](doc/plan.md) | Feature status and roadmap |
| [OpenTimestamps](opents/readme.md) | Blockchain timestamp service |

---

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Market Data**: yfinance
- **Deployment**: Docker
- **Blockchain**: OpenTimestamps (Bitcoin blockchain anchoring)

---

## OpenTimestamps Integration

The platform includes built-in OpenTimestamps support for creating tamper-proof timestamps of account and trade data:

- **Multiple Timestamps per Day**: Support for different market close times (e.g., US market at 16:00, HK market at 22:00)
- **Automatic Scheduling**: Configurable cron jobs for automatic timestamp creation
- **Labeled Timestamps**: Optional labels to distinguish different markets or strategies
- **File Format**: `record_YYYY-MM-DD_HH-MM-SS.json` or `record_YYYY-MM-DD_label.json`

See [OpenTimestamps Documentation](opents/readme.md) for detailed configuration.

---

## License

No License
