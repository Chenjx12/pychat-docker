# app/room.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .extensions import socketio
from .models import db, Room, RoomMember, User, FriendRequest

room_bp = Blueprint('room', __name__, url_prefix='/rooms')

@room_bp.get('/search')
@jwt_required()
def search():
    query = request.args.get('query')
    if not query:
        return jsonify({'code': 1, 'msg': '查询参数不能为空'}), 400

    rooms = Room.query.filter(
        Room.name.like(f"%{query}%"),
        Room.group_flag == True  # 只搜索群聊
    ).all()

    room_list = [{'room_id': room.room_id, 'name': room.name} for room in rooms]
    return jsonify({'code': 0, 'rooms': room_list}), 200

@room_bp.post('/create_private')
@jwt_required()
def create_private_chat():
    current_user_id = get_jwt_identity()
    target_user_id = request.json.get('target_user_id')

    if not target_user_id:
        return jsonify({'code': 1, 'msg': '目标用户ID不能为空'}), 400

    if current_user_id == target_user_id:
        return jsonify({'code': 1, 'msg': '不能与自己创建私聊'}), 400

    # 检查是否已经是好友
    if not FriendRequest.is_friend(current_user_id, target_user_id):
        return jsonify({'code': 1, 'msg': '只能与好友创建私聊'}), 400

    # 检查是否已存在私聊房间
    existing_room = db.session.query(Room).join(
        RoomMember, Room.room_id == RoomMember.room_id
    ).filter(
        Room.group_flag == False,
        RoomMember.user_id.in_([current_user_id, target_user_id])
    ).group_by(Room.room_id).having(db.func.count(RoomMember.user_id) == 2).first()

    if existing_room:
        return jsonify({'code': 0, 'room_id': existing_room.room_id, 'msg': '私聊已存在'}), 200

    # 创建新私聊房间
    room = Room(group_flag=False, name=None, owner=None)
    db.session.add(room)
    db.session.flush()  # 获取room_id但不提交

    # 添加两个用户到房间
    member1 = RoomMember(room_id=room.room_id, user_id=current_user_id, last_read_seq=0)
    member2 = RoomMember(room_id=room.room_id, user_id=target_user_id, last_read_seq=0)

    db.session.add_all([member1, member2])
    db.session.commit()

    return jsonify({'code': 0, 'room_id': room.room_id, 'msg': '私聊创建成功'}), 201


@room_bp.post('/create_group')
@jwt_required()
def create_group_chat():
    current_user_id = get_jwt_identity()
    room_name = request.json.get('room_name')
    member_ids = request.json.get('member_ids', [])

    if not room_name:
        return jsonify({'code': 1, 'msg': '群聊名称不能为空'}), 400

    # 创建群聊房间
    room = Room(group_flag=True, name=room_name, owner=current_user_id)
    db.session.add(room)
    db.session.flush()

    # 添加创建者到房间
    creator_member = RoomMember(room_id=room.room_id, user_id=current_user_id, last_read_seq=0)
    db.session.add(creator_member)

    # 添加其他成员到房间
    for member_id in member_ids:
        if member_id != current_user_id and FriendRequest.is_friend(current_user_id, member_id):
            member = RoomMember(room_id=room.room_id, user_id=member_id, last_read_seq=0)
            db.session.add(member)

    db.session.commit()

    # 通知所有成员有新群聊
    for member_id in [current_user_id] + member_ids:
        if member_id != current_user_id:  # 不重复通知自己
            socketio.emit('new_group', {
                'room_id': room.room_id,
                'room_name': room_name,
                'creator_id': current_user_id
            }, room=member_id)

    return jsonify({'code': 0, 'room_id': room.room_id, 'msg': '群聊创建成功'}), 201


@room_bp.get('/get_user_rooms')
@jwt_required()
def get_user_rooms():
    current_user_id = get_jwt_identity()

    # 获取用户加入的所有房间
    user_rooms = db.session.query(Room).join(
        RoomMember, Room.room_id == RoomMember.room_id
    ).filter(RoomMember.user_id == current_user_id).all()

    room_list = []
    for room in user_rooms:
        # 获取房间成员信息
        members = db.session.query(User).join(
            RoomMember, User.user_id == RoomMember.user_id
        ).filter(RoomMember.room_id == room.room_id).all()

        member_info = [{
            'user_id': member.user_id,
            'username': member.username
        } for member in members]

        # 对于私聊，显示对方用户名
        if not room.group_flag:
            other_member = next((m for m in members if m.user_id != current_user_id), None)
            display_name = other_member.username if other_member else '未知用户'
        else:
            display_name = room.name

        room_list.append({
            'id': room.room_id,
            'name': display_name,
            'is_group': room.group_flag,
            'members': member_info,
            'last_read_seq': next((rm.last_read_seq for rm in room.members if rm.user_id == current_user_id), 0)
        })

    return jsonify({'code': 0, 'rooms': room_list}), 200


@room_bp.post('/add_member')
@jwt_required()
def add_member_to_room():
    current_user_id = get_jwt_identity()
    room_id = request.json.get('room_id')
    member_id = request.json.get('member_id')

    if not room_id or not member_id:
        return jsonify({'code': 1, 'msg': '房间ID和成员ID不能为空'}), 400

    # 检查房间是否存在且当前用户是群主
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'code': 1, 'msg': '房间不存在'}), 404

    if not room.group_flag:
        return jsonify({'code': 1, 'msg': '不能向私聊添加成员'}), 400

    if room.owner != current_user_id:
        return jsonify({'code': 1, 'msg': '只有群主可以添加成员'}), 403

    # 检查是否已经是好友
    if not FriendRequest.is_friend(current_user_id, member_id):
        return jsonify({'code': 1, 'msg': '只能添加好友到群聊'}), 400

    # 检查是否已在房间中
    existing_member = RoomMember.query.filter_by(room_id=room_id, user_id=member_id).first()
    if existing_member:
        return jsonify({'code': 1, 'msg': '用户已在群聊中'}), 400

    # 添加成员
    member = RoomMember(room_id=room_id, user_id=member_id, last_read_seq=0)
    db.session.add(member)
    db.session.commit()

    # 通知新成员
    socketio.emit('added_to_group', {
        'room_id': room_id,
        'room_name': room.name,
        'added_by': current_user_id
    }, room=member_id)

    # 通知现有成员
    socketio.emit('new_member', {
        'room_id': room_id,
        'member_id': member_id,
        'username': User.find_by_id(member_id).username
    }, room=room_id, include_self=False)

    return jsonify({'code': 0, 'msg': '成员添加成功'}), 200


@room_bp.post('/leave_room')
@jwt_required()
def leave_room():
    current_user_id = get_jwt_identity()
    room_id = request.json.get('room_id')

    if not room_id:
        return jsonify({'code': 1, 'msg': '房间ID不能为空'}), 400

    # 检查房间是否存在
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'code': 1, 'msg': '房间不存在'}), 404

    # 检查用户是否在房间中
    membership = RoomMember.query.filter_by(room_id=room_id, user_id=current_user_id).first()
    if not membership:
        return jsonify({'code': 1, 'msg': '您不在该房间中'}), 400

    # 如果是群主，需要转移群主权限或解散群聊
    if room.group_flag and room.owner == current_user_id:
        # 查找其他成员
        other_members = RoomMember.query.filter(
            RoomMember.room_id == room_id,
            RoomMember.user_id != current_user_id
        ).all()

        if other_members:
            # 转移群主权限给第一个其他成员
            new_owner = other_members[0].user_id
            room.owner = new_owner
            db.session.add(room)

            # 通知所有成员群主变更
            socketio.emit('owner_changed', {
                'room_id': room_id,
                'new_owner_id': new_owner,
                'new_owner_name': User.find_by_id(new_owner).username
            }, room=room_id)
        else:
            # 没有其他成员，删除房间
            db.session.delete(room)

    # 移除成员关系
    db.session.delete(membership)
    db.session.commit()

    # 通知其他成员
    socketio.emit('member_left', {
        'room_id': room_id,
        'user_id': current_user_id,
        'username': User.find_by_id(current_user_id).username
    }, room=room_id, include_self=False)

    return jsonify({'code': 0, 'msg': '已退出房间'}), 200