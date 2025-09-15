"""
注册 / 登录 / 限流
- bcrypt 哈希
- Flask-Limiter 5次/分钟
- JWT 写入 HttpOnly Cookie
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address  # 导入 get_remote_address
from .models import db, User
from .utils import logger

auth_bp = Blueprint('auth', __name__, url_prefix='')
limiter = Limiter(key_func=get_remote_address)  # 使用 get_remote_address 作为 key_func

@auth_bp.post('/reg')
@limiter.limit('5 per minute')
def reg():
    username = request.form['username']
    password = request.form['password']
    if User.find_by_name(username):
        return {'code': 1, 'msg': '用户名已存在'}, 409
    User.create(username, password)
    logger.info('user_registered', username=username)
    return {'code': 0}

@auth_bp.post('/login')
@limiter.limit('5 per minute')
def login():
    username = request.form['username']
    user = User.authenticate(username, request.form['password'])
    if not user:
        return {'code': 1, 'msg': '密码错误'}, 401
    token = create_access_token(identity=username)
    resp = jsonify({'code': 0})
    set_access_cookies(resp, token)
    logger.info('user_login', username=username)
    return resp