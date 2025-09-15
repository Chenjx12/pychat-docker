from flask import Flask
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO  # 添加 SocketIO 导入
from .models import db
from .auth import auth_bp
from .utils import setup_logger, init_redis, logger
import os

# 在导入 message 之前创建 socketio 实例
socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    # ... 其他配置 ...

    # 初始化 socketio
    socketio.init_app(app)

    # 现在可以安全地导入 message
    from .message import msg_bp, on_connect  # 延迟导入

    # 注册蓝图和事件
    app.register_blueprint(auth_bp)
    app.register_blueprint(msg_bp)

    # 注册 socketio 事件
    on_connect()  # 注册连接事件

    return app


__all__ = ['create_app', 'db', 'auth_bp', 'msg_bp', 'socketio']  # 添加 socketio 到 __all__