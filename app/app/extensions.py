from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .utils import blacklist

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")
limiter = Limiter(key_func=get_remote_address)

# JWT回调函数
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in blacklist

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"code": 1, "msg": "Token已过期"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"code": 1, "msg": "无效的Token"}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"code": 1, "msg": "请先登录"}), 401