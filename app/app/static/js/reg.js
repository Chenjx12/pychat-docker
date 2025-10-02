$(document).ready(function() {
    $('#reg-form').submit(async function(event) {
        event.preventDefault();
        const username = $('#username').val();
        const password = $('#password').val();
        const confirm_password = $('#confirm_password').val();

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