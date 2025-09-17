from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(logger=False, engineio_logger=False, cors_allowed_origins=[], async_mode='gevent')
limiter = Limiter(key_func=get_remote_address)