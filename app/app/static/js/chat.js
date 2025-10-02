let currentRoomId; // 声明全局变量
let currentUserId; // 声明全局变量

$(document).ready(function() {
    console.log("Document is ready. Initializing chat functionality...");

    // 获取 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const roomId = urlParams.get('room');

    if (roomId) {
        // 进入指定的聊天界面
        currentRoomId = roomId;
        $('#chat-room-name').text(`聊天: ${roomId}`);
    } else {
        // 默认进入全局聊天室
        currentRoomId = 1;
        $('#chat-room-name').text('全局聊天');
    }

    // 获取当前登录用户的用户ID
    currentUserId = getJwtIdentity(getCookie('access_token_cookie'));

    // 初始化 WebSocket 连接
    if (getCookie('access_token_cookie')) {
        connectWS();
    }

    // 为发送按钮绑定事件
    $('#chat-send-button').on('click', send);

    // 为输入框绑定回车键发送
    $('#chat-input-field').on('keypress', function(e) {
        if (e.which === 13) { // 回车键
            send();
            return false; // 阻止默认行为
        }
    });

    // 为汉堡菜单绑定点击事件
    $('.hamburger-link').on('click', function(event) {
        event.preventDefault(); // 阻止默认行为
        window.location.href = '/center'; // 跳转到 /center
    });

    // 为空心圆绑定点击事件
    $('.circle-link').on('click', function(event) {
        event.preventDefault(); // 阻止默认行为
        window.location.href = '/contact'; // 跳转到 /contact
    });

    // 加载房间历史消息
    loadRoomHistory(currentRoomId);
});

// WebSocket 连接
let socket;
function connectWS() {
    const token = getCookie('access_token_cookie');
    if (!token) {
        showError('未登录');
        location.reload();
        return;
    }

    socket = io({
        transports: ['websocket'],
        query: { token } // JWT 放在 query，服务端从 auth.token 取
    });

    socket.on('connect', () => {
        console.log('[WS] 已连接');
    });

    socket.on('connect_error', (err) => {
        console.error('[WS] 连接失败', err.message);
        // 常见 401/422 说明 JWT 失效
        if (err.message.includes('401') || err.message.includes('422')) {
            refreshToken()
                .then(refreshedData => {
                    if (refreshedData.access_token) {
                        setCookie('access_token_cookie', refreshedData.access_token, { path: '/' });
                        connectWS(); // 重新连接 WebSocket
                    } else {
                        showError('登录已失效，请重新登录');
                        window.location.href = '/auth/login';
                    }
                })
                .catch(refreshError => {
                    showError('登录已失效，请重新登录');
                    window.location.href = '/auth/login';
                });
        }
    });

    socket.on('chat', function(data) {
        if (data.room_id === currentRoomId) {
            addMsg(data.sender, data.body, data.sender_id);
        }
    });

    socket.on('new_private_chat', function(data) {
        const room_id = data.room_id;
        const friend_user_id = data.friend_user_id;
        // 更新当前房间 ID
        currentRoomId = room_id;
        // 跳转到新私聊房间
        window.location.href = `/chat?room=${room_id}`;
    });
}

// 发送消息
function send() {
    const txt = $('#chat-input-field').val().trim();
    if (!txt || !socket) return;
    socket.emit('chat', { body: txt, room_id: currentRoomId });
    $('#chat-input-field').val('');
}

// 渲染消息
function addMsg(user, body, senderId) {
    const self = senderId === currentUserId;
    const div = $('<div>').addClass('msg' + (self ? ' self' : '')).text(`${user}: ${body}`);
    $('#chat-messages').append(div);
    $('#chat-messages').scrollTop($('#chat-messages')[0].scrollHeight);
}

// 初始化房间列表
function loadRooms() {
    API('/rooms/get_user_rooms', {}, 'GET')
        .done(function(data) {
            if (data.code === 0) {
                const rooms = data.rooms;
                const chatList = $('#chat-list');
                chatList.empty();

                // 添加全局聊天室
                chatList.append(`
                    <li class="room-item ${currentRoomId === 1 ? 'active' : ''}" data-room-id="1">
                        <span class="room-name">全局聊天</span>
                    </li>
                `);

                // 添加用户所在的房间
                rooms.forEach(room => {
                    chatList.append(`
                        <li class="room-item ${currentRoomId === room.id ? 'active' : ''}" data-room-id="${room.id}">
                            <span class="room-name">${room.name}</span>
                            <span class="room-members">(${room.members.length}人)</span>
                        </li>
                    `);
                });

                // 添加创建房间按钮
                chatList.append(`
                    <li id="create-room-btn">
                        <button>创建新房间</button>
                    </li>
                `);

                // 绑定房间点击事件
                $('.room-item').on('click', function() {
                    const roomId = $(this).data('room-id');
                    switchRoom(roomId);
                });

                // 绑定创建房间按钮事件
                $('#create-room-btn button').on('click', showCreateRoomDialog);
            } else {
                console.error('获取房间列表失败:', data.msg);
            }
        })
        .fail(function(xhr, status, error) {
            console.error('获取房间列表失败:', error);
        });
}

// 切换房间
function switchRoom(roomId) {
    currentRoomId = roomId;

    // 更新UI
    $('.room-item').removeClass('active');
    $(`.room-item[data-room-id="${roomId}"]`).addClass('active');

    // 更新房间名称显示
    const roomName = $(`.room-item[data-room-id="${roomId}"] .room-name`).text();
    $('#chat-room-name').text(roomName);

    // 清空消息区域
    $('#chat-messages').empty();

    // 加载该房间的历史消息
    loadRoomHistory(roomId);
}

// 加载房间历史消息
async function loadRoomHistory(roomId) {
    try {
        const data = await API(`/room_history?room_id=${roomId}&page=1&size=50`, {}, 'GET');
        if (data.code === 0) {
            if (data.data.length === 0) {
                // 没有历史消息，不显示任何内容或显示友好的提示信息
                $('#chat-messages').html('<p class="no-messages">没有历史消息</p>');
            } else {
                // 有历史消息，显示消息
                data.data.forEach(msg => {
                    addMsg(msg.sender, msg.body, msg.sender_id);
                });
            }
        } else {
            // 处理其他错误情况
            showError(data.msg || '加载历史消息失败');
        }
    } catch (error) {
        // 处理网络错误
        showError('加载历史消息失败，请稍后重试');
    }
}

// 显示创建房间对话框
function showCreateRoomDialog() {
    // 这里实现创建房间的UI和逻辑
    const dialog = `
        <div id="create-room-dialog" class="popup">
            <div class="popup-content">
                <span class="popup-close">&times;</span>
                <h2>创建新房间</h2>
                <div>
                    <label>房间类型:</label>
                    <select id="room-type">
                        <option value="private">私聊</option>
                        <option value="group">群聊</option>
                    </select>
                </div>
                <div id="private-room-options">
                    <label>选择好友:</label>
                    <select id="friend-select"></select>
                </div>
                <div id="group-room-options" style="display:none">
                    <label>群聊名称:</label>
                    <input type="text" id="group-name">
                    <label>选择成员:</label>
                    <div id="friend-multiselect"></div>
                </div>
                <button id="create-room-submit">创建</button>
            </div>
        </div>
    `;

    $('body').append(dialog);
    $('#create-room-dialog').show();

    // 加载好友列表
    loadFriendsForRoomCreation();

    // 绑定事件
    $('#room-type').on('change', function() {
        if ($(this).val() === 'private') {
            $('#private-room-options').show();
            $('#group-room-options').hide();
        } else {
            $('#private-room-options').hide();
            $('#group-room-options').show();
        }
    });

    $('.popup-close').on('click', function() {
        $('#create-room-dialog').remove();
    });

    $('#create-room-submit').on('click', createRoom);
}