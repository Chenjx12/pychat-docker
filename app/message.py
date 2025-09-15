from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import SocketIO, emit  # 移除这里的 socketio 导入
from .models import db, Message
from .utils import init_redis

msg_bp = Blueprint('msg', __name__, url_prefix='')
r = init_redis()

# 延迟导入 socketio，避免循环导入
def get_socketio():
    from . import socketio  # 在函数内部导入
    return socketio

@msg_bp.get('/history')
@jwt_required()
def history():
    page = int(request.args.get('page', 1))
    size = 50
    data = Message.get_page(page, size)
    return {'data': data, 'has_more': len(data) == size}

# WebSocket 事件 - 修改为使用获取函数
def on_connect():
    socketio = get_socketio()
    @socketio.on('connect')
    @jwt_required()
    def handle_connect():
        r.sadd('online', request.sid)
        emit('online', {'count': r.scard('online')}, broadcast=True)

# 对其他事件处理函数做类似修改...