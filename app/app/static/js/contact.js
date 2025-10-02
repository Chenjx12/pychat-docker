$(document).ready(function() {
    loadContacts();
    loadGroups(); // 加载群聊列表
    $('#back-button').click(function() {
        window.location.href = '/chat';
    });
});

function loadContacts() {
    API('/friends/get_friends', {}, 'GET')
        .then(data => {
            if (data.code === 0) {
                const friends = data.friends;
                let friendsHtml = '';
                friends.forEach(friend => {
                    friendsHtml += `
                        <li class="friend-item">
                            <span>${friend.username} (${friend.user_id})</span>
                            <button class="btn-delete" onclick="deleteFriend('${friend.user_id}')">删除好友</button>
                        </li>
                    `;
                });
                $('#friends').html(friendsHtml);
                // 为好友列表项绑定双击事件
                $('.friend-item').dblclick(function() {
                    const friendUserId = $(this).find('span').text().match(/\((\d+)\)/)[1];
                    window.location.href = `/chat?user=${friendUserId}`;
                });
            } else {
                $('#friends').html('<p class="no-contacts">没有联系人</p>');
            }
        })
        .catch(error => {
            console.error('加载联系人失败:', error);
            showError('加载联系人失败，请检查网络连接或联系管理员。');
        });
}

function loadGroups() {
    API('/rooms/get_user_rooms', {}, 'GET')
        .then(data => {
            if (data.code === 0) {
                const groups = data.rooms.filter(room => room.group_flag); // 过滤出群聊
                let groupsHtml = '';
                groups.forEach(group => {
                    groupsHtml += `
                        <li class="group-item">
                            <span>${group.name} (${group.room_id})</span>
                            <button class="btn-leave" onclick="leaveGroup('${group.room_id}')">退出群聊</button>
                        </li>
                    `;
                });
                $('#groups').html(groupsHtml);
                // 为群聊列表项绑定双击事件
                $('.group-item').dblclick(function() {
                    const groupId = $(this).find('span').text().match(/\((\d+)\)/)[1];
                    window.location.href = `/chat?group=${groupId}`;
                });
            } else {
                $('#groups').html('<p class="no-groups">没有群聊</p>');
            }
        })
        .catch(error => {
            console.error('加载群聊失败:', error);
            showError('加载群聊失败，请检查网络连接或联系管理员。');
        });
}

function deleteFriend(friendUserId) {
    API('/friends/delete_friend', { friend_user_id: friendUserId })
        .then(data => {
            if (data.code === 0) {
                showError(data.msg);
                loadContacts();
            } else {
                showError(data.msg || '删除联系人失败');
            }
        })
        .catch(error => {
            console.error('删除联系人失败:', error);
        });
}

function leaveGroup(groupId) {
    API('/rooms/leave_group', { room_id: groupId })
        .then(data => {
            if (data.code === 0) {
                showError(data.msg);
                loadGroups();
            } else {
                showError(data.msg || '退出群聊失败');
            }
        })
        .catch(error => {
            console.error('退出群聊失败:', error);
        });
}