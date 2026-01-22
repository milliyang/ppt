/**
 * Paper Trade 前端逻辑
 */

// 当前用户信息
let currentUser = { authenticated: false, role: 'viewer' };

function formatMoney(n) { 
    return '$' + n.toLocaleString('en-US', {minimumFractionDigits: 2}); 
}

// ========== 用户认证 ==========

async function loadUser() {
    try {
        const res = await fetch('/api/user');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        currentUser = await res.json();
        updateUIByRole();
    } catch (e) {
        console.error('加载用户信息失败:', e);
        window.location.href = '/login';
    }
}

function updateUIByRole() {
    const isAdmin = currentUser.role === 'admin';
    
    // 显示/隐藏需要 admin 权限的元素
    document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });
    
    // 显示用户信息
    const userInfo = document.getElementById('user-info');
    if (userInfo) {
        userInfo.textContent = `${currentUser.username} (${currentUser.role})`;
    }
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login';
}

// ========== 账户管理 ==========

async function loadAccounts() {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    const select = document.getElementById('account-select');
    select.innerHTML = data.accounts.map(a => 
        `<option value="${a.name}" ${a.is_current ? 'selected' : ''}>${a.name} (${formatMoney(a.total_value)}, ${a.pnl >= 0 ? '+' : ''}${a.pnl_pct}%)</option>`
    ).join('');
}

async function switchAccount() {
    const name = document.getElementById('account-select').value;
    await fetch('/api/accounts/switch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    });
    loadAll();
}

async function createAccount() {
    const name = prompt('输入账户名称:');
    if (!name) return;
    const capital = prompt('初始资金 (默认 100 万):', '1000000');
    const res = await fetch('/api/accounts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, capital: parseFloat(capital) || 1000000})
    });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    loadAll();
}

async function deleteAccount() {
    const name = document.getElementById('account-select').value;
    if (!confirm(`确定删除账户 "${name}"？`)) return;
    const res = await fetch(`/api/accounts/${name}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    loadAll();
}

async function loadAccount() {
    const res = await fetch('/api/account');
    const data = await res.json();
    document.getElementById('total-value').textContent = formatMoney(data.total_value);
    document.getElementById('cash').textContent = formatMoney(data.cash);
    document.getElementById('position-value').textContent = formatMoney(data.position_value);
    document.getElementById('pnl').textContent = formatMoney(data.pnl);
    document.getElementById('pnl').className = 'stat-value ' + (data.pnl >= 0 ? 'positive' : 'negative');
    document.getElementById('pnl-pct').textContent = data.pnl_pct.toFixed(2) + '%';
    document.getElementById('pnl-pct').className = 'stat-value ' + (data.pnl >= 0 ? 'positive' : 'negative');
}

async function resetAccount() {
    if (!confirm('确定重置账户？所有数据将清空！')) return;
    await fetch('/api/account/reset', {method: 'POST'});
    loadAll();
}

// ========== 持仓 ==========

async function loadPositions(realtime = false) {
    const url = realtime ? '/api/positions?realtime=true' : '/api/positions';
    const res = await fetch(url);
    const data = await res.json();
    const tbody = document.getElementById('positions-body');
    const summary = document.getElementById('positions-summary');
    
    if (!data.positions.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">暂无持仓</td></tr>';
        summary.innerHTML = '';
        return;
    }
    
    tbody.innerHTML = data.positions.map(p => {
        const pnlClass = (p.pnl || 0) >= 0 ? 'positive' : 'negative';
        const pnlText = p.pnl !== undefined ? 
            `<span class="${pnlClass}">${p.pnl >= 0 ? '+' : ''}${formatMoney(p.pnl)}</span>` : '-';
        const pnlPctText = p.pnl_pct !== undefined ? 
            `<span class="${pnlClass}">${p.pnl_pct >= 0 ? '+' : ''}${p.pnl_pct.toFixed(2)}%</span>` : '-';
        const priceText = p.current_price ? formatMoney(p.current_price) : '-';
        return `<tr><td>${p.symbol}</td><td class="num">${p.qty}</td><td class="num">${formatMoney(p.avg_price)}</td><td class="num">${priceText}</td><td class="num">${pnlText}</td><td class="num">${pnlPctText}</td></tr>`;
    }).join('');
    
    if (data.summary) {
        const s = data.summary;
        const pnlClass = s.total_pnl >= 0 ? 'positive' : 'negative';
        summary.innerHTML = `总成本: ${formatMoney(s.total_cost)} | 市值: ${formatMoney(s.total_market_value)} | 盈亏: <span class="${pnlClass}">${s.total_pnl >= 0 ? '+' : ''}${formatMoney(s.total_pnl)} (${s.total_pnl_pct >= 0 ? '+' : ''}${s.total_pnl_pct.toFixed(2)}%)</span>`;
    } else {
        summary.innerHTML = '';
    }
}

async function loadPositionsRealtime() {
    await loadPositions(true);
}

// ========== 交易 ==========

async function loadTrades() {
    const res = await fetch('/api/trades');
    const data = await res.json();
    const list = document.getElementById('trades-list');
    list.innerHTML = data.trades.slice(-20).reverse().map(t => 
        `<div class="trade-item trade-${t.side}">${t.time.split('T')[1].split('.')[0]} ${t.side.toUpperCase()} ${t.symbol} ${t.qty}@${t.price}</div>`
    ).join('') || '<div style="color:#8b949e">暂无成交</div>';
}

async function placeOrder() {
    const order = {
        symbol: document.getElementById('symbol').value,
        qty: document.getElementById('qty').value,
        price: document.getElementById('price').value,
        side: document.getElementById('side').value
    };
    const res = await fetch('/api/orders', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(order)
    });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    loadAll();
    document.getElementById('symbol').value = '';
    document.getElementById('qty').value = '';
    document.getElementById('price').value = '';
}

// ========== 收益曲线 ==========

async function loadEquityChart() {
    const res = await fetch('/api/equity');
    const data = await res.json();
    drawChart(data.history, data.initial_capital);
}

// 全局存储图表数据供鼠标交互使用
let chartData = { history: [], padding: {}, W: 0, H: 0, chartW: 0, chartH: 0, minPnl: 0, maxPnl: 0, range: 1 };

function drawChart(history, initialCapital) {
    const canvas = document.getElementById('equity-chart');
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth || canvas.parentElement.offsetWidth;
    const H = canvas.height = 220;
    
    ctx.clearRect(0, 0, W, H);
    
    if (!history || history.length < 1) {
        ctx.fillStyle = '#8b949e';
        ctx.font = '12px sans-serif';
        ctx.fillText('暂无数据', W/2 - 30, H/2);
        chartData.history = [];
        return;
    }
    
    const padding = {top: 25, right: 65, bottom: 35, left: 50};
    const chartW = W - padding.left - padding.right;
    const chartH = H - padding.top - padding.bottom;
    
    // 计算收益率范围
    const pnlPcts = history.map(h => h.pnl_pct);
    const dataMin = Math.min(...pnlPcts);
    const dataMax = Math.max(...pnlPcts);
    // 增加 10% 边距，确保包含 0
    const margin = Math.max((dataMax - dataMin) * 0.1, 1);
    const minPnl = Math.min(0, dataMin - margin);
    const maxPnl = Math.max(0, dataMax + margin);
    const range = maxPnl - minPnl;
    
    // 保存数据供鼠标交互
    chartData = { history, padding, W, H, chartW, chartH, minPnl, maxPnl, range };
    
    const isPositive = pnlPcts[pnlPcts.length-1] >= 0;
    const mainColor = isPositive ? '#3fb950' : '#f85149';
    const lightColor = isPositive ? 'rgba(63,185,80,0.15)' : 'rgba(248,81,73,0.15)';
    
    // 绘制水平网格线和Y轴标签
    ctx.fillStyle = '#6e7681';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'right';
    
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const value = maxPnl - (range * i / gridLines);
        const y = padding.top + (chartH * i / gridLines);
        
        // 网格线
        ctx.strokeStyle = i === 0 || i === gridLines ? '#30363d' : '#21262d';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(W - padding.right, y);
        ctx.stroke();
        
        // Y轴标签
        const label = value >= 0 ? `+${value.toFixed(1)}%` : `${value.toFixed(1)}%`;
        ctx.fillText(label, padding.left - 8, y + 3);
    }
    
    // 零线（加粗）
    const zeroY = padding.top + chartH * (maxPnl / range);
    if (zeroY > padding.top && zeroY < H - padding.bottom) {
        ctx.strokeStyle = '#484f58';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, zeroY);
        ctx.lineTo(W - padding.right, zeroY);
        ctx.stroke();
    }
    
    // X轴时间标签
    ctx.fillStyle = '#6e7681';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    const labelCount = Math.min(7, history.length);
    for (let i = 0; i < labelCount; i++) {
        const idx = Math.floor(i * (history.length - 1) / Math.max(labelCount - 1, 1));
        const x = padding.left + (idx / Math.max(history.length - 1, 1)) * chartW;
        const date = history[idx].date;
        const dateStr = date ? date.slice(5, 10) : '';
        ctx.fillText(dateStr, x, H - 12);
    }
    
    // 计算曲线点
    const points = history.map((h, i) => ({
        x: padding.left + (i / Math.max(history.length - 1, 1)) * chartW,
        y: padding.top + chartH * ((maxPnl - h.pnl_pct) / range)
    }));
    
    // 渐变填充
    const gradient = ctx.createLinearGradient(0, padding.top, 0, H - padding.bottom);
    gradient.addColorStop(0, lightColor);
    gradient.addColorStop(1, 'rgba(13,17,23,0)');
    
    ctx.beginPath();
    ctx.moveTo(points[0].x, zeroY);
    points.forEach((p, i) => {
        if (i === 0) ctx.lineTo(p.x, p.y);
        else {
            // 平滑曲线
            const prev = points[i - 1];
            const cpX = (prev.x + p.x) / 2;
            ctx.quadraticCurveTo(prev.x, prev.y, cpX, (prev.y + p.y) / 2);
            if (i === points.length - 1) ctx.quadraticCurveTo(cpX, (prev.y + p.y) / 2, p.x, p.y);
        }
    });
    ctx.lineTo(points[points.length - 1].x, zeroY);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // 绘制曲线
    ctx.strokeStyle = mainColor;
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    points.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else {
            const prev = points[i - 1];
            const cpX = (prev.x + p.x) / 2;
            ctx.quadraticCurveTo(prev.x, prev.y, cpX, (prev.y + p.y) / 2);
            if (i === points.length - 1) ctx.quadraticCurveTo(cpX, (prev.y + p.y) / 2, p.x, p.y);
        }
    });
    ctx.stroke();
    
    // 最后一个点的高亮圆点
    const lastPoint = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(lastPoint.x, lastPoint.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = mainColor;
    ctx.fill();
    ctx.strokeStyle = '#0d1117';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 当前值标签
    const last = history[history.length - 1];
    ctx.fillStyle = mainColor;
    ctx.font = 'bold 13px -apple-system, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${last.pnl_pct >= 0 ? '+' : ''}${last.pnl_pct.toFixed(2)}%`, lastPoint.x + 10, lastPoint.y + 4);
}

// 鼠标悬浮显示详情
function setupChartHover() {
    const canvas = document.getElementById('equity-chart');
    const tooltip = document.getElementById('chart-tooltip');
    
    canvas.addEventListener('mousemove', (e) => {
        if (!chartData.history || chartData.history.length < 1) return;
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const { history, padding, chartW, chartH, maxPnl, range, W, H } = chartData;
        
        // 检查是否在图表区域内
        if (x < padding.left || x > W - padding.right) {
            tooltip.style.display = 'none';
            return;
        }
        
        // 计算对应的数据点索引
        const ratio = (x - padding.left) / chartW;
        const idx = Math.round(ratio * (history.length - 1));
        const clampedIdx = Math.max(0, Math.min(history.length - 1, idx));
        const point = history[clampedIdx];
        
        // 计算该点的位置
        const pointX = padding.left + (clampedIdx / Math.max(history.length - 1, 1)) * chartW;
        const pointY = padding.top + chartH * ((maxPnl - point.pnl_pct) / range);
        
        // 显示tooltip
        const pnlClass = point.pnl_pct >= 0 ? 'positive' : 'negative';
        const pnlSign = point.pnl_pct >= 0 ? '+' : '';
        tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px;">${point.date}</div>
            <div>净值: $${point.equity.toLocaleString()}</div>
            <div class="${pnlClass}">收益: ${pnlSign}${point.pnl_pct.toFixed(2)}%</div>
        `;
        
        // 定位tooltip
        let tooltipX = rect.left + pointX + 10;
        let tooltipY = rect.top + pointY - 40;
        
        // 防止超出右边界
        if (tooltipX + 120 > window.innerWidth) {
            tooltipX = rect.left + pointX - 130;
        }
        
        tooltip.style.left = tooltipX + 'px';
        tooltip.style.top = tooltipY + 'px';
        tooltip.style.display = 'block';
        
        // 重绘图表并添加指示线
        drawChart(history);
        drawIndicator(clampedIdx);
    });
    
    canvas.addEventListener('mouseleave', () => {
        tooltip.style.display = 'none';
        // 重绘图表（移除指示线）
        if (chartData.history && chartData.history.length > 0) {
            drawChart(chartData.history);
        }
    });
}

// 绘制指示线（在已有图表上叠加）
function drawIndicator(highlightIdx) {
    const { history, padding, W, H, chartW, chartH, maxPnl, range } = chartData;
    if (!history || history.length < 1) return;
    
    const canvas = document.getElementById('equity-chart');
    const ctx = canvas.getContext('2d');
    
    // 计算位置
    const x = padding.left + (highlightIdx / Math.max(history.length - 1, 1)) * chartW;
    const y = padding.top + chartH * ((maxPnl - history[highlightIdx].pnl_pct) / range);
    
    // 垂直虚线
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, H - padding.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // 高亮点（更大）
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#58a6ff';
    ctx.fill();
    ctx.strokeStyle = '#0d1117';
    ctx.lineWidth = 2.5;
    ctx.stroke();
}

// ========== 净值更新 ==========

async function updateEquity() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '更新中...';
    btn.disabled = true;
    
    try {
        const res = await fetch('/api/equity/update', {method: 'POST'});
        const data = await res.json();
        
        // 显示结果（不弹窗）
        if (data.failed_symbols && data.failed_symbols.length > 0) {
            btn.textContent = `✓ ${data.failed_symbols.length}个失败`;
            btn.title = `失败: ${data.failed_symbols.join(', ')} (用成本价)`;
        } else {
            btn.textContent = '✓ 已更新';
        }
        setTimeout(() => { 
            btn.textContent = originalText; 
            btn.title = '用实时价格更新净值';
        }, 3000);
        
        // 刷新数据
        loadEquityChart();
        loadAccount();
        loadAnalytics();
    } catch (e) {
        btn.textContent = '✗ 失败';
        btn.title = e.message;
        setTimeout(() => { 
            btn.textContent = originalText;
            btn.title = '用实时价格更新净值';
        }, 3000);
    } finally {
        btn.disabled = false;
    }
}


// ========== 交易模拟 ==========

async function loadSimulation() {
    try {
        const res = await fetch('/api/simulation');
        const data = await res.json();
        
        // 预设名称
        document.getElementById('sim-preset').textContent = data.preset ? 
            `[${data.preset}]` : '[自定义]';
        
        // 滑点
        const slip = data.slippage;
        document.getElementById('sim-slippage').innerHTML = slip.enabled ? 
            `<span style="color:#3fb950">开</span> ${slip.mode} ${slip.value}%` : 
            `<span style="color:#8b949e">关</span>`;
        
        // 手续费
        const comm = data.commission;
        document.getElementById('sim-commission').innerHTML = comm.enabled ? 
            `<span style="color:#3fb950">开</span> ${(comm.rate*100).toFixed(2)}% (≥$${comm.minimum})` : 
            `<span style="color:#8b949e">关</span>`;
        
        // 部分成交
        const pf = data.partial_fill;
        document.getElementById('sim-partial').innerHTML = pf.enabled ? 
            `<span style="color:#3fb950">开</span> >${pf.threshold}` : 
            `<span style="color:#8b949e">关</span>`;
        
        // 延迟
        const lat = data.latency;
        document.getElementById('sim-latency').innerHTML = lat.enabled ? 
            `<span style="color:#3fb950">开</span>` : 
            `<span style="color:#8b949e">关</span>`;
    } catch (e) {
        console.error('加载模拟配置失败:', e);
    }
}

async function loadConfig() {
    if (currentUser.role !== 'admin') return;
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        const tokenEl = document.getElementById('webhook-token');
        if (tokenEl) {
            if (data.webhook_token) {
                tokenEl.textContent = data.webhook_token;
                tokenEl.style.color = '#58a6ff';
            } else {
                tokenEl.textContent = '未设置';
                tokenEl.style.color = '#f85149';
            }
        }
    } catch (e) {
        console.error('加载配置失败:', e);
    }
}

function copyToken() {
    const token = document.getElementById('webhook-token').textContent;
    if (token && token !== '未设置' && token !== '-') {
        navigator.clipboard.writeText(token).then(() => {
            alert('Token 已复制');
        });
    }
}

// ========== 绩效分析 ==========

async function loadAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const data = await res.json();
        
        // 夏普比率
        const sharpe = data.sharpe;
        document.getElementById('sharpe-ratio').textContent = sharpe.sharpe_ratio || '-';
        document.getElementById('sharpe-ratio').className = 'stat-value ' + 
            (sharpe.sharpe_ratio > 0 ? 'positive' : sharpe.sharpe_ratio < 0 ? 'negative' : '');
        document.getElementById('annual-return').textContent = sharpe.annual_return ? sharpe.annual_return + '%' : '-';
        document.getElementById('annual-return').className = 'stat-value ' + 
            (sharpe.annual_return > 0 ? 'positive' : sharpe.annual_return < 0 ? 'negative' : '');
        document.getElementById('volatility').textContent = sharpe.volatility ? sharpe.volatility + '%' : '-';
        
        // 最大回撤
        const dd = data.drawdown;
        document.getElementById('max-drawdown').textContent = dd.max_drawdown ? '-' + dd.max_drawdown + '%' : '-';
        document.getElementById('max-drawdown').className = 'stat-value negative';
        
        // 交易统计
        const ts = data.trade_stats;
        document.getElementById('win-rate').textContent = ts.win_rate ? ts.win_rate + '%' : '-';
        document.getElementById('win-rate').className = 'stat-value ' + 
            (ts.win_rate >= 50 ? 'positive' : ts.win_rate > 0 ? 'negative' : '');
        document.getElementById('profit-factor').textContent = ts.profit_factor || '-';
        document.getElementById('profit-factor').className = 'stat-value ' + 
            (ts.profit_factor >= 1 ? 'positive' : ts.profit_factor > 0 ? 'negative' : '');
        document.getElementById('avg-win').textContent = ts.avg_win ? formatMoney(ts.avg_win) : '-';
        document.getElementById('avg-loss').textContent = ts.avg_loss ? formatMoney(ts.avg_loss) : '-';
        document.getElementById('total-trades').textContent = ts.total_trades || 0;
        document.getElementById('net-profit').textContent = formatMoney(ts.net_profit || 0);
        document.getElementById('net-profit').className = (ts.net_profit >= 0 ? 'positive' : 'negative');
        
        // 持仓分析
        const pos = data.positions;
        document.getElementById('pos-count').textContent = pos.total_positions || 0;
        document.getElementById('pos-pct').textContent = pos.position_pct ? pos.position_pct + '%' : '0%';
        document.getElementById('top1-pct').textContent = pos.concentration?.top1 ? pos.concentration.top1 + '%' : '-';
        document.getElementById('hhi').textContent = pos.concentration?.hhi || '-';
        
        // 持仓分布条形图
        const barsDiv = document.getElementById('position-bars');
        if (pos.positions && pos.positions.length > 0) {
            barsDiv.innerHTML = pos.positions.slice(0, 5).map(p => {
                const pnlClass = p.pnl >= 0 ? 'positive' : 'negative';
                const pnlSign = p.pnl >= 0 ? '+' : '';
                return `
                    <div style="display:flex;align-items:center;margin-bottom:4px;">
                        <span style="width:60px;color:#8b949e;">${p.symbol}</span>
                        <div style="flex:1;background:#21262d;height:16px;border-radius:3px;position:relative;">
                            <div style="width:${p.weight}%;background:#238636;height:100%;border-radius:3px;"></div>
                            <span style="position:absolute;right:4px;top:0;font-size:10px;line-height:16px;">${p.weight}%</span>
                        </div>
                        <span class="${pnlClass}" style="width:80px;text-align:right;font-size:10px;">
                            ${pnlSign}${formatMoney(p.pnl)}
                        </span>
                    </div>
                `;
            }).join('');
        } else {
            barsDiv.innerHTML = '<div style="color:#8b949e;">暂无持仓</div>';
        }
        
    } catch (e) {
        console.error('加载分析数据失败:', e);
    }
}

// ========== 初始化 ==========

// 快速刷新（不含 analytics，30秒）
function loadQuick() { 
    loadAccounts(); 
    loadAccount(); 
    loadPositions(); 
    loadTrades(); 
    loadEquityChart(); 
}

// 完整加载（含 analytics）
async function loadAll() { 
    await loadUser();  // 先加载用户信息
    loadQuick();
    loadSimulation();
    loadConfig();  // 加载系统配置 (Webhook Token)
    loadAnalytics();
}

// 页面加载
document.addEventListener('DOMContentLoaded', function() {
    loadAll();  // 首次完整加载
    setupChartHover();
    setInterval(loadQuick, 30000);  // 30秒快速刷新（不含 analytics）
});
