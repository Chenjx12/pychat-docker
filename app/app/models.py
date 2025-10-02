"""
SQLAlchemy ORM + 复用连接池
"""
import hashlib
import os
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

from .extensions import db
import bcrypt

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.String(8), primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    pwd_hash = db.Column(db.Text, nullable=False)
    salt = db.Column(db.Text, nullable=False)

    @staticmethod
    def find_by_name(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def find_by_id(user_id):
        return User.query.filter_by(user_id=user_id).first()

    @staticmethod
    def create(username, plain_pwd, user_id):
        # 确保密码长度在 8-12 位之间
        if len(plain_pwd) < 8 or len(plain_pwd) > 12:
            raise ValueError("Password must be between 8 and 12 characters long")

        # 生成随机盐值
        salt = os.urandom(16).hex()

        # 将密码和盐值拼接后进行哈希处理
        pwd_hash = hashlib.sha256((plain_pwd+ salt).encode()).hexdigest()

        # 创建用户
        user = User(user_id=user_id, username=username, pwd_hash=pwd_hash, salt=salt)
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def authenticate_by_username_or_id(identifier, plain_pwd):
        # 尝试根据用户名或用户 ID 查找用户
        user = User.find_by_name(identifier) or User.find_by_id(identifier)
        if not user:
            # 如果没有找到用户，返回 None
            return None, "用户不存在"

        # 将密码和 salt 拼接
        pwd = plain_pwd + user.salt

        # 进行哈希处理
        pwd_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()

        # 比较生成的哈希值和数据库中的 pwd_hash
        if pwd_hash == user.pwd_hash:
            return user, None
        else:
            # 如果哈希值不匹配，返回 None 和错误信息
            return None, "密码错误"

    @staticmethod
    def generate_user_id():
        max_user_id = db.session.query(db.func.max(User.user_id)).scalar()
        if max_user_id is None:
            return '10000001'
        return str(int(max_user_id) + 1).zfill(8)

class FriendRequest(db.Model):
    __tablename__ = 'friend'
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.String(8), db.ForeignKey('user.user_id'))
    friend_id = db.Column(db.String(8), db.ForeignKey('user.user_id'))
    status = db.Column(db.Integer, default=0)
    request_time = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(user_id, friend_id):
        request = FriendRequest(user_id=user_id, friend_id=friend_id)
        db.session.add(request)
        db.session.commit()

    @staticmethod
    def is_pending(user_id, friend_id):
        return FriendRequest.query.filter(
            or_(
                (FriendRequest.user_id == user_id) & (FriendRequest.friend_id == friend_id),
                (FriendRequest.user_id == friend_id) & (FriendRequest.friend_id == user_id)
            ),
            FriendRequest.status == 0
        ).first() is not None

    @staticmethod
    def is_friend(user_id, friend_id):
        return FriendRequest.query.filter(
            or_(
                (FriendRequest.user_id == user_id) & (FriendRequest.friend_id == friend_id),
                (FriendRequest.user_id == friend_id) & (FriendRequest.friend_id == user_id)
            ),
            FriendRequest.status == 1
        ).first() is not None

    @staticmethod
    def accept_request(user_id, friend_id):
        request = FriendRequest.query.filter(
            or_(
                (FriendRequest.user_id == user_id) & (FriendRequest.friend_id == friend_id),
                (FriendRequest.user_id == friend_id) & (FriendRequest.friend_id == user_id)
            ),
            FriendRequest.status == 0
        ).first()
        if request:
            request.status = 1
            db.session.commit()
            return True
        return False

    @staticmethod
    def reject_request(user_id, friend_id):
        request = FriendRequest.query.filter(
            or_(
                (FriendRequest.user_id == user_id) & (FriendRequest.friend_id == friend_id),
                (FriendRequest.user_id == friend_id) & (FriendRequest.friend_id == user_id)
            ),
            FriendRequest.status == 0
        ).first()
        if request:
            request.status = 2
            db.session.commit()
            return True
        return False


# 在 Room 模型中添加关系
class Room(db.Model):
    __tablename__ = 'room'
    room_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    group_flag = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(255))
    owner = db.Column(db.String(8), db.ForeignKey('user.user_id'))

    # 添加关系
    members = db.relationship('RoomMember', backref='room', lazy=True)
    messages = db.relationship('Message', backref='room_ref', lazy=True)


# 在 RoomMember 模型中添加关系
class RoomMember(db.Model):
    __tablename__ = 'room_member'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    room_id = db.Column(db.BigInteger, db.ForeignKey('room.room_id'))
    user_id = db.Column(db.String(8), db.ForeignKey('user.user_id'))
    last_read_seq = db.Column(db.BigInteger, default=0)

    # 添加关系
    user = db.relationship('User', backref='room_memberships', lazy=True)


# 在 models.py 中的 Message 类

class Message(db.Model):
    __tablename__ = 'message'
    msg_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    room_id = db.Column(db.BigInteger, db.ForeignKey('room.room_id'), default=0)
    seq = db.Column(db.BigInteger, default=0)
    type = db.Column(db.Integer, default=0)
    sender = db.Column(db.String(8), db.ForeignKey('user.user_id'))
    body = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    ts = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 添加关系
    sender_ref = db.relationship('User', backref='messages', lazy=True)

    @staticmethod
    def save(sender, body, room_id=0, type=0, status=0):
        # 获取当前房间的最后一个 seq 值
        last_seq = db.session.query(db.func.max(Message.seq)).filter_by(room_id=room_id).scalar() or 0
        seq = last_seq + 1
        msg = Message(sender=sender, body=body, room_id=room_id, seq=seq, type=type, status=status)
        db.session.add(msg)
        db.session.commit()

    @staticmethod
    def get_page(page, size):
        msgs = (Message.query.order_by(Message.msg_id.desc())
                .limit(size)
                .offset((page - 1) * size)
                .all())
        return [{'sender': m.sender,
                 'body': m.body,
                 'ts': m.ts.isoformat(),
                 'msg_id': m.msg_id} for m in msgs]

    @staticmethod
    def get_messages_for_room(room_id, page, size):
        msgs = (Message.query.filter_by(room_id=room_id)
                .order_by(Message.seq.asc())
                .limit(size)
                .offset((page - 1) * size)
                .all())
        return [{'sender': m.sender,
                 'body': m.body,
                 'ts': m.ts.isoformat(),
                 'seq': m.seq} for m in msgs]