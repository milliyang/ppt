"""
测试数据 API (开发用, admin only)

路由:
- POST /api/test/generate - 生成测试数据 (admin)
- POST /api/test/clean    - 清理测试数据 (admin)
"""
import os
import random
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from core import db as database
from core.auth import admin_required

bp = Blueprint('test', __name__)

# 测试股票池
TEST_STOCKS = [
    {'symbol': 'AAPL', 'name': 'Apple', 'base_price': 185, 'volatility': 0.02},
    {'symbol': 'TSLA', 'name': 'Tesla', 'base_price': 250, 'volatility': 0.05},
    {'symbol': 'GOOGL', 'name': 'Google', 'base_price': 140, 'volatility': 0.025},
    {'symbol': 'NVDA', 'name': 'NVIDIA', 'base_price': 480, 'volatility': 0.04},
    {'symbol': 'SPY', 'name': 'S&P 500 ETF', 'base_price': 470, 'volatility': 0.015},
    {'symbol': 'QQQ', 'name': 'Nasdaq 100 ETF', 'base_price': 410, 'volatility': 0.02},
]


@bp.route('/api/test/generate', methods=['POST'])
@admin_required
def generate_test_data():
    """
    生成测试数据 (模拟多天交易, admin only)
    
    Query params:
        days: 生成天数 (默认 30)
    """
    # 检查是否允许测试 API
    if os.getenv('ENABLE_TEST_API', 'true').lower() == 'false':
        return jsonify({'error': '测试 API 已禁用'}), 403
    
    days = int(request.args.get('days', 30))
    if days < 1 or days > 365:
        return jsonify({'error': 'days 需要在 1-365 之间'}), 400
    
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    initial_capital = account['initial_capital']
    
    # 重置账户
    database.reset_account(account_name, initial_capital)
    
    # 模拟数据
    cash = initial_capital
    positions = {}  # {symbol: {'qty': int, 'avg_price': float, 'buy_price': float}}
    
    # 价格追踪 (模拟价格变动)
    prices = {s['symbol']: s['base_price'] for s in TEST_STOCKS}
    
    trades_count = 0
    orders_count = 0
    
    start_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        date_str = current_date.strftime('%Y-%m-%d')
        time_str = current_date.replace(hour=10, minute=30).isoformat()
        
        # 更新价格 (随机波动)
        for stock in TEST_STOCKS:
            symbol = stock['symbol']
            change = random.uniform(-stock['volatility'], stock['volatility'])
            prices[symbol] = max(1, prices[symbol] * (1 + change))
        
        # 每天 0-3 笔交易
        num_trades = random.choices([0, 1, 2, 3], weights=[0.2, 0.4, 0.3, 0.1])[0]
        
        for _ in range(num_trades):
            stock = random.choice(TEST_STOCKS)
            symbol = stock['symbol']
            price = round(prices[symbol], 2)
            
            # 决定买卖
            if symbol in positions and positions[symbol]['qty'] > 0:
                # 有持仓，60% 概率卖出
                if random.random() < 0.6:
                    side = 'sell'
                    max_qty = positions[symbol]['qty']
                    qty = random.randint(1, max_qty)
                else:
                    side = 'buy'
                    max_value = cash * 0.3
                    qty = max(1, int(max_value / price / 100)) * 100
            else:
                # 无持仓，买入
                side = 'buy'
                max_value = cash * 0.3
                qty = max(1, int(max_value / price / 100)) * 100
            
            if qty <= 0:
                continue
            
            value = qty * price
            
            # 执行交易
            if side == 'buy':
                if value > cash:
                    continue
                cash -= value
                if symbol in positions:
                    old_qty = positions[symbol]['qty']
                    old_value = old_qty * positions[symbol]['avg_price']
                    new_qty = old_qty + qty
                    positions[symbol] = {
                        'qty': new_qty,
                        'avg_price': (old_value + value) / new_qty,
                        'buy_price': price
                    }
                else:
                    positions[symbol] = {'qty': qty, 'avg_price': price, 'buy_price': price}
            else:
                if symbol not in positions or positions[symbol]['qty'] < qty:
                    continue
                cash += value
                positions[symbol]['qty'] -= qty
                if positions[symbol]['qty'] == 0:
                    del positions[symbol]
            
            # 写入数据库
            with database.get_connection() as conn:
                # 订单
                conn.execute('''
                    INSERT INTO orders (account_name, symbol, side, qty, price, value, time, status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'filled', 'test')
                ''', (account_name, symbol, side, qty, price, value, time_str))
                orders_count += 1
                
                # 成交
                conn.execute('''
                    INSERT INTO trades (account_name, symbol, side, qty, price, value, time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (account_name, symbol, side, qty, price, value, time_str))
                trades_count += 1
        
        # 计算当日净值
        position_value = sum(
            pos['qty'] * prices[symbol] 
            for symbol, pos in positions.items()
        )
        equity = cash + position_value
        pnl = equity - initial_capital
        pnl_pct = (pnl / initial_capital) * 100
        
        # 写入净值历史
        with database.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO equity_history (account_name, date, equity, pnl, pnl_pct)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_name, date_str, round(equity, 2), round(pnl, 2), round(pnl_pct, 2)))
    
    # 更新最终持仓
    for symbol, pos in positions.items():
        database.update_position(account_name, symbol, pos['qty'], pos['avg_price'])
    
    # 更新最终现金
    database.update_account_cash(account_name, cash)
    
    # 把最后的净值也写入今天（覆盖 reset_account 创建的 0 记录）
    today_str = datetime.now().strftime('%Y-%m-%d')
    with database.get_connection() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO equity_history (account_name, date, equity, pnl, pnl_pct)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_name, today_str, round(equity, 2), round(pnl, 2), round(pnl_pct, 2)))
    
    return jsonify({
        'status': 'ok',
        'message': f'已生成 {days} 天测试数据',
        'account': account_name,
        'days': days,
        'orders': orders_count,
        'trades': trades_count,
        'final_positions': len(positions),
        'final_cash': round(cash, 2)
    })


@bp.route('/api/test/clean', methods=['POST'])
@admin_required
def clean_test_data():
    """清理测试数据 (重置账户, admin only)"""
    if os.getenv('ENABLE_TEST_API', 'true').lower() == 'false':
        return jsonify({'error': '测试 API 已禁用'}), 403
    
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    database.reset_account(account_name, account['initial_capital'])
    
    return jsonify({
        'status': 'ok',
        'message': f'账户 {account_name} 已重置',
        'initial_capital': account['initial_capital']
    })
