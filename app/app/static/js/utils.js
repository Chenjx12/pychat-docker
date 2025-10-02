// 从 Cookie 中获取 JWT（服务端已 Set-Cookie）
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// 设置 Cookie
function setCookie(name, value, options) {
    options = options || {};
    let expires = options.expires;
    if (typeof expires == "number" && expires) {
        let d = new Date();
        d.setTime(d.getTime() + expires * 1000);
        expires = options.path ? "expires=" + d.toGMTString() + "; path=" + options.path : "expires=" + d.toGMTString();
    }
    let path = options.path ? "; path=" + options.path : "";
    let secure = options.secure ? "; secure" : "";
    document.cookie = name + "=" + value + expires + path + secure;
}

// API 请求工具函数
const API = (path, body = {}, method = 'POST') => {
    const token = getCookie('access_token_cookie');
    const headers = {
        'Content-Type': 'application/json'
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (method === 'GET') {
        return fetch(path, {
            method: method,
            headers: headers
        }).then(r => r.json()).catch(error => {
            console.error('API 请求失败:', error);
            alert('API 请求失败，请检查网络连接或联系管理员。');
            throw error;
        });
    } else {
        return fetch(path, {
            method: method,
            headers: headers,
            body: JSON.stringify(body)
        }).then(r => r.json()).catch(error => {
            console.error('API 请求失败:', error);
            alert('API 请求失败，请检查网络连接或联系管理员。');
            throw error;
        });
    }
};

// 刷新 Token
async function refreshToken() {
    const refreshToken = getCookie('refresh_token_cookie');
    if (!refreshToken) {
        alert('用户未登录');
        return Promise.reject(new Error('用户未登录'));
    }
    try {
        const res = await API('/auth/refresh', {}, 'POST');
        if (res.access_token) {
            setCookie('access_token_cookie', res.access_token, { path: '/' });
            return res;
        } else {
            alert('登录已失效，请重新登录');
            window.location.href = '/auth/login';
            return Promise.reject(new Error('Token refresh failed'));
        }
    } catch (error) {
        alert('登录已失效，请重新登录');
        window.location.href = '/auth/login';
        return Promise.reject(error);
    }
}

// 从 JWT Token 中获取用户信息
function getJwtIdentity(token) {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.identity;
}

// 显示错误信息
function showError(message) {
    alert(message);
}