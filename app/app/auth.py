from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from .models import db, User
import logging
from .extensions import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='')

@auth_bp.post('/reg')
@limiter.limit('5 per minute')
def reg():
    username = request.form['username']
    password = request.form['password']
    if User.find_by_name(username):
        return {'code': 1, 'msg': '用户名已存在'}, 409
    User.create(username, password)
    logging.info('user_registered'+f'username={username}')
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
    logging.info('user_login' + f'username={username}')
    return resp
