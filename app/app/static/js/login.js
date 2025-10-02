$(document).ready(function() {
    $('#login-form').submit(async function(event) {
        event.preventDefault();
        const identifier = $('#username').val(); // 使用 jQuery
        const password = $('#password').val(); // 使用 jQuery

        try {
            const res = await API('/auth/login', { identifier, password });
            if (res.code === 0) {
                // 登录成功后的处理
                window.location.href = '/chat'; // 假设聊天页面在 /chat
            } else {
                showError(res.msg || '登录失败');
            }
        } catch (error) {
            showError('登录失败，请检查网络连接或联系管理员。');
        }
    });
});

// 确保 login 函数在全局作用域中可用
window.login = function() {
    $('#login-form').submit();
};