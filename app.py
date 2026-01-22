"""
Paper Trade - 模拟交易平台

主入口文件，负责:
- Flask 应用初始化
- 注册所有 Blueprint
- 静态页面路由
- WebSocket 事件
- 定时任务
- 用户认证
"""
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or os.urandom(24).hex()

# Initialize extensions
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 静态文件目录
STATIC_DIR = Path(__file__).parent / 'static'

# ============================================================
# Import Core Modules
# ============================================================

from core import db as database
from core.utils import get_quotes_batch
from core.auth import init_login_manager, authenticate

# 初始化 Flask-Login
init_login_manager(app)

# ============================================================
# Register API Blueprints
# ============================================================

from api import all_blueprints
from api import webhook

# 初始化需要 socketio 的模块
webhook.init_socketio(socketio)

# 注册所有 Blueprint
for bp in all_blueprints:
    app.register_blueprint(bp)

# ============================================================
# 定时任务 - 自动更新净值
# ============================================================

def setup_scheduler():
    """设置定时任务"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("[Scheduler] APScheduler 未安装，跳过定时任务")
        print("[Scheduler] 安装: pip install apscheduler")
        return None
    
    # 从环境变量读取配置，默认美股时间
    # 格式: "5:0,21:30,0:0" 表示 5:00, 21:30, 0:00
    schedule_times = os.getenv('EQUITY_UPDATE_SCHEDULE', '5:0,21:30,0:0')
    
    if not schedule_times or schedule_times.lower() == 'off':
        print("[Scheduler] 定时更新已禁用 (EQUITY_UPDATE_SCHEDULE=off)")
        return None
    
    scheduler = BackgroundScheduler()
    
    def auto_update_equity():
        """自动更新所有账户净值"""
        print(f"[Scheduler] 开始更新净值 {datetime.now().isoformat()}")
        try:
            for acc in database.get_all_accounts():
                account_name = acc['name']
                positions = database.get_positions(account_name)
                
                if positions:
                    symbols = list(positions.keys())
                    quotes = get_quotes_batch(symbols)
                    database.update_equity_history(account_name, quotes)
                else:
                    database.update_equity_history(account_name)
                    
            print(f"[Scheduler] 净值更新完成")
        except Exception as e:
            print(f"[Scheduler] 净值更新失败: {e}")
    
    # 解析时间配置
    for time_str in schedule_times.split(','):
        time_str = time_str.strip()
        if ':' in time_str:
            hour, minute = time_str.split(':')
            trigger = CronTrigger(hour=int(hour), minute=int(minute))
            scheduler.add_job(auto_update_equity, trigger, id=f'equity_update_{hour}_{minute}')
            print(f"[Scheduler] 添加定时任务: {hour}:{minute}")
    
    scheduler.start()
    print("[Scheduler] 定时任务已启动")
    return scheduler

# 启动定时器 (仅在非测试环境)
if os.getenv('FLASK_ENV') != 'testing':
    _scheduler = setup_scheduler()

# ============================================================
# 登录/登出路由
# ============================================================

@app.route('/login')
def login_page():
    """登录页面"""
    if current_user.is_authenticated:
        return redirect('/')
    return send_from_directory(STATIC_DIR, 'login.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """登录 API"""
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user = authenticate(username, password)
    if user:
        login_user(user)
        return jsonify({
            'status': 'ok',
            'user': {'username': user.username, 'role': user.role}
        })
    return jsonify({'error': '用户名或密码错误'}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """登出 API"""
    logout_user()
    return jsonify({'status': 'ok'})


@app.route('/api/user')
def api_user():
    """获取当前用户信息"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'role': current_user.role
        })
    return jsonify({'authenticated': False})


# ============================================================
# Static Pages & Health Check
# ============================================================

@app.route('/')
@login_required
def index():
    """Dashboard 首页 (需登录)"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory(STATIC_DIR, filename)


@app.route('/watchlist')
@login_required
def watchlist_page():
    """行情监控页面 (需 admin)"""
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return send_from_directory(STATIC_DIR, 'watchlist.html')


@app.route('/test')
@login_required
def test_page():
    """测试工具页面 (需 admin)"""
    if os.getenv('ENABLE_TEST_API', 'true').lower() == 'false':
        return redirect(url_for('index'))
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return send_from_directory(STATIC_DIR, 'test.html')


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'paper-trade',
        'version': '2.0.0'
    })


@app.route('/api/info')
def info():
    """API information"""
    return jsonify({
        'name': 'Paper Trade API',
        'version': '2.0.0',
        'endpoints': {
            '/': 'Dashboard 交易界面',
            '/watchlist': '行情监控页面',
            '/test': '测试工具页面',
            '/api/health': '健康检查',
            '/api/accounts': 'GET - 账户列表 / POST - 创建账户',
            '/api/accounts/switch': 'POST - 切换账户',
            '/api/account': 'GET - 当前账户信息',
            '/api/account/reset': 'POST - 重置当前账户',
            '/api/positions': 'GET - 持仓列表',
            '/api/orders': 'GET - 订单历史 / POST - 下单',
            '/api/trades': 'GET - 成交记录',
            '/api/equity': 'GET - 净值历史',
            '/api/watchlist': '行情监控',
            '/api/analytics': '绩效分析',
            '/api/simulation': '交易模拟配置',
            '/api/webhook': 'POST - Webhook 信号接收',
        }
    })


# ============================================================
# WebSocket Events
# ============================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle market data subscription"""
    symbol = data.get('symbol')
    print(f'Subscribed to: {symbol}')
    socketio.emit('subscribed', {'symbol': symbol, 'status': 'ok'})


# ============================================================
# Main Entry
# ============================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 11182))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 初始化数据库
    database.init_db()
    
    print(f'\n=== Paper Trade Server ===')
    print(f'Dashboard: http://localhost:{port}/')
    print(f'Watchlist: http://localhost:{port}/watchlist')
    print(f'Test Page: http://localhost:{port}/test')
    print(f'API Health: http://localhost:{port}/api/health')
    print(f'Debug: {debug}')
    print(f'==========================\n')
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
