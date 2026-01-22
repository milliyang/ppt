"""
交易/行情 API

路由:
- GET  /api/positions      - 获取持仓 (登录)
- GET  /api/quote/<symbol> - 获取单个行情 (登录)
- GET  /api/quotes         - 批量获取行情 (登录)
- GET  /api/orders         - 获取订单历史 (登录)
- POST /api/orders         - 下单 (admin)
- GET  /api/trades         - 获取成交记录 (登录)
- GET  /api/equity         - 获取净值历史 (登录)
- POST /api/equity/update  - 更新净值 (admin)
- GET  /api/export/trades  - 导出交易 CSV (登录)
- GET  /api/export/equity  - 导出净值 CSV (登录)
"""
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from core import db as database
from core import simulation
from core.utils import get_quote, get_quotes_batch, normalize_symbol
from core.auth import admin_required, login_required_api

bp = Blueprint('trade', __name__)


@bp.route('/api/positions', methods=['GET'])
@login_required_api
def get_positions_api():
    """获取当前账户持仓 (带实时行情)"""
    account_name = database.get_current_account_name()
    db_positions = database.get_positions(account_name)
    realtime = request.args.get('realtime', 'false').lower() == 'true'
    
    # 获取 watchlist 中的缓存价格
    watchlist = {w['symbol']: w for w in database.get_watchlist()}
    
    positions = []
    total_cost = 0
    total_market_value = 0
    total_pnl = 0
    
    for symbol, pos in db_positions.items():
        cost = pos['qty'] * pos['avg_price']
        total_cost += cost
        
        item = {
            'symbol': symbol,
            'qty': pos['qty'],
            'avg_price': round(pos['avg_price'], 2),
            'cost': round(cost, 2),
        }
        
        current_price = 0
        
        if realtime:
            # 实时模式：获取最新价格并更新到 watchlist
            quote = get_quote(symbol)
            current_price = quote.get('price', 0)
            if current_price > 0:
                # 更新到 watchlist 缓存
                if symbol not in watchlist:
                    database.add_to_watchlist(symbol, quote.get('name', symbol))
                database.update_watchlist_quote(symbol, current_price, quote.get('name'))
        else:
            # 非实时模式：从 watchlist 读取缓存价格
            if symbol in watchlist and watchlist[symbol].get('last_price'):
                current_price = watchlist[symbol]['last_price']
        
        if current_price > 0:
            market_value = pos['qty'] * current_price
            pnl = market_value - cost
            pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
            
            item.update({
                'current_price': round(current_price, 2),
                'market_value': round(market_value, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
            })
            
            total_market_value += market_value
            total_pnl += pnl
        else:
            item['market_value'] = round(cost, 2)
            total_market_value += cost
        
        positions.append(item)
    
    result = {'positions': positions}
    if realtime:
        result['summary'] = {
            'total_cost': round(total_cost, 2),
            'total_market_value': round(total_market_value, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0
        }
    
    return jsonify(result)


@bp.route('/api/quote/<symbol>', methods=['GET'])
@login_required_api
def get_symbol_quote(symbol):
    """获取单个股票行情"""
    quote = get_quote(normalize_symbol(symbol))
    return jsonify(quote)


@bp.route('/api/quotes', methods=['GET'])
@login_required_api
def get_multi_quotes():
    """获取多个股票行情"""
    raw_symbols = request.args.get('symbols', '').split(',')
    symbols = [normalize_symbol(s) for s in raw_symbols if s.strip()]
    if not symbols:
        return jsonify({'error': '需要 symbols 参数'}), 400
    
    quotes = get_quotes_batch(symbols)
    return jsonify({'quotes': quotes})


@bp.route('/api/orders', methods=['GET'])
@login_required_api
def get_orders_api():
    """获取当前账户订单历史"""
    account_name = database.get_current_account_name()
    orders = database.get_orders(account_name, limit=50)
    return jsonify({'orders': orders})


@bp.route('/api/orders', methods=['POST'])
@admin_required
def place_order():
    """下单 (admin, 支持交易模拟: 滑点、手续费、部分成交)"""
    data = request.json
    if not data:
        return jsonify({'error': '缺少订单数据'}), 400
    
    symbol = normalize_symbol(data.get('symbol', ''))
    side = data.get('side', '').lower()
    qty = int(data.get('qty', 0))
    price = float(data.get('price', 0))
    
    if not all([symbol, side in ['buy', 'sell'], qty > 0, price > 0]):
        return jsonify({'error': '参数错误: symbol, side(buy/sell), qty, price'}), 400
    
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    
    # ===== 交易模拟 =====
    sim_result = simulation.simulate_execution(symbol, side, qty, price)
    
    filled_qty = sim_result['filled_qty']
    exec_price = sim_result['exec_price']
    commission = sim_result['commission']
    filled_value = sim_result['filled_value']
    total_cost = sim_result['total_cost']
    
    # 买入检查
    if side == 'buy':
        if total_cost > account['cash']:
            return jsonify({
                'error': f'资金不足: 需要 {total_cost:.2f} (含手续费 {commission:.2f}), 可用 {account["cash"]:.2f}'
            }), 400
        
        # 更新现金 (扣除总成本)
        new_cash = account['cash'] - total_cost
        database.update_account_cash(account_name, new_cash)
        
        # 更新持仓 (按实际成交价计算)
        pos = database.get_position(account_name, symbol)
        if pos:
            old_qty = pos['qty']
            old_value = old_qty * pos['avg_price']
            new_qty = old_qty + filled_qty
            new_avg_price = (old_value + filled_value) / new_qty
            database.update_position(account_name, symbol, new_qty, new_avg_price)
        else:
            database.update_position(account_name, symbol, filled_qty, exec_price)
    
    # 卖出检查
    elif side == 'sell':
        pos = database.get_position(account_name, symbol)
        if not pos or pos['qty'] < filled_qty:
            return jsonify({'error': f'持仓不足: {symbol}'}), 400
        
        new_qty = pos['qty'] - filled_qty
        database.update_position(account_name, symbol, new_qty, pos['avg_price'])
        
        # 更新现金 (卖出所得减去手续费)
        new_cash = account['cash'] + total_cost
        database.update_account_cash(account_name, new_cash)
    
    # 记录订单和成交 (使用实际成交价格)
    status = 'partial' if sim_result['partial_fill'] else 'filled'
    order_id = database.add_order(account_name, symbol, side, filled_qty, exec_price, status, 'web')
    database.add_trade(account_name, symbol, side, filled_qty, exec_price)
    
    # 更新净值历史
    database.update_equity_history(account_name)
    
    # 获取更新后的现金
    updated_account = database.get_account(account_name)
    
    return jsonify({
        'status': 'ok',
        'order': {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'requested_qty': qty,
            'filled_qty': filled_qty,
            'requested_price': price,
            'exec_price': exec_price,
            'value': filled_value,
            'time': datetime.now().isoformat(),
            'status': status
        },
        'simulation': {
            'slippage': sim_result['slippage'],
            'commission': commission,
            'fill_rate': sim_result['fill_rate'],
            'total_cost': total_cost
        },
        'cash': round(updated_account['cash'], 2)
    })


@bp.route('/api/trades', methods=['GET'])
@login_required_api
def get_trades_api():
    """获取当前账户成交记录"""
    account_name = database.get_current_account_name()
    trades = database.get_trades(account_name, limit=100)
    return jsonify({'trades': trades})


@bp.route('/api/equity', methods=['GET'])
@login_required_api
def get_equity_history_api():
    """获取净值历史"""
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    history = database.get_equity_history(account_name)
    return jsonify({
        'history': history,
        'initial_capital': account['initial_capital']
    })


@bp.route('/api/equity/update', methods=['POST'])
@admin_required
def update_equity_with_market_price():
    """
    用实时市价更新当天净值 (admin)
    
    建议每天收盘后调用，或配置 cron 每天多次调用
    """
    results = []
    failed_symbols = []
    
    # 遍历所有账户
    for acc in database.get_all_accounts():
        account_name = acc['name']
        positions = database.get_positions(account_name)
        
        if not positions:
            # 无持仓，直接用成本价更新
            database.update_equity_history(account_name)
            results.append({'account': account_name, 'status': 'ok', 'positions': 0})
            continue
        
        # 获取所有持仓的实时行情
        symbols = list(positions.keys())
        quotes = get_quotes_batch(symbols)
        
        # 检查哪些获取失败
        for symbol in symbols:
            q = quotes.get(symbol, {})
            if q.get('price', 0) <= 0 or not q.get('valid', True) == True:
                failed_symbols.append(symbol)
        
        # 用实时行情更新 equity
        database.update_equity_history(account_name, quotes)
        
        results.append({
            'account': account_name, 
            'status': 'ok', 
            'positions': len(positions),
            'quote_failed': [s for s in symbols if s in failed_symbols]
        })
    
    return jsonify({
        'message': f'已更新 {len(results)} 个账户',
        'results': results,
        'failed_symbols': list(set(failed_symbols)),
        'tip': '获取失败的股票将使用成本价计算'
    })


@bp.route('/api/export/trades', methods=['GET'])
@login_required_api
def export_trades_csv():
    """导出交易记录 CSV"""
    account_name = database.get_current_account_name()
    trades = database.get_trades(account_name, limit=10000)
    
    # CSV 头
    lines = ['时间,代码,方向,数量,价格,金额']
    
    for t in trades:
        lines.append(f"{t['time']},{t['symbol']},{t['side']},{t['qty']},{t['price']:.2f},{t['value']:.2f}")
    
    csv_content = '\n'.join(lines)
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=trades_{account_name}_{datetime.now().strftime("%Y%m%d")}.csv'}
    )


@bp.route('/api/export/equity', methods=['GET'])
@login_required_api
def export_equity_csv():
    """导出净值历史 CSV"""
    account_name = database.get_current_account_name()
    history = database.get_equity_history(account_name)
    
    lines = ['日期,净值,盈亏,收益率%']
    
    for h in history:
        lines.append(f"{h['date']},{h['equity']},{h['pnl']},{h['pnl_pct']}")
    
    csv_content = '\n'.join(lines)
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=equity_{account_name}_{datetime.now().strftime("%Y%m%d")}.csv'}
    )
