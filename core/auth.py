"""
用户认证模块

- 从 config/users.yaml 加载用户
- Flask-Login 集成
- 权限装饰器 (admin_required, login_required_api)
"""
import os
from functools import wraps
from flask import jsonify, current_app
from flask_login import LoginManager, UserMixin, current_user, login_required
from werkzeug.security import check_password_hash
import yaml

# ============================================================
# 用户模型
# ============================================================

class User(UserMixin):
    def __init__(self, username: str, password_hash: str, role: str):
        self.id = username
        self.username = username
        self.password_hash = password_hash
        self.role = role
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'


# ============================================================
# 用户存储
# ============================================================

_users: dict[str, User] = {}

def load_users(config_path: str = None):
    """从 YAML 文件加载用户"""
    global _users
    
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'config', 'users.yaml')
    
    if not os.path.exists(config_path):
        print(f"[Auth] 用户配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    users_config = config.get('users', {})
    _users = {}
    
    for username, user_data in users_config.items():
        _users[username] = User(
            username=username,
            password_hash=user_data.get('password', ''),
            role=user_data.get('role', 'viewer')
        )
    
    print(f"[Auth] 已加载 {len(_users)} 个用户: {list(_users.keys())}")


def get_user(username: str) -> User | None:
    """获取用户"""
    return _users.get(username)


def authenticate(username: str, password: str) -> User | None:
    """验证用户名密码"""
    user = get_user(username)
    if user and user.check_password(password):
        return user
    return None


# ============================================================
# Flask-Login 初始化
# ============================================================

login_manager = LoginManager()

def init_login_manager(app):
    """初始化 Flask-Login"""
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'
    login_manager.login_message = '请先登录'
    
    # 加载用户配置
    load_users()
    
    @login_manager.user_loader
    def load_user(user_id):
        return get_user(user_id)


# ============================================================
# 权限装饰器
# ============================================================

def admin_required(f):
    """需要 admin 角色的装饰器 (用于 API，返回 JSON)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user or not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
        if not current_user.is_admin:
            return jsonify({'error': 'Admin required'}), 403
        return f(*args, **kwargs)
    return decorated


def login_required_api(f):
    """需要登录的装饰器 (用于 API，返回 JSON)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user or not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated
