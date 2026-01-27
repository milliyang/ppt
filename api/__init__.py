"""
API 模块

所有 Blueprint:
- account: 账户管理
- trade: 交易/行情
- watchlist: 行情监控
- analytics_api: 绩效分析
- webhook: Webhook 信号
- test: 测试工具
- opentimestamps: OpenTimestamps 时间戳服务
"""

from .account import bp as account_bp
from .trade import bp as trade_bp
from .watchlist import bp as watchlist_bp
from .analytics_api import bp as analytics_bp
from .webhook import bp as webhook_bp
from .test import bp as test_bp
from opents.api import bp as ots_bp

all_blueprints = [
    account_bp,
    trade_bp,
    watchlist_bp,
    analytics_bp,
    webhook_bp,
    test_bp,
    ots_bp,
]

__all__ = [
    'account_bp', 'trade_bp', 'watchlist_bp',
    'analytics_bp', 'webhook_bp', 'test_bp', 'ots_bp',
    'all_blueprints'
]
