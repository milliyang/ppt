"""
账户管理 API

路由:
- GET  /api/accounts       - 获取所有账户列表 (登录)
- POST /api/accounts       - 创建新账户 (admin)
- POST /api/accounts/switch - 切换账户 (登录)
- DELETE /api/accounts/<name> - 删除账户 (admin)
- GET  /api/account        - 获取当前账户信息 (登录)
- POST /api/account/reset  - 重置当前账户 (admin)
- GET  /api/config         - 获取系统配置 (admin)
"""
import os
from flask import Blueprint, jsonify, request
from core import db as database
from core.auth import admin_required, login_required_api

bp = Blueprint('account', __name__)

DEFAULT_CAPITAL = database.DEFAULT_CAPITAL


@bp.route('/api/accounts', methods=['GET'])
@login_required_api
def list_accounts():
    """获取所有账户列表"""
    current = database.get_current_account_name()
    accounts = []
    for acc in database.get_all_accounts():
        positions = database.get_positions(acc['name'])
        position_value = sum(p['qty'] * p['avg_price'] for p in positions.values())
        total_value = acc['cash'] + position_value
        pnl = total_value - acc['initial_capital']
        accounts.append({
            'name': acc['name'],
            'total_value': round(total_value, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round((pnl / acc['initial_capital']) * 100, 2) if acc['initial_capital'] > 0 else 0,
            'is_current': acc['name'] == current
        })
    return jsonify({'accounts': accounts, 'current': current})


@bp.route('/api/accounts', methods=['POST'])
@admin_required
def create_new_account():
    """创建新账户 (admin)"""
    data = request.json or {}
    name = data.get('name', '').strip()
    capital = float(data.get('capital', DEFAULT_CAPITAL))
    
    if not name:
        return jsonify({'error': '账户名称不能为空'}), 400
    if database.get_account(name):
        return jsonify({'error': f'账户 {name} 已存在'}), 400
    
    database.create_account(name, capital)
    database.set_current_account(name)
    
    return jsonify({'status': 'ok', 'message': f'账户 {name} 创建成功', 'current': name})


@bp.route('/api/accounts/switch', methods=['POST'])
@login_required_api
def switch_account():
    """切换账户"""
    data = request.json or {}
    name = data.get('name', '')
    
    if not database.get_account(name):
        return jsonify({'error': f'账户 {name} 不存在'}), 400
    
    database.set_current_account(name)
    
    return jsonify({'status': 'ok', 'current': name})


@bp.route('/api/accounts/<name>', methods=['DELETE'])
@admin_required
def delete_account_api(name):
    """删除账户 (admin)"""
    if not database.get_account(name):
        return jsonify({'error': f'账户 {name} 不存在'}), 400
    
    all_accounts = database.get_all_accounts()
    if len(all_accounts) <= 1:
        return jsonify({'error': '至少保留一个账户'}), 400
    
    database.delete_account(name)
    
    # 如果删除的是当前账户，切换到第一个
    if database.get_current_account_name() == name:
        remaining = [a for a in all_accounts if a['name'] != name]
        if remaining:
            database.set_current_account(remaining[0]['name'])
    
    return jsonify({'status': 'ok', 'message': f'账户 {name} 已删除'})


@bp.route('/api/account', methods=['GET'])
@login_required_api
def get_account_api():
    """获取当前账户信息"""
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    positions = database.get_positions(account_name)
    
    # 计算持仓市值 (用成本价)
    position_value = sum(p['qty'] * p['avg_price'] for p in positions.values())
    
    # 优先用 equity_history 最后一条记录（更准确）
    equity_history = database.get_equity_history(account_name)
    if equity_history:
        last_eq = equity_history[-1]
        total_value = last_eq['equity']
        pnl = last_eq['pnl']
        pnl_pct = last_eq['pnl_pct']
    else:
        total_value = account['cash'] + position_value
        pnl = total_value - account['initial_capital']
        pnl_pct = (pnl / account['initial_capital']) * 100 if account['initial_capital'] > 0 else 0
    
    return jsonify({
        'name': account_name,
        'initial_capital': account['initial_capital'],
        'cash': round(account['cash'], 2),
        'position_value': round(position_value, 2),
        'total_value': round(total_value, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 2),
        'created_at': account['created_at']
    })


@bp.route('/api/account/reset', methods=['POST'])
@admin_required
def reset_account_api():
    """重置当前账户 (admin)"""
    account_name = database.get_current_account_name()
    account = database.get_account(account_name)
    
    # 安全获取 JSON 数据
    data = request.get_json(silent=True) or {}
    capital = data.get('capital', account['initial_capital'])
    
    database.reset_account(account_name, capital)
    
    return jsonify({'status': 'ok', 'message': f'账户 {account_name} 已重置，初始资金: {capital}'})


@bp.route('/api/config', methods=['GET'])
@admin_required
def get_config():
    """获取系统配置 (admin)"""
    webhook_token = os.getenv('WEBHOOK_TOKEN', '')
    
    return jsonify({
        'webhook_token': webhook_token,
        'webhook_token_set': bool(webhook_token)
    })
