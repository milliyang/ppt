"""
Paper Trade SQLite 数据库模块
"""
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

DB_FILE = os.getenv('DB_FILE', 'db/paper_trade.db')
DEFAULT_CAPITAL = 1000000

# 默认关注列表
DEFAULT_WATCHLIST = [
    ('GOOGL', 'Google'),
    ('SPY', 'S&P 500 ETF'),
    ('QQQ', 'Nasdaq 100 ETF'),
    ('GLD', '黄金 ETF'),
    ('SLV', '白银 ETF'),
    ('0700.HK', '腾讯'),
]


def get_db_path() -> str:
    """获取数据库路径"""
    return DB_FILE


@contextmanager
def get_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_FILE) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 返回字典形式
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_connection() as conn:
        conn.executescript('''
            -- 账户表
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY,
                initial_capital REAL NOT NULL,
                cash REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            
            -- 持仓表
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                qty INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                UNIQUE(account_name, symbol),
                FOREIGN KEY (account_name) REFERENCES accounts(name)
            );
            
            -- 订单表
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT DEFAULT 'web',
                FOREIGN KEY (account_name) REFERENCES accounts(name)
            );
            
            -- 成交表
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                time TEXT NOT NULL,
                FOREIGN KEY (account_name) REFERENCES accounts(name)
            );
            
            -- 净值历史表
            CREATE TABLE IF NOT EXISTS equity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                date TEXT NOT NULL,
                equity REAL NOT NULL,
                pnl REAL NOT NULL,
                pnl_pct REAL NOT NULL,
                UNIQUE(account_name, date),
                FOREIGN KEY (account_name) REFERENCES accounts(name)
            );
            
            -- 设置表
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            
            -- 关注列表 (行情监控)
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                last_price REAL,
                last_update TEXT,
                status TEXT DEFAULT 'unknown',
                error TEXT
            );
        ''')
        
        # 初始化默认账户（如果不存在）
        cursor = conn.execute("SELECT COUNT(*) FROM accounts")
        if cursor.fetchone()[0] == 0:
            create_account('default', DEFAULT_CAPITAL)
            set_current_account('default')
        
        # 初始化默认关注列表（如果为空）
        cursor = conn.execute("SELECT COUNT(*) FROM watchlist")
        if cursor.fetchone()[0] == 0:
            for symbol, name in DEFAULT_WATCHLIST:
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist (symbol, name, status) VALUES (?, ?, 'pending')",
                    (symbol, name)
                )


# ============================================================
# 账户操作
# ============================================================

def create_account(name: str, capital: float = DEFAULT_CAPITAL) -> bool:
    """创建新账户"""
    now = datetime.now()
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO accounts (name, initial_capital, cash, created_at) VALUES (?, ?, ?, ?)",
                (name, capital, capital, now.isoformat())
            )
            # 初始净值记录
            conn.execute(
                "INSERT INTO equity_history (account_name, date, equity, pnl, pnl_pct) VALUES (?, ?, ?, 0, 0)",
                (name, now.strftime('%Y-%m-%d'), capital)
            )
            return True
        except sqlite3.IntegrityError:
            return False


def delete_account(name: str) -> bool:
    """删除账户"""
    with get_connection() as conn:
        # 删除关联数据
        conn.execute("DELETE FROM positions WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM orders WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM trades WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM equity_history WHERE account_name = ?", (name,))
        cursor = conn.execute("DELETE FROM accounts WHERE name = ?", (name,))
        return cursor.rowcount > 0


def get_account(name: str) -> Optional[Dict]:
    """获取账户信息"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM accounts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_accounts() -> List[Dict]:
    """获取所有账户"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM accounts ORDER BY created_at")
        return [dict(row) for row in cursor.fetchall()]


def update_account_cash(name: str, cash: float):
    """更新账户现金"""
    with get_connection() as conn:
        conn.execute("UPDATE accounts SET cash = ? WHERE name = ?", (cash, name))


def reset_account(name: str, capital: float = None):
    """重置账户"""
    with get_connection() as conn:
        account = get_account(name)
        if not account:
            return False
        
        new_capital = capital or account['initial_capital']
        now = datetime.now()
        
        # 清空持仓、订单、成交
        conn.execute("DELETE FROM positions WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM orders WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM trades WHERE account_name = ?", (name,))
        conn.execute("DELETE FROM equity_history WHERE account_name = ?", (name,))
        
        # 重置账户
        conn.execute(
            "UPDATE accounts SET initial_capital = ?, cash = ?, created_at = ? WHERE name = ?",
            (new_capital, new_capital, now.isoformat(), name)
        )
        
        # 初始净值
        conn.execute(
            "INSERT INTO equity_history (account_name, date, equity, pnl, pnl_pct) VALUES (?, ?, ?, 0, 0)",
            (name, now.strftime('%Y-%m-%d'), new_capital)
        )
        return True


# ============================================================
# 当前账户
# ============================================================

def get_current_account_name() -> str:
    """获取当前账户名"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'current_account'")
        row = cursor.fetchone()
        return row['value'] if row else 'default'


def set_current_account(name: str):
    """设置当前账户"""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('current_account', ?)",
            (name,)
        )


# ============================================================
# 持仓操作
# ============================================================

def get_positions(account_name: str) -> Dict[str, Dict]:
    """获取持仓"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT symbol, qty, avg_price FROM positions WHERE account_name = ?",
            (account_name,)
        )
        return {row['symbol']: {'qty': row['qty'], 'avg_price': row['avg_price']} 
                for row in cursor.fetchall()}


def update_position(account_name: str, symbol: str, qty: int, avg_price: float):
    """更新持仓"""
    with get_connection() as conn:
        if qty <= 0:
            conn.execute(
                "DELETE FROM positions WHERE account_name = ? AND symbol = ?",
                (account_name, symbol)
            )
        else:
            conn.execute('''
                INSERT INTO positions (account_name, symbol, qty, avg_price)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_name, symbol) 
                DO UPDATE SET qty = ?, avg_price = ?
            ''', (account_name, symbol, qty, avg_price, qty, avg_price))


def get_position(account_name: str, symbol: str) -> Optional[Dict]:
    """获取单个持仓"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT qty, avg_price FROM positions WHERE account_name = ? AND symbol = ?",
            (account_name, symbol)
        )
        row = cursor.fetchone()
        return {'qty': row['qty'], 'avg_price': row['avg_price']} if row else None


# ============================================================
# 订单操作
# ============================================================

def add_order(account_name: str, symbol: str, side: str, qty: int, 
              price: float, status: str = 'filled', source: str = 'web') -> int:
    """添加订单"""
    now = datetime.now().isoformat()
    value = qty * price
    with get_connection() as conn:
        cursor = conn.execute('''
            INSERT INTO orders (account_name, symbol, side, qty, price, value, time, status, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_name, symbol, side, qty, price, value, now, status, source))
        return cursor.lastrowid


def get_orders(account_name: str, limit: int = 100) -> List[Dict]:
    """获取订单历史"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM orders WHERE account_name = ? ORDER BY id DESC LIMIT ?",
            (account_name, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


# ============================================================
# 成交操作
# ============================================================

def add_trade(account_name: str, symbol: str, side: str, qty: int, price: float) -> int:
    """添加成交记录"""
    now = datetime.now().isoformat()
    value = qty * price
    with get_connection() as conn:
        cursor = conn.execute('''
            INSERT INTO trades (account_name, symbol, side, qty, price, value, time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (account_name, symbol, side, qty, price, value, now))
        return cursor.lastrowid


def get_trades(account_name: str, limit: int = 100) -> List[Dict]:
    """获取成交记录"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM trades WHERE account_name = ? ORDER BY id DESC LIMIT ?",
            (account_name, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


# ============================================================
# 净值历史
# ============================================================

def update_equity_history(account_name: str, quotes: dict = None):
    """
    更新净值历史
    
    Args:
        account_name: 账户名
        quotes: 实时行情 {symbol: {'price': float}} 
                如果提供则用市价，否则用成本价
    """
    account = get_account(account_name)
    if not account:
        return
    
    positions = get_positions(account_name)
    
    # 计算持仓市值
    position_value = 0
    for symbol, pos in positions.items():
        qty = pos['qty']
        # 优先用实时价格，获取不到则用成本价
        if quotes and symbol in quotes:
            price = quotes[symbol].get('price', 0)
            if price > 0:
                position_value += qty * price
                continue
        # fallback 到成本价
        position_value += qty * pos['avg_price']
    
    equity = account['cash'] + position_value
    pnl = equity - account['initial_capital']
    pnl_pct = (pnl / account['initial_capital']) * 100 if account['initial_capital'] > 0 else 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO equity_history (account_name, date, equity, pnl, pnl_pct)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_name, date) 
            DO UPDATE SET equity = ?, pnl = ?, pnl_pct = ?
        ''', (account_name, today, equity, pnl, pnl_pct, equity, pnl, pnl_pct))


def get_equity_history(account_name: str) -> List[Dict]:
    """获取净值历史"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT date, equity, pnl, pnl_pct FROM equity_history WHERE account_name = ? ORDER BY date",
            (account_name,)
        )
        return [dict(row) for row in cursor.fetchall()]


# ============================================================
# 计算函数
# ============================================================

def calc_equity(account_name: str) -> float:
    """计算账户净值"""
    account = get_account(account_name)
    if not account:
        return 0
    
    positions = get_positions(account_name)
    position_value = sum(p['qty'] * p['avg_price'] for p in positions.values())
    return account['cash'] + position_value


# ============================================================
# 数据迁移
# ============================================================

def migrate_from_json(json_file: str):
    """从 JSON 文件迁移数据"""
    import json
    
    if not os.path.exists(json_file):
        print(f"JSON 文件不存在: {json_file}")
        return False
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    accounts = data.get('accounts', {})
    current = data.get('current_account', 'default')
    
    for name, acc in accounts.items():
        # 创建账户
        with get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO accounts (name, initial_capital, cash, created_at)
                VALUES (?, ?, ?, ?)
            ''', (name, acc['initial_capital'], acc['cash'], acc['created_at']))
        
        # 导入持仓
        for symbol, pos in acc.get('positions', {}).items():
            update_position(name, symbol, pos['qty'], pos['avg_price'])
        
        # 导入订单
        with get_connection() as conn:
            for order in acc.get('orders', []):
                conn.execute('''
                    INSERT INTO orders (account_name, symbol, side, qty, price, value, time, status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, order['symbol'], order['side'], order['qty'], order['price'],
                      order['value'], order['time'], order['status'], order.get('source', 'web')))
        
        # 导入成交
        with get_connection() as conn:
            for trade in acc.get('trades', []):
                conn.execute('''
                    INSERT INTO trades (account_name, symbol, side, qty, price, value, time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, trade['symbol'], trade['side'], trade['qty'], trade['price'],
                      trade['value'], trade['time']))
        
        # 导入净值历史
        with get_connection() as conn:
            for eq in acc.get('equity_history', []):
                conn.execute('''
                    INSERT OR REPLACE INTO equity_history (account_name, date, equity, pnl, pnl_pct)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, eq['date'], eq['equity'], eq['pnl'], eq['pnl_pct']))
    
    set_current_account(current)
    print(f"成功迁移 {len(accounts)} 个账户")
    return True


# ============================================================
# 关注列表 (行情监控)
# ============================================================

def get_watchlist() -> List[Dict]:
    """获取关注列表"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM watchlist ORDER BY symbol")
        return [dict(row) for row in cursor.fetchall()]


def add_to_watchlist(symbol: str, name: str = None) -> bool:
    """添加到关注列表"""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO watchlist (symbol, name, status) VALUES (?, ?, 'pending')",
                (symbol.upper(), name or symbol)
            )
            return True
        except sqlite3.IntegrityError:
            return False


def remove_from_watchlist(symbol: str) -> bool:
    """从关注列表移除"""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        return cursor.rowcount > 0


def update_watchlist_quote(symbol: str, price: float, name: str = None, 
                           status: str = 'ok', error: str = None):
    """更新关注列表行情"""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute('''
            UPDATE watchlist 
            SET last_price = ?, last_update = ?, status = ?, error = ?, name = COALESCE(?, name)
            WHERE symbol = ?
        ''', (price, now, status, error, name, symbol.upper()))


def clear_watchlist():
    """清空关注列表"""
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist")


def init_default_watchlist() -> dict:
    """导入默认关注列表（跳过已存在的）"""
    added = []
    skipped = []
    
    with get_connection() as conn:
        for symbol, name in DEFAULT_WATCHLIST:
            try:
                conn.execute(
                    "INSERT INTO watchlist (symbol, name, status) VALUES (?, ?, 'pending')",
                    (symbol, name)
                )
                added.append(symbol)
            except sqlite3.IntegrityError:
                skipped.append(symbol)
    
    return {'added': added, 'skipped': skipped}


# 初始化数据库
init_db()
