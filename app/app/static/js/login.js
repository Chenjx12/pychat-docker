$(document).ready(function() {
    $('#login-form').submit(async function(event) {
        event.preventDefault();
        const identifier = $('#username').val(); // 使用 jQuery
        const password = $('#password').val(); // 使用 jQuery

        // 验证用户名和密码
        if (!identifier || identifier.length === 0) {
            showError('用户名不能为空');
            return;
        }
        if (identifier.length > 20) {
            showError('用户名最多20个字符');
            return;
        }
        if (!password || password.length === 0) {
            showError('密码不能为空');
            return;
        }
        if (password.length < 8 || password.length > 16) {
            showError('密码长度必须为8到16个字符');
            return;
        }
        if (!/^[a-zA-Z0-9]+$/.test(password)) {
            showError('密码不能包含特殊字符');
            return;
        }

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