/**
 * 统一导航栏组件
 * 在所有页面中提供一致的导航体验
 */

// 页面路由配置
const NAV_ROUTES = {
    home: { path: '/', label: '📊 交易界面', icon: '📊' },
    watchlist: { path: '/watchlist', label: '📊 行情监控', icon: '📊' },
    test: { path: '/test', label: '🧪 测试', icon: '🧪' },
    ots: { path: '/ots', label: '⏰ 时间戳', icon: '⏰' }
};

/**
 * 初始化导航栏
 * @param {Object} options - 配置选项
 * @param {string} options.title - 页面标题
 * @param {string} options.currentRoute - 当前路由键（home/watchlist/test/ots）
 */
function initNav(options = {}) {
    const {
        title = 'Paper Trade',
        currentRoute = getCurrentRoute()
    } = options;

    // 获取用户信息
    fetch('/api/user')
        .then(res => res.json())
        .then(data => {
            if (data.authenticated) {
                // 确保 currentRoute 正确
                const actualRoute = getCurrentRoute();
                renderNav(title, currentRoute || actualRoute, data);
            } else {
                window.location.href = '/login';
            }
        })
        .catch(err => {
            console.error('获取用户信息失败:', err);
        });
}

/**
 * 根据当前路径获取路由键
 */
function getCurrentRoute() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index.html') return 'home';
    if (path.startsWith('/watchlist')) return 'watchlist';
    if (path.startsWith('/test')) return 'test';
    if (path.startsWith('/ots')) return 'ots';
    return 'home';
}

/**
 * 渲染导航栏
 */
function renderNav(title, currentRoute, userData) {
    const header = document.querySelector('.header') || createHeader();
    
    // 确保 header 使用 CSS 类样式
    header.className = 'header';
    header.removeAttribute('style');
    
    // 确保 currentRoute 正确（如果传入的 route 不对，重新检测）
    const actualRoute = getCurrentRoute();
    if (currentRoute !== actualRoute) {
        currentRoute = actualRoute;
    }
    
    // 清空现有内容
    header.innerHTML = '';
    
    // 左侧：标题
    const leftSection = document.createElement('div');
    leftSection.style.display = 'flex';
    leftSection.style.alignItems = 'center';
    leftSection.style.gap = '12px';
    
    const titleEl = document.createElement('h1');
    titleEl.innerHTML = `<img src="/static/icon4-dollar.svg" alt="" style="width:24px;height:24px;vertical-align:middle;margin-right:6px;">${title}`;
    titleEl.style.cssText = 'margin:0;color:#f0f6fc;font-size:18px;display:flex;align-items:center;';
    leftSection.appendChild(titleEl);
    
    header.appendChild(leftSection);
    
    // 右侧：导航链接和用户信息
    const rightSection = document.createElement('div');
    rightSection.style.cssText = 'display:flex;align-items:center;gap:16px;';
    
    // 导航链接：显示所有链接，当前页面用灰色表示
    Object.entries(NAV_ROUTES).forEach(([key, route]) => {
        const link = document.createElement('a');
        link.href = route.path;
        link.textContent = route.label;
        
        // 当前页面用灰色，其他用蓝色
        if (key === currentRoute) {
            link.style.cssText = 'color:#8b949e;text-decoration:none;font-size:13px;cursor:default;pointer-events:none;';
        } else {
            link.style.cssText = 'color:#58a6ff;text-decoration:none;font-size:13px;';
        }
        
        rightSection.appendChild(link);
    });
    
    // 用户信息
    const userInfo = document.createElement('span');
    userInfo.id = 'user-info';
    userInfo.textContent = `${userData.username} (${userData.role})`;
    userInfo.style.cssText = 'color:#8b949e;font-size:12px;';
    rightSection.appendChild(userInfo);
    
    // 登出按钮
    const logoutBtn = document.createElement('button');
    logoutBtn.textContent = '登出';
    logoutBtn.onclick = logout;
    logoutBtn.style.cssText = 'background:#21262d;border:none;color:#c9d1d9;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;';
    rightSection.appendChild(logoutBtn);
    
    header.appendChild(rightSection);
}

/**
 * 创建 header 元素（如果不存在）
 */
function createHeader() {
    let header = document.querySelector('.header');
    if (!header) {
        header = document.createElement('div');
        header.className = 'header';
        // 使用与 style.css 一致的样式（不设置内联样式，让 CSS 控制）
        document.body.insertBefore(header, document.body.firstChild);
    }
    // 确保 header 使用 CSS 类样式，移除可能的内联样式覆盖
    header.removeAttribute('style');
    return header;
}

/**
 * 登出函数（如果页面没有定义，则使用此函数）
 */
if (typeof logout === 'undefined') {
    window.logout = function() {
        fetch('/api/logout', { method: 'POST' })
            .then(() => {
                window.location.href = '/login';
            })
            .catch(err => {
                console.error('登出失败:', err);
                window.location.href = '/login';
            });
    };
}
