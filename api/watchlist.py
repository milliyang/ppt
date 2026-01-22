"""
行情监控 API (Watchlist) - 仅 admin

路由:
- GET    /api/watchlist         - 获取关注列表 (admin)
- POST   /api/watchlist         - 添加到关注列表 (admin)
- DELETE /api/watchlist/<symbol> - 从关注列表移除 (admin)
- POST   /api/watchlist/refresh - 刷新关注列表行情 (admin)
- GET    /api/watchlist/test    - 测试行情服务 (admin)
- POST   /api/watchlist/clear   - 清空关注列表 (admin)
- POST   /api/watchlist/init    - 导入默认关注列表 (admin)
"""
import time
from flask import Blueprint, jsonify, request
from core import db as database
from core.utils import get_quote, normalize_symbol
from core.auth import admin_required

bp = Blueprint('watchlist', __name__)


@bp.route('/api/watchlist', methods=['GET'])
@admin_required
def get_watchlist():
    """获取关注列表"""
    watchlist = database.get_watchlist()
    return jsonify({'watchlist': watchlist})


@bp.route('/api/watchlist', methods=['POST'])
@admin_required
def add_watchlist():
    """添加到关注列表"""
    data = request.json or {}
    symbol = data.get('symbol', '').strip()
    
    if not symbol:
        return jsonify({'error': '需要 symbol 参数'}), 400
    
    symbol = normalize_symbol(symbol)
    name = data.get('name', symbol)
    
    if database.add_to_watchlist(symbol, name):
        return jsonify({'status': 'ok', 'symbol': symbol})
    else:
        return jsonify({'error': f'{symbol} 已在关注列表中'}), 400


@bp.route('/api/watchlist/<symbol>', methods=['DELETE'])
@admin_required
def remove_watchlist(symbol):
    """从关注列表移除"""
    symbol = normalize_symbol(symbol)
    if database.remove_from_watchlist(symbol):
        return jsonify({'status': 'ok', 'symbol': symbol})
    else:
        return jsonify({'error': f'{symbol} 不在关注列表中'}), 400


@bp.route('/api/watchlist/refresh', methods=['POST'])
@admin_required
def refresh_watchlist():
    """刷新关注列表行情"""
    watchlist = database.get_watchlist()
    
    if not watchlist:
        return jsonify({'message': '关注列表为空', 'results': []})
    
    results = []
    ok_count = 0
    fail_count = 0
    
    for item in watchlist:
        symbol = item['symbol']
        try:
            quote = get_quote(symbol)
            
            if quote.get('valid', False) and quote.get('price', 0) > 0:
                database.update_watchlist_quote(
                    symbol, 
                    quote['price'], 
                    name=quote.get('name'),
                    status='ok'
                )
                results.append({
                    'symbol': symbol,
                    'status': 'ok',
                    'price': quote['price'],
                    'name': quote.get('name', symbol)
                })
                ok_count += 1
            else:
                error = quote.get('error', '无法获取行情')
                database.update_watchlist_quote(symbol, 0, status='error', error=error)
                results.append({
                    'symbol': symbol,
                    'status': 'error',
                    'error': error
                })
                fail_count += 1
        except Exception as e:
            database.update_watchlist_quote(symbol, 0, status='error', error=str(e))
            results.append({
                'symbol': symbol,
                'status': 'error',
                'error': str(e)
            })
            fail_count += 1
    
    return jsonify({
        'message': f'刷新完成: {ok_count} 成功, {fail_count} 失败',
        'ok': ok_count,
        'fail': fail_count,
        'results': results
    })


@bp.route('/api/watchlist/test', methods=['GET'])
@admin_required
def test_quote_service():
    """测试行情服务是否正常 (用 AAPL 测试)"""
    start = time.time()
    
    try:
        quote = get_quote('AAPL')
        elapsed = round((time.time() - start) * 1000)
        
        if quote.get('valid', False) and quote.get('price', 0) > 0:
            return jsonify({
                'status': 'ok',
                'message': 'yfinance 服务正常',
                'test_symbol': 'AAPL',
                'price': quote['price'],
                'latency_ms': elapsed
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'yfinance 返回无效数据',
                'error': quote.get('error'),
                'latency_ms': elapsed
            })
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return jsonify({
            'status': 'error',
            'message': f'yfinance 服务异常: {str(e)}',
            'latency_ms': elapsed
        })


@bp.route('/api/watchlist/clear', methods=['POST'])
@admin_required
def clear_watchlist():
    """清空关注列表"""
    database.clear_watchlist()
    return jsonify({'status': 'ok', 'message': '关注列表已清空'})


@bp.route('/api/watchlist/init', methods=['POST'])
@admin_required
def init_default_watchlist():
    """导入默认关注列表"""
    result = database.init_default_watchlist()
    return jsonify({
        'status': 'ok',
        'message': f'已添加 {len(result["added"])} 个，跳过 {len(result["skipped"])} 个已存在',
        'added': result['added'],
        'skipped': result['skipped']
    })
