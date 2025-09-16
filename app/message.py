"""
历史消息分页 + WebSocket 收发
- Redis 统计在线人数
- 消息持久化
"""
# message.py
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit
from .models import db, Message
from .utils import init_redis
# 从extensions导入socketio
from .extensions import socketio

msg_bp = Blueprint('msg', __name__, url_prefix='')
r = init_redis()

# 移除_get_socketio函数，直接使用从extensions导入的socketio

@socketio.on('connect')
@jwt_required()
def on_connect():
    r.sadd('online', request.sid)
    emit('online', {'count': r.scard('online')}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    r.srem('online', request.sid)
    emit('online', {'count': r.scard('online')}, broadcast=True)

@socketio.on('chat')
@jwt_required()
def on_chat(json):
    user = get_jwt_identity()
    body = str(json.get('body', ''))[:2000]
    Message.save(user, body)
    emit('chat',
         {'from': user, 'body': body, 'ts': datetime.utcnow().isoformat()},
         broadcast=True)