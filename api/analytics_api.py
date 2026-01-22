"""
绩效分析 & 交易模拟配置 API

路由:
- GET  /api/analytics           - 完整绩效分析 (登录)
- GET  /api/analytics/sharpe    - 夏普比率 (登录)
- GET  /api/analytics/drawdown  - 最大回撤 (登录)
- GET  /api/analytics/trades    - 交易统计 (登录)
- GET  /api/analytics/positions - 持仓分析 (登录)
- GET  /api/simulation          - 交易模拟配置 (登录)
- POST /api/simulation/reload   - 重载模拟配置 (admin)
"""
from flask import Blueprint, jsonify, request
from core import db as database
from core import analytics
from core import simulation
from core.utils import get_quotes_batch
from core.auth import admin_required, login_required_api

bp = Blueprint('analytics_api', __name__)


@bp.route('/api/simulation', methods=['GET'])
@login_required_api
def get_simulation_config():
    """获取交易模拟配置状态"""
    return jsonify(simulation.get_simulation_status())


@bp.route('/api/simulation/reload', methods=['POST'])
@admin_required
def reload_simulation_config():
    """重新加载模拟配置文件 (admin)"""
    simulation.load_config()
    return jsonify({
        'status': 'ok',
        'message': '配置已重新加载',
        'config': simulation.get_simulation_status()
    })


@bp.route('/api/analytics', methods=['GET'])
@login_required_api
def get_analytics():
    """
    获取完整绩效分析
    
    Returns:
        - sharpe: 夏普比率
        - drawdown: 最大回撤
        - trade_stats: 交易统计 (胜率/盈亏比)
        - positions: 持仓分析
    
    Query params:
        - realtime: 是否获取实时行情 (默认 false，使用 watchlist 缓存)
    """
    account_name = database.get_current_account_name()
    positions = database.get_positions(account_name)
    
    quotes = {}
    if request.args.get('realtime', 'false').lower() == 'true':
        # 实时模式：获取最新行情
        if positions:
            quotes = get_quotes_batch(list(positions.keys()))
    else:
        # 非实时模式：从 watchlist 读取缓存价格
        watchlist = {w['symbol']: w for w in database.get_watchlist()}
        for symbol in positions.keys():
            if symbol in watchlist and watchlist[symbol].get('last_price'):
                quotes[symbol] = {'price': watchlist[symbol]['last_price']}
    
    return jsonify(analytics.get_full_analytics(account_name, quotes))


@bp.route('/api/analytics/sharpe', methods=['GET'])
@login_required_api
def get_sharpe():
    """获取夏普比率"""
    account_name = database.get_current_account_name()
    return jsonify(analytics.calc_sharpe_ratio(account_name))


@bp.route('/api/analytics/drawdown', methods=['GET'])
@login_required_api
def get_drawdown():
    """获取最大回撤"""
    account_name = database.get_current_account_name()
    return jsonify(analytics.calc_max_drawdown(account_name))


@bp.route('/api/analytics/trades', methods=['GET'])
@login_required_api
def get_trade_stats():
    """获取交易统计"""
    account_name = database.get_current_account_name()
    return jsonify(analytics.calc_trade_stats(account_name))


@bp.route('/api/analytics/positions', methods=['GET'])
@login_required_api
def get_position_analysis():
    """获取持仓分析 (使用 watchlist 缓存价格)"""
    account_name = database.get_current_account_name()
    positions = database.get_positions(account_name)
    
    # 从 watchlist 读取缓存价格
    quotes = {}
    watchlist = {w['symbol']: w for w in database.get_watchlist()}
    for symbol in positions.keys():
        if symbol in watchlist and watchlist[symbol].get('last_price'):
            quotes[symbol] = {'price': watchlist[symbol]['last_price']}
    
    return jsonify(analytics.calc_position_analysis(account_name, quotes))
