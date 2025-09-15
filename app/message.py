# app/message.py
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import SocketIO, emit
from .models import db, Message
from .utils import init_redis
from . import socketio  # 从 app 包导入 socketio

msg_bp = Blueprint('msg', __name__, url_prefix='')
r = init_redis()

@msg_bp.get('/history')
@jwt_required()
def history():
    page = int(request.args.get('page', 1))
    size = 50
    data = Message.get_page(page, size)
    return {'data': data, 'has_more': len(data) == size}

# WebSocket 事件
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