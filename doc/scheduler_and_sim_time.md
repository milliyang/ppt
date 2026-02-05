# PPT 定时任务与仿真时间 (stime)

## 1. 为什么 PPT 没有“按 stime 走”？

PPT 保持独立性：既有 Webhook 接收外部下单，也有**自己的定时任务**（净值更新、OTS 时间戳等）。原先这些任务只用**系统时钟**：

- **APScheduler** 使用 `CronTrigger(hour=5, minute=0)` 等：触发条件是**真实时间**到达 5:00、21:30 等。
- 设置 `SIMULATION_TIME_URL` 后，PPT 仅用 stime 做两件事：
  - 主题变为“仿真”样式（红底）
  - `GET /api/sim_now` 从 stime 拉当前时间给前端展示  
- **定时任务仍按系统时钟触发**，所以仿真时会出现“服务器真实日期”的净值点（例如 2026/1/28、1/29、1/30 被写成 100 万、0%），和 webhook 按 sim 日期写的点混在一起。

因此：PPT 之前没有“进入 simulate 模式”让**任务时间**按 stime 走，只有**展示**用了 stime。

## 2. APScheduler 是怎么触发的？

- **调度器**：`BackgroundScheduler` 在后台线程里跑，按配置的 trigger 检查是否该执行。
- **CronTrigger**：和 cron 一样，用**系统当前时间**。例如 `CronTrigger(hour=5, minute=0)` 表示“每天**真实** 5:00 执行一次”。
- **IntervalTrigger**：按**时间间隔**执行，例如 `IntervalTrigger(seconds=30)` 表示每 30 秒执行一次（也是按系统时钟计间隔）。

因此：不配置 stime 时，PPT 的“几点几分”任务完全是**真实时间**驱动，和仿真时间无关。

## 3. 仿真模式下 PPT 被 stime 驱动（当前实现）

为保持“PPT 独立但仿真时时间跟 stime 一致”，当设置了 **SIMULATION_TIME_URL** 时：

- **净值更新**不再用 `CronTrigger`，改为：
  - 使用 **IntervalTrigger(seconds=30)**，每 30 秒跑一次。
  - 每次请求 stime 的 `GET /now`，得到当前 **sim 时间**。
  - 若 sim 时间**已经跨过**配置的某个时刻（如 5:0、21:30、0:0），且该 (sim 日期, 时, 分) 尚未执行过，则执行一次净值更新，并传入 **as_of_date = 当前 sim 日期** 写 `equity_history`。
- 这样：
  - 仿真时“几点更新净值”由 **stime 的 sim 时间**决定，不会再用真实 5:00/21:30 写错日期。
  - PPT 仍独立：不依赖 zuilow 或 stime 的 tick 回调，只轮询 stime 的“当前时间”。

**环境变量**：

| 变量 | 说明 |
|------|------|
| `SIMULATION_TIME_URL` | stime 的 base URL（如 `http://stime:11185`）。设置后主题为仿真、/api/sim_now 拉 stime，且净值更新改为“按 stime 驱动”。 |
| `EQUITY_UPDATE_SCHEDULE` | 净值更新时刻，如 `5:0,21:30,0:0`。仿真时表示“sim 时间到达这些时刻时”执行。 |

**OTS 时间戳任务**：目前仿真模式下仍按系统时钟的 CronTrigger 触发；若需要也可改为按 stime 驱动（同样用轮询 sim 时间跨过配置时刻即可）。

---

## 4. 推荐：stime 多 tick URL（先 zuilow 再 PPT）

收益曲线按 sim 日期更新、且不依赖 PPT 轮询时，可用 **stime 多 tick URL**：

- **stime** 设置 `TICK_URLS=http://zuilow:11180/api/scheduler/tick,http://ppt:11182/api/scheduler/tick`（逗号分隔，顺序先 zuilow 后 PPT）。
- 每次 advance 后，stime 按顺序 POST 各 URL，并带请求头 **X-Simulation-Time**（当前 sim 时间）。
- **ZuiLow** 收到 tick 后跑策略、下单、写信号、执行；**PPT** 收到 tick 后调用 `POST /api/scheduler/tick`，按 X-Simulation-Time 的日期为所有账户写一条净值（`update_equity_history(..., as_of_date=sim_date)`）。
- **PPT 仿真时从 DMS 取价**：若设置 **DMS_BASE_URL**（DMS 的 base URL），tick 时 PPT 会对每个账户的持仓标的请求 DMS 的 `POST /api/dms/read/batch`（带 as_of=sim_datetime），取最后一根 K 线 Close 作为价格计算持仓市值并写净值。未设置 DMS_BASE_URL 或某标的取价失败时，仍用成本价计算。

这样：先触发 zuilow 再触发 paper 更新净值，收益曲线按 sim 日期正确，且净值基于 DMS 的 as_of 日价格；效率上每步多一次 HTTP 到 PPT，但逻辑清晰。PPT 若仍设 `SIMULATION_TIME_URL`，轮询 stime 的净值任务可保留作备用，或关闭（`EQUITY_UPDATE_SCHEDULE=off`）仅依赖 stime tick。

**环境变量（tick 取价）**：

| 变量 | 说明 |
|------|------|
| `DMS_BASE_URL` | DMS API base URL（如 `http://dms:11183`）。设置后 tick 时从 DMS read/batch 拉取 as_of 日期的股票价格（最后一根 K 线 Close）用于净值计算。 |

---

## 5. 净值历史里的记录从哪里来？日期从哪来？

写入 `equity_history`（净值历史）的**触发点**和**日期来源**如下。

| 触发点 | 日期来源 | 说明 |
|--------|----------|------|
| **POST /api/scheduler/tick** | 请求头 **X-Simulation-Time** 的日期 | stime 在「Advance + Trigger」时，**每步** advance 后对 TICK_URLS 里的每个 URL（含 PPT）发一次 POST，并带当前 sim 时间。PPT 用该日写一条净值。 |
| PPT 内部调度（仿真） | stime **GET /now** 返回的 sim 日期 | 每 30 秒轮询 stime，当 sim 时间跨过配置时刻（如 5:0、21:30、0:0）时写一条，日期 = 当前 sim 日期。 |
| PPT 内部调度（非仿真） | **服务器当天** `datetime.now().date()` | CronTrigger 到点执行，日期 = 服务器真实日期。 |
| Webhook 成交后 | 请求头 **X-Simulation-Time** 的日期（有则用） | 仿真下单时 ZuiLow 会带该头；PPT 用订单时间的日期写一条净值。 |
| 前端「更新净值」按钮（POST /api/equity/update） | 仿真时从 stime GET /now 取日期，否则服务器当天 | 仿真模式下不再用系统日期，避免 2026/1/31 等混入曲线。 |
| 下单后（POST /api/orders） | 请求头 X-Simulation-Time 的日期（有则用） | 与 webhook 一致，有头则用 sim 日期写净值。 |
| 创建账户（POST /api/accounts）、重置账户（POST /api/account/reset） | 仿真时从 stime GET /now 取日期，否则服务器当天 | 初始净值/重置后一条净值不再用系统日期，避免 2026/1/31 1000000 0 0 混入曲线。 |

**为什么会出现 2026/1/28、2026/1/29、2026/1/30、2026/1/31 且净值=1000000、盈亏=0？**

- 这些**日期**来自 **stime 的当前仿真时间**：在 stime 页面点了「Advance + Trigger ZuiLow tick」且 advance 了多天（例如 4 天）时，stime 会**每步**（每 advance 一天）对 PPT 调用一次 **POST /api/scheduler/tick**，请求头里 **X-Simulation-Time** 依次为 2026-01-28、2026-01-29、2026-01-30、2026-01-31。
- 所以**每步都会在 PPT 里写一条净值**；若该日没有成交、账户无持仓或持仓未变，算出来的就是「初始资金 + 0 盈亏」，即 1000000 / 0 / 0%。

**总结**：多出来的那几笔记录是 **stime「Advance + Trigger」每步调用 PPT tick** 触发的；**日期**一律来自 **stime 的仿真时间**（X-Simulation-Time 或 GET /now），不是服务器真实日期。
