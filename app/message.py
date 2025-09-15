# app/message.py
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit
from .models import db, Message
from .utils import init_redis

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
def on_connect():
    from .app import socketio  # 导入 socketio 实例
    r.sadd('online', request.sid)
    socketio.emit('online', {'count': r.scard('online')}, broadcast=True)

def on_disconnect():
    from .app import socketio  # 导入 socketio 实例
    r.srem('online', request.sid)
    socketio.emit('online', {'count': r.scard('online')}, broadcast=True)

def on_chat(json):
    from .app import socketio  # 导入 socketio 实例
    user = get_jwt_identity()
    body = str(json.get('body', ''))[:2000]
    Message.save(user, body)
    socketio.emit('chat',
         {'from': user, 'body': body, 'ts': datetime.utcnow().isoformat()},
         broadcast=True)

# 注册事件处理函数
socketio.on_event(on_connect)
socketio.on_event(on_disconnect)
socketio.on_event(on_chat)