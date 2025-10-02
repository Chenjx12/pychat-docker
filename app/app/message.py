"""
历史消息分页 + WebSocket 收发
- Redis 统计在线人数
- 消息持久化
- 支持房间聊天功能
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from flask_socketio import emit, disconnect, join_room, leave_room
from .models import db, Message, Room, RoomMember, User
from .utils import init_redis
from .extensions import socketio

msg_bp = Blueprint('msg', __name__, url_prefix='')
r = init_redis()

@msg_bp.get('/history')
@jwt_required()
def history():
    page = int(request.args.get('page', 1))
    size = 50
    data = Message.get_page(page, size)
    return {'data': data, 'has_more': len(data) == size}

@msg_bp.get('/room_history')
@jwt_required()
def room_history():
    room_id = request.args.get('room_id', 0, type=int)
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 50, type=int)

    # 检查用户是否在房间中
    current_user_id = get_jwt_identity()
    if room_id != 0:
        membership = RoomMember.query.filter_by(room_id=room_id, user_id=current_user_id).first()
        if not membership:
            return jsonify({'code': 1, 'msg': '您不在该房间中'}), 403

    messages = Message.get_messages_for_room(room_id, page, size)
    data = [{'sender_id': msg['sender'], 'sender': msg['username'], 'body': msg['body'], 'ts': msg['ts'], 'seq': msg['seq']} for msg in messages]

    if not data:
        return jsonify({'code': 0, 'data': [], 'has_more': False}), 200

    return jsonify({'code': 0, 'data': data, 'has_more': len(data) == size}), 200

@socketio.on('connect')
def on_connect():
    try:
        # 从查询参数获取token
        token = request.args.get('token')
        if not token:
            disconnect()
            return False

        # 手动验证token
        decoded_token = decode_token(token)
        current_user = decoded_token['sub']

        # 存储用户ID和sessionID的映射
        r.sadd('online', request.sid)
        r.set(f'session:{request.sid}', current_user)
        r.set(f'user:{current_user}:session', request.sid)

        # 让用户加入其所在的所有房间
        memberships = RoomMember.query.filter_by(user_id=current_user).all()
        for membership in memberships:
            join_room(str(membership.room_id))

        # 加入全局房间
        join_room('0')

        emit('online', {'count': r.scard('online')}, broadcast=True)
        print(f'[WS] 用户 {current_user} 已连接')
    except Exception as e:
        print(f'[WS] 连接失败: {str(e)}')
        disconnect()
        return False

@socketio.on('disconnect')
def on_disconnect():
    session_id = request.sid
    user_id = r.get(f'session:{session_id}')
    if user_id:
        r.delete(f'session:{session_id}')
        r.delete(f'user:{user_id}:session')
    r.srem('online', session_id)
    emit('online', {'count': r.scard('online')}, broadcast=True)
    print(f'[WS] 用户 {user_id} 已断开连接')

@socketio.on('join_room')
@jwt_required()
def on_join_room(data):
    room_id = data.get('room_id')
    user_id = get_jwt_identity()

    # 检查用户是否在房间中
    membership = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
    if not membership and room_id != 0:  # 全局房间不需要检查
        return

    join_room(str(room_id))
    print(f'[WS] 用户 {user_id} 加入房间 {room_id}')

@socketio.on('leave_room')
@jwt_required()
def on_leave_room(data):
    room_id = data.get('room_id')
    user_id = get_jwt_identity()

    leave_room(str(room_id))
    print(f'[WS] 用户 {user_id} 离开房间 {room_id}')

@socketio.on('chat')
@jwt_required()
def on_chat(json):
    user_id = get_jwt_identity()
    body = str(json.get('body', ''))[:2000]
    room_id = json.get('room_id', 0)  # 默认为全局房间

    # 检查用户是否在房间中
    if room_id != 0:
        membership = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
        if not membership:
            return jsonify({'code': 1, 'msg': '您不在该房间中'}), 403

    # 保存消息
    Message.save(user_id, body, room_id)

    # 获取发送者用户名
    user = User.find_by_id(user_id)
    username = user.username if user else user_id

    # 发送消息到房间
    emit('chat', {
        'sender_id': user_id,
        'sender': username,
        'body': body,
        'ts': datetime.utcnow().isoformat(),
        'room_id': room_id
    }, room=str(room_id))  # 使用房间ID作为房间名

@socketio.on('typing')
@jwt_required()
def on_typing(json):
    user_id = get_jwt_identity()
    room_id = json.get('room_id', 0)
    is_typing = json.get('is_typing', False)

    # 获取发送者用户名
    user = User.find_by_id(user_id)
    username = user.username if user else user_id

    # 发送输入状态到房间
    emit('typing', {
        'user_id': user_id,
        'username': username,
        'is_typing': is_typing
    }, room=str(room_id), include_self=False)

@socketio.on('read_receipt')
@jwt_required()
def on_read_receipt(json):
    user_id = get_jwt_identity()
    room_id = json.get('room_id', 0)
    last_read_seq = json.get('last_read_seq', 0)

    # 更新用户在该房间的最后阅读位置
    if room_id != 0:
        membership = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
        if membership:
            membership.last_read_seq = last_read_seq
            db.session.commit()

            # 发送已读回执到房间
            emit('read_receipt', {
                'user_id': user_id,
                'room_id': room_id,
                'last_read_seq': last_read_seq
            }, room=str(room_id))

@socketio.on('new_private_chat')
def handle_new_private_chat(data):
    room_id = data['room_id']
    user_id = data['user_id']
    friend_user_id = data['friend_user_id']

    # 通知用户有新的私聊房间
    emit('new_private_chat', {
        'room_id': room_id,
        'friend_user_id': friend_user_id
    }, room=user_id)

