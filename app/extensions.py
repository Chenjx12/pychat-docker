# extensions.py
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

socketio = SocketIO(logger=False, engineio_logger=False,
                    cors_allowed_origins=[], async_mode='gevent')
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)