"""
Webhook API - 接收外部交易信号

路由:
- POST /api/webhook - 接收外部信号
"""
import os
from datetime import datetime
from flask import Blueprint, jsonify, request
from core import db as database
from core import simulation
from core.utils import normalize_symbol

bp = Blueprint('webhook', __name__)

# SocketIO 引用，由 app.py 设置
socketio = None

def init_socketio(sio):
    """初始化 SocketIO 引用"""
    global socketio
    socketio = sio


@bp.route('/api/webhook', methods=['POST'])
def webhook():
    """
    接收外部交易信号
    
    支持格式:
    1. 标准格式: {"symbol": "AAPL", "side": "buy", "qty": 100, "price": 185}
    2. TradingView: {"ticker": "AAPL", "action": "buy", "contracts": 100, "price": 185}
    3. 简化格式: {"symbol": "AAPL", "action": "buy"}  (使用默认数量和当前价格占位)
    
    可选参数:
    - account: 指定账户名 (默认当前账户)
    - token: 认证令牌 (如设置了 WEBHOOK_TOKEN 环境变量)
    """
    # 认证检查
    webhook_token = os.getenv('WEBHOOK_TOKEN')
    if webhook_token:
        token = request.headers.get('X-Webhook-Token') or request.json.get('token')
        if token != webhook_token:
            return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    if not data:
        return jsonify({'error': '缺少数据'}), 400
    
    # 解析信号 (兼容多种格式)
    symbol = normalize_symbol(data.get('symbol') or data.get('ticker') or '')
    side = (data.get('side') or data.get('action') or '').lower()
    qty = int(data.get('qty') or data.get('contracts') or data.get('quantity') or 100)
    price = float(data.get('price') or data.get('limit_price') or 0)
    
    # 映射 action
    if side in ['long', 'buy_to_open', 'buy']:
        side = 'buy'
    elif side in ['short', 'sell_to_close', 'sell', 'close']:
        side = 'sell'
    
    if not symbol:
        return jsonify({'error': '缺少 symbol'}), 400
    if side not in ['buy', 'sell']:
        return jsonify({'error': f'无效的 side: {side}，需要 buy/sell'}), 400
    if price <= 0:
        return jsonify({'error': '需要指定 price'}), 400
    
    # 获取目标账户 (不切换全局当前账户)
    account_name = data.get('account') or database.get_current_account_name()
    account = database.get_account(account_name)
    if not account:
        return jsonify({'error': f'账户不存在: {account_name}'}), 400
    
    # ===== 交易模拟 =====
    sim_result = simulation.simulate_execution(symbol, side, qty, price)
    
    filled_qty = sim_result['filled_qty']
    exec_price = sim_result['exec_price']
    commission = sim_result['commission']
    filled_value = sim_result['filled_value']
    total_cost = sim_result['total_cost']
    
    # 执行交易
    if side == 'buy':
        if total_cost > account['cash']:
            return jsonify({
                'error': f'资金不足: 需要 {total_cost:.2f} (含手续费 {commission:.2f}), 可用 {account["cash"]:.2f}'
            }), 400
        
        # 更新现金
        new_cash = account['cash'] - total_cost
        database.update_account_cash(account_name, new_cash)
        
        # 更新持仓
        pos = database.get_position(account_name, symbol)
        if pos:
            old_qty = pos['qty']
            old_value = old_qty * pos['avg_price']
            new_qty = old_qty + filled_qty
            new_avg_price = (old_value + filled_value) / new_qty
            database.update_position(account_name, symbol, new_qty, new_avg_price)
        else:
            database.update_position(account_name, symbol, filled_qty, exec_price)
    
    elif side == 'sell':
        pos = database.get_position(account_name, symbol)
        if not pos:
            return jsonify({'error': f'无持仓: {symbol}'}), 400
        
        # 自动调整卖出数量
        if pos['qty'] < filled_qty:
            filled_qty = pos['qty']
            filled_value = filled_qty * exec_price
            total_cost = filled_value - commission
        
        new_qty = pos['qty'] - filled_qty
        database.update_position(account_name, symbol, new_qty, pos['avg_price'])
        
        # 更新现金
        new_cash = account['cash'] + total_cost
        database.update_account_cash(account_name, new_cash)
    
    # 记录订单和成交
    status = 'partial' if sim_result['partial_fill'] else 'filled'
    order_id = database.add_order(account_name, symbol, side, filled_qty, exec_price, status, 'webhook')
    database.add_trade(account_name, symbol, side, filled_qty, exec_price)
    
    database.update_equity_history(account_name)
    
    # 获取更新后的账户
    updated_account = database.get_account(account_name)
    
    order = {
        'id': order_id,
        'symbol': symbol,
        'side': side,
        'requested_qty': qty,
        'filled_qty': filled_qty,
        'requested_price': price,
        'exec_price': exec_price,
        'value': filled_value,
        'time': datetime.now().isoformat(),
        'status': status,
        'source': 'webhook'
    }
    
    # 模拟信息
    sim_info = {
        'slippage': sim_result['slippage'],
        'commission': commission,
        'fill_rate': sim_result['fill_rate'],
        'total_cost': total_cost
    }
    
    # 通知 WebSocket 客户端
    if socketio:
        socketio.emit('trade', {**order, 'simulation': sim_info})
    
    return jsonify({
        'status': 'ok',
        'order': order,
        'simulation': sim_info,
        'account': account_name,
        'cash': round(updated_account['cash'], 2)
    })
