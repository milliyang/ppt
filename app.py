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
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# 配置日志系统
# ============================================================
def setup_logging():
    """配置日志系统"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'run/logs/paper_trade.log')
    
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器（用于开发环境）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    logging.info(f"日志系统已初始化: 级别={log_level}, 文件={log_file}")

# 初始化日志
setup_logging()

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
    
    scheduler = BackgroundScheduler()
    
    # ===== 净值更新定时任务 =====
    # 从环境变量读取配置，默认美股时间
    # 格式: "5:0,21:30,0:0" 表示 5:00, 21:30, 0:00
    schedule_times = os.getenv('EQUITY_UPDATE_SCHEDULE', '5:0,21:30,0:0')
    
    if schedule_times and schedule_times.lower() != 'off':
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
                print(f"[Scheduler] 添加净值更新任务: {hour}:{minute}")
    else:
        print("[Scheduler] 净值更新已禁用 (EQUITY_UPDATE_SCHEDULE=off)")
    
    # ===== OpenTimestamps 定时任务 =====
    # 从环境变量读取配置，支持多个时间点
    # 格式: "16:0" 表示 16:00（单个时间点）
    # 格式: "16:0,22:0" 表示 16:00 和 22:00（多个时间点，用逗号分隔）
    # 格式: "16:0:us_market,22:0:hk_market" 表示带标签的多个时间点（可选标签）
    ots_schedule = os.getenv('OTS_TIMESTAMP_SCHEDULE', '16:0')
    
    if ots_schedule and ots_schedule.lower() != 'off':
        def create_daily_timestamp_with_label(label=None):
            """创建每日时间戳（带标签）"""
            def wrapper():
                print(f"[Scheduler] 开始创建每日时间戳 {datetime.now().isoformat()}, label={label}")
                try:
                    from opents import service
                    result = service.create_daily_timestamp(label=label)
                    if result.get('success'):
                        print(f"[Scheduler] 时间戳创建成功: {result.get('date')}, label={label}")
                    else:
                        print(f"[Scheduler] 时间戳创建失败: {result.get('error')}")
                except Exception as e:
                    print(f"[Scheduler] 时间戳创建异常: {e}")
            return wrapper
        
        # 解析多个时间点配置
        schedule_items = [item.strip() for item in ots_schedule.split(',')]
        
        for idx, schedule_item in enumerate(schedule_items):
            # 支持格式: "16:0" 或 "16:0:us_market"
            parts = schedule_item.split(':')
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                label = parts[2] if len(parts) >= 3 else None
                
                trigger = CronTrigger(hour=hour, minute=minute)
                job_id = f'ots_timestamp_{hour}_{minute}' + (f'_{label}' if label else '')
                job_func = create_daily_timestamp_with_label(label=label)
                
                scheduler.add_job(job_func, trigger, id=job_id)
                print(f"[Scheduler] 添加时间戳任务: {hour}:{minute}" + (f" (label: {label})" if label else ""))
    else:
        print("[Scheduler] 时间戳任务已禁用 (OTS_TIMESTAMP_SCHEDULE=off)")
    
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


@app.route('/ots')
@login_required
def ots_page():
    """OpenTimestamps 管理页面 (所有登录用户可查看)"""
    # 移除 admin 检查，允许所有登录用户查看
    return send_from_directory(STATIC_DIR, 'ots.html')


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
            '/api/ots/history': 'GET - OpenTimestamps 历史记录',
            '/api/ots/detail/<date>': 'GET - 获取指定日期的时间戳详情',
            '/api/ots/record/<date>': 'GET - 下载原始记录文件',
            '/api/ots/proof/<date>': 'GET - 下载证明文件',
            '/api/ots/create': 'POST - 手动创建时间戳 (admin)',
            '/api/ots/verify/<date>': 'POST - 验证时间戳 (admin)',
            '/api/ots/info': 'GET - OpenTimestamps 服务信息',
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
