# app/__init__.py
from flask import Flask
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .models import db
from .auth import auth_bp
from .message import msg_bp
from .utils import setup_logger, init_redis, logger

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_TOKEN_LOCATION=['cookies'],
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=False,
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
    setup_logger(app)
    db.init_app(app)
    jwt = JWTManager(app)
    limiter = Limiter(key_func=get_remote_address, app=app)
    socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(msg_bp)

    # 健康检查
    @app.route('/health')
    def health():
        db.session.execute('SELECT 1')
        init_redis().ping()
        return {'status': 'ok'}

    return app

# 导出 socketio 实例供其他模块使用
socketio = SocketIO(async_mode='gevent')