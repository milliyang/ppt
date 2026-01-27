# PPT - Paper Trade 模拟交易平台

轻量级模拟交易平台，支持多账户、实时行情、交易模拟、绩效分析、Webhook 信号接收。

> 未寻得简洁、解耦且架构清晰的现有方案，遂自研之。

🚀 ***ZuiLow** 一站式AI交易平台子项目，敬请期待！*

![交易界面](doc/pic/trade.png)

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 多账户 | 创建/切换/删除，支持多策略 |
| Webhook | 接收外部信号，兼容 TradingView |
| 交易模拟 | 滑点/手续费/部分成交 |
| 绩效分析 | 夏普比率/最大回撤/胜率 |
| 时间戳 | 对账户/交易信息上区块链时间戳,禁止作弊 |

---

## 快速开始

```bash
# 1. 配置环境
cp env.example .env
# 编辑 .env 设置 SECRET_KEY 和 WEBHOOK_TOKEN

# 2. 启动服务
./run_ppt_server.sh

# 或 Docker 部署
./deploy_ppt_server.sh upd
```

**访问**: http://localhost:11182

**默认用户**:
- admin : admin / admin123
- viewer: ppt / ppt

---

## 文档

| 文档 | 说明 |
|------|------|
| [功能概览](doc/feature_comparison.md) | 完整功能列表 |
| [API 使用](doc/api.usage.md) | API 端点和示例 |
| [Webhook](doc/webhook.md) | 外部信号接入 |
| [部署说明](doc/docker_setup.md) | Docker 部署详情 |
| [开发计划](doc/plan.md) | 功能状态和计划 |
| [OpenTimestamps](opents/readme.md) | 区块链时间戳服务 |

---

## 技术栈

- **后端**: Flask (Python)
- **数据库**: SQLite
- **行情数据**: yfinance
- **部署**: Docker
- **区块链**: OpenTimestamps (比特币区块链锚定)

---

## OpenTimestamps 集成

平台内置 OpenTimestamps 支持，为账户和交易数据创建防篡改时间戳：

- **每天多个时间戳**：支持不同市场收盘时间（如美股 16:00，港股 22:00）
- **自动调度**：可配置的定时任务自动创建时间戳
- **标签化时间戳**：可选标签区分不同市场或策略
- **文件格式**：`record_YYYY-MM-DD_HH-MM-SS.json` 或 `record_YYYY-MM-DD_label.json`

详细配置请参见 [OpenTimestamps 文档](opents/readme.md)。

---

## License

No License

