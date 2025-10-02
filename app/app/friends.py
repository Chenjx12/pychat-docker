from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from . import socketio
from .models import db, User, FriendRequest, RoomMember, Room
from flask_socketio import emit

friends_bp = Blueprint('friends', __name__, url_prefix='/friends')

@friends_bp.get('/search_user')
@jwt_required()
def search_user():
    query = request.args.get('query')
    if not query:
        return jsonify({'code': 1, 'msg': '查询参数不能为空'}), 400

    users = User.query.filter(
        (User.username.like(f"%{query}%")) | (User.user_id.like(f"%{query}%"))
    ).all()

    user_list = [{'username': user.username, 'user_id': user.user_id} for user in users]
    return jsonify({'code': 0, 'users': user_list}), 200

@friends_bp.post('/send_friend_request')
@jwt_required()
def send_friend_request():
    data = request.get_json()
    friend_user_id = data.get('friend_user_id')
    current_user_id = get_jwt_identity()

    if not User.find_by_id(friend_user_id):
        return jsonify({'code': 1, 'msg': '用户不存在'}), 404

    if friend_user_id == current_user_id:
        return jsonify({'code': 1, 'msg': '不能添加自己为好友'}), 400

    if FriendRequest.is_pending(current_user_id, friend_user_id):
        return jsonify({'code': 1, 'msg': '好友请求已发送'}), 400

    if FriendRequest.is_friend(current_user_id, friend_user_id):
        return jsonify({'code': 1, 'msg': '已经是好友'}), 400

    # 检查是否已经发送过好友请求
    if FriendRequest.query.filter(
        or_(
            (FriendRequest.user_id == current_user_id) & (FriendRequest.friend_id == friend_user_id),
            (FriendRequest.user_id == friend_user_id) & (FriendRequest.friend_id == current_user_id)
        ),
        FriendRequest.status != 2  # 排除已拒绝的请求
    ).first():
        return jsonify({'code': 1, 'msg': '好友请求已发送或已经是好友'}), 400

    FriendRequest.create(current_user_id, friend_user_id)
    emit('new_friend_request', {'user_id': current_user_id}, room=friend_user_id, namespace='/')
    return jsonify({'code': 0, 'msg': '好友请求已发送'}), 201


@friends_bp.post('/handle_friend_request')
@jwt_required()
def handle_friend_request():
    data = request.get_json()
    user_id = data.get('user_id')
    action = data.get('action')  # 'accept' 或 'reject'

    current_user_id = get_jwt_identity()
    if action == 'accept':
        if FriendRequest.accept_request(user_id, current_user_id):
            # 创建私聊房间
            room = Room(group_flag=False, name=None, owner=None)
            db.session.add(room)
            db.session.flush()  # 获取room_id但不提交

            # 添加两个用户到房间
            member1 = RoomMember(room_id=room.room_id, user_id=current_user_id, last_read_seq=0)
            member2 = RoomMember(room_id=room.room_id, user_id=user_id, last_read_seq=0)

            db.session.add_all([member1, member2])
            db.session.commit()

            # 通知双方有新的私聊房间
            socketio.emit('new_private_chat', {
                'room_id': room.room_id,
                'user_id': current_user_id,
                'friend_user_id': user_id
            }, room=current_user_id)

            socketio.emit('new_private_chat', {
                'room_id': room.room_id,
                'user_id': user_id,
                'friend_user_id': current_user_id
            }, room=user_id)

            return jsonify({'code': 0, 'msg': '好友请求已接受'}), 200
        else:
            return jsonify({'code': 1, 'msg': '好友请求不存在'}), 404
    elif action == 'reject':
        if FriendRequest.reject_request(user_id, current_user_id):
            return jsonify({'code': 0, 'msg': '好友请求已拒绝'}), 200
    else:
        return jsonify({'code': 1, 'msg': '无效的操作'}), 400

@friends_bp.get('/get_friend_requests')
@jwt_required()
def get_friend_requests():
    current_user_id = get_jwt_identity()
    requests = FriendRequest.query.filter_by(friend_id=current_user_id, status=0).all()
    request_list = [{'user_id': req.user_id, 'username': User.find_by_id(req.user_id).username} for req in requests]
    return jsonify({'code': 0, 'requests': request_list}), 200


@friends_bp.get('/get_friends')
@jwt_required()
def get_friends():
    current_user_id = get_jwt_identity()

    # 查询当前用户的所有好友关系
    friendships = FriendRequest.query.filter(
        or_(
            FriendRequest.user_id == current_user_id,
            FriendRequest.friend_id == current_user_id
        ),
        FriendRequest.status == 1  # 只获取已接受的好友关系
    ).all()

    # 处理查询结果
    friend_list = []
    for friendship in friendships:
        # 确定好友的ID（不是当前用户的ID）
        if friendship.user_id == current_user_id:
            # 当前用户是发起方，好友是接收方
            friend_id = friendship.friend_id
        else:
            # 当前用户是接收方，好友是发起方
            friend_id = friendship.user_id

        # 获取好友的用户信息
        friend_user = User.find_by_id(friend_id)
        if friend_user:
            friend_list.append({
                'user_id': friend_user.user_id,
                'username': friend_user.username
            })

    return jsonify({'code': 0, 'friends': friend_list}), 200

@friends_bp.post('/delete_friend')
@jwt_required()
def delete_friend():
    data = request.get_json()
    friend_id = data.get('friend_id')
    current_user_id = get_jwt_identity()

    # 查找好友关系（双向）
    friendship = FriendRequest.query.filter(
        or_(
            (FriendRequest.user_id == current_user_id) & (FriendRequest.friend_id == friend_id),
            (FriendRequest.user_id == friend_id) & (FriendRequest.friend_id == current_user_id)
        ),
        FriendRequest.status == 1  # 只删除已接受的好友关系
    ).first()

    if friendship:
        db.session.delete(friendship)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '好友删除成功'}), 200
    else:
        return jsonify({'code': 1, 'msg': '好友关系不存在'}), 404
