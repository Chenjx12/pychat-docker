# __init__.py
import os
from datetime import timedelta

from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text

from .center import center_bp
from .extensions import db, jwt, socketio, limiter
from .auth import auth_bp
from .message import msg_bp
from .friends import friends_bp
from .room import room_bp
from .router import register_routes
from .utils import setup_logger

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_TOKEN_LOCATION=['cookies'],
        JWT_COOKIE_CSRF_PROTECT=False,
        JWT_COOKIE_SECURE=False,  # 本地 http 先 False
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=24),  # 访问 Token 有效期为 24 小时
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),  # 刷新 Token 有效期为 30 天
        JWT_DATETIME_ZONE = "Asia/Shanghai",
        SQLALCHEMY_DATABASE_URI=(
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
            f"@db:3306/{os.getenv('MYSQL_DATABASE')}?charset=utf8mb4"
        ),
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_size': 20,
            'max_overflow': 40,
            'pool_pre_ping': True
        },
        REDIS_URL=os.getenv('REDIS_URL', 'redis://redis:6379/0')
    )

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    limiter = Limiter(app)  # 创建 Limiter 实例
    limiter.limit("5 per minute")  # 设置速率限制

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(msg_bp)
    app.register_blueprint(center_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(room_bp)

    # 注册路由
    register_routes(app)

    # 日志 JSON 化
    setup_logger(app)

    @app.before_request
    def before_request():
        app.logger.info(f"Request: {request.method} {request.path} - {request.remote_addr}")

    @app.after_request
    def after_request(response):
        app.logger.info(f"Response: {request.method} {request.path} - {response.status_code}")
        return response

    # 添加全局错误处理
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'code': 1, 'msg': '请先登录'}), 401

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({'code': 1, 'msg': 'Token无效或已过期'}), 422

    return app
