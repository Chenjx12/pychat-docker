$(document).ready(function() {
    // 上传头像
    $('#upload-avatar-btn').click(uploadAvatar);

    // 修改用户名
    $('#update-username-btn').click(updateUsername);

    // 修改密码
    $('#update-password-btn').click(updatePassword);

    // 退出登录
    $('#logout-btn').click(logout);

    // 显示当前用户名
    displayCurrentUsername();
});

function displayCurrentUsername() {
    const token = getCookie('access_token_cookie');
    if (token) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const username = payload.username;
        $('#profile-username-display').text(username);
    }
}

function uploadAvatar() {
    const avatarInput = $('#profile-avatar')[0];
    if (avatarInput.files.length === 0) {
        showError('请选择一个头像文件');
        return;
    }

    const formData = new FormData();
    formData.append('avatar', avatarInput.files[0]);

    fetch('/center/upload-avatar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            showError('头像上传成功');
            // 更新页面上的头像预览
            const reader = new FileReader();
            reader.onloadend = function() {
                $('#profile-avatar-preview').attr('src', reader.result);
            }
            reader.readAsDataURL(avatarInput.files[0]);
        } else {
            showError(data.msg || '头像上传失败');
        }
    });
}

async function updateUsername() {
    const newUsername = $('#profile-username').val().trim();
    if (newUsername === '') {
        showError('请输入新用户名');
        return;
    }

    const res = await API('/center/update-username', { newUsername });
    if (res.code === 0) {
        showError('用户名修改成功');
        // 更新页面上的用户名
        $('#profile-username-display').text(newUsername);
    } else {
        showError(res.msg || '用户名修改失败');
    }
}

async function updatePassword() {
    const currentPassword = $('#profile-password').val();
    const newPassword = $('#profile-new-password').val();
    if (currentPassword === '' || newPassword === '') {
        showError('请输入当前密码和新密码');
        return;
    }

    const res = await API('/center/update-password', { currentPassword, newPassword });
    if (res.code === 0) {
        showError('密码修改成功');
    } else {
        showError(res.msg || '密码修改失败');
    }
}

// 退出登录
function logout() {
    document.cookie = 'access_token_cookie=; Max-Age=0; path=/';
    window.location.href = '/'; // 重定向到主页
}