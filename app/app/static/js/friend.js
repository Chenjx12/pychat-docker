$(document).ready(function() {
    // 初始化好友请求列表
    showFriendRequests();

    // 为搜索按钮绑定事件
    $('#search-button').on('click', searchUserAndRooms);
    // 为好友申请按钮绑定点击事件
    $('#friend-request-button').on('click', function() {
        openFriendRequestPopup();
    });
    // 为弹窗关闭按钮绑定点击事件
    $('.popup-close').on('click', function() {
        closeFriendRequestPopup();
    });
});

// 搜索用户
async function searchUserAndRooms() {
    const query = $('#search-input').val();
    if (!query) {
        showError('请输入搜索内容');
        return;
    }

    const userList = $('#chat-list');
    userList.empty();

    try {
        // 搜索用户
        const userData = await API(`/friends/search_user?query=${encodeURIComponent(query)}`, {}, 'GET');
        if (userData.code === 0) {
            const users = userData.users;
            users.forEach(user => {
                const listItem = $('<li>').text(`${user.username} (${user.user_id})`);
                listItem.on('click', () => {
                    sendFriendRequest(user.user_id);  // 传递用户ID
                });
                userList.append(listItem);
            });
        } else {
            showError(userData.msg || '用户搜索失败');
        }
    } catch (error) {
        showError('用户搜索失败，请稍后重试');
    }

    try {
        // 搜索群聊
        const roomData = await API(`/rooms/search?query=${encodeURIComponent(query)}`, {}, 'GET');
        if (roomData.code === 0) {
            const rooms = roomData.rooms;
            rooms.forEach(room => {
                const listItem = $('<li>').text(`群聊: ${room.name} (${room.room_id})`);
                listItem.on('click', () => {
                    joinRoom(room.room_id);  // 加入群聊
                });
                userList.append(listItem);
            });
        } else {
            showError(roomData.msg || '群聊搜索失败');
        }
    } catch (error) {
        showError('群聊搜索失败，请稍后重试');
    }
}

// 发送好友申请
function sendFriendRequest(friendUserId) {
    // 首先检查是否已经是好友
    API('/friends/get_friends', {}, 'GET')
    .then(data => {
        if (data.code === 0) {
            const friends = data.friends;
            // 检查是否已经是好友
            const isAlreadyFriend = friends.some(friend => friend.user_id === friendUserId);

            if (isAlreadyFriend) {
                showError('该用户已经是您的好友');
                return;
            }

            // 如果不是好友，继续发送好友请求
            return API('/friends/send_friend_request', { friend_user_id: friendUserId }, 'POST');
        } else {
            throw new Error('获取好友列表失败');
        }
    })
    .then(data => {
        if (data) {
            if (data.code === 0) {
                showSuccess('好友请求已发送');
            } else {
                showError(data.msg || '发送好友请求失败');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('操作失败，请稍后重试');
    });
}


// 处理好友申请
function handleFriendRequest(userId, action) {
    API('/friends/handle_friend_request', { user_id: userId, action: action })
        .then(data => {
            if (data.code === 0) {
                showError(data.msg);
                showFriendRequests();
                if (action === 'accept') {
                    // 跳转到新私聊房间
                    window.location.href = `/chat?room=${data.room_id}`;
                    }
            } else {
                showError(data.msg || '处理好友申请失败');
            }
        })
        .catch(error => {
            if (error.includes('Token has expired')) {
                refreshToken()
                    .then(refreshedData => {
                        if (refreshedData.access_token) {
                            setCookie('access_token_cookie', refreshedData.access_token, { path: '/' });
                            handleFriendRequest(userId, action); // 重新发起请求
                        } else {
                            showError('登录已失效，请重新登录');
                            window.location.href = '/auth/login';
                        }
                    })
                    .catch(refreshError => {
                        showError('登录已失效，请重新登录');
                        window.location.href = '/auth/login';
                    });
            } else {
                showError(error);
            }
        });
}

// 显示好友申请
function showFriendRequests() {
    API('/friends/get_friend_requests', {}, 'GET')
        .then(data => {
            if (data.code === 0) {
                const requests = data.requests;
                const requestList = $('#friend-request-list');
                requestList.empty();
                requests.forEach(request => {
                    const listItem = $('<li>').text(`${request.user_id} 请求加你为好友`);
                      // 创建按钮容器
                    const buttonContainer = $('<div>').addClass('button-container');
                    const acceptButton = $('<button>').text('接受').on('click', () => handleFriendRequest(request.user_id, 'accept'));
                    const rejectButton = $('<button>').text('拒绝').on('click', () => handleFriendRequest(request.user_id, 'reject'));
                    listItem.append(acceptButton, ' ', rejectButton);
                    requestList.append(listItem);
                });
            } else {
                showError(data.msg || '获取好友申请失败');
            }
        })
        .catch(error => {
            if (error.includes('Token has expired')) {
                refreshToken()
                    .then(refreshedData => {
                        if (refreshedData.access_token) {
                            setCookie('access_token_cookie', refreshedData.access_token, { path: '/' });
                            showFriendRequests(); // 重新发起请求
                        } else {
                            showError('登录已失效，请重新登录');
                            window.location.href = '/auth/login';
                        }
                    })
                    .catch(refreshError => {
                        showError('登录已失效，请重新登录');
                        window.location.href = '/auth/login';
                    });
            } else {
                showError(error);
            }
        });
}

// 打开好友申请弹窗
function openFriendRequestPopup() {
    $('#friend-request-popup').show();
    showFriendRequests();
}

// 关闭好友申请弹窗
function closeFriendRequestPopup() {
    $('#friend-request-popup').hide();
}
