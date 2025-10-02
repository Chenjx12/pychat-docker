$(document).ready(function() {
    $('#reg-form').submit(async function(event) {
        event.preventDefault();
        const username = $('#username').val();
        const password = $('#password').val();
        const confirm_password = $('#confirm_password').val();

        // 验证用户名
        if (!username || username.length === 0) {
            showError('用户名不能为空');
            return;
        }
        if (username.length > 20) {
            showError('用户名最多20个字符');
            return;
        }

        // 验证密码
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

        // 验证确认密码
        if (password !== confirm_password) {
            showError('密码和确认密码不一致');
            return;
        }

        try {
            const res = await API('/auth/reg', { username, password, confirm_password });
            if (res.code === 0) {
                alert('注册成功，您的ID是：' + res.user_id); // 显示用户ID
                window.location.href = '/auth/login'; // 注册成功后跳转到登录页面
            } else {
                showError(res.msg || '注册失败');
            }
        } catch (error) {
            showError('注册失败，请检查网络连接或联系管理员。');
        }
    });
});

// 确保 login 函数在全局作用域中可用
window.reg = function() {
    $('#reg-form').submit();
};