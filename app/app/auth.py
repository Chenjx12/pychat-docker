"""
注册 / 登录 / 限流
- bcrypt 哈希
- Flask-Limiter 5次/分钟
- JWT 写入 HttpOnly Cookie
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, jwt_required, get_jwt_identity, get_jwt
from .models import  User
from .extensions import limiter, jwt
from .utils import blacklist

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET'])
@limiter.limit('5 per minute')
def login():
    return render_template('login.html')

@auth_bp.route('/reg', methods=['GET'])
@limiter.limit('5 per minute')
def reg():
    return render_template('reg.html')

@auth_bp.route('/login', methods=['POST'])
@limiter.limit('5 per minute')
def login_post():
    data = request.get_json()  # 获取 JSON 数据
    username = data.get('identifier')
    password = data.get('password')

    user, error = User.authenticate_by_username_or_id(username, password)
    if user:
        # 生成访问 Token 和刷新 Token
        now = datetime.now(ZoneInfo('Asia/Shanghai'))
        access_token = create_access_token(identity=user.user_id)
        refresh_token = create_refresh_token(identity=user.user_id)
        # 添加调试信息
        from flask_jwt_extended import decode_token
        decoded = decode_token(access_token)
        print(f"Token expires at: {decoded['exp']}")
        print(f"Current server time: {datetime.now()}")

        resp = jsonify({'code': 0, 'user_id': user.user_id, 'username': user.username})
        # set_access_cookies(resp, access_token)
        # set_refresh_cookies(resp, refresh_token)
        # 设置访问 Token Cookie（非 HTTP-only）
        resp.set_cookie(
            'access_token_cookie',
            access_token,
            max_age=3600,  # Token 有效期为 1 小时
            path='/',  # Cookie 适用于整个站点
            httponly=False,  # 这将使 Cookie 非 HTTP-only
            secure=False  # 只在 HTTPS 连接中发送 Cookie
        )

        # 设置刷新 Token Cookie（非 HTTP-only）
        resp.set_cookie(
            'refresh_token_cookie',
            refresh_token,
            max_age=604800,  # Token 有效期为 7 天
            path='/',
            httponly=False,  # 这将使 Cookie 非 HTTP-only
            secure=False
        )
        return resp
    else:
        if error == "用户不存在":
            return jsonify({'code': 1, 'msg': '用户不存在'}), 404
        elif error == "密码错误":
            return jsonify({'code': 1, 'msg': '密码错误'}), 401
        else:
            return jsonify({'code': 1, 'msg': '未知错误'}), 500

@auth_bp.route('/reg', methods=['POST'])
@limiter.limit('5 per minute')
def reg_post():
    data = request.get_json()  # 获取 JSON 数据
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not User.find_by_name(username):
        if password != confirm_password:
            return jsonify({'code': 1, 'msg': '密码和确认密码不一致'}), 400

        user_id = User.generate_user_id()
        User.create(username, password, user_id)
        return jsonify({'code': 0, 'user_id': user_id}), 201
    else:
        return jsonify({'code': 1, 'msg': '用户名已存在'}), 400

@auth_bp.route('/logout')
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    blacklist.add(jti)
    response = jsonify({'code': 0, 'msg': '您已退出登录。'})
    response.delete_cookie('access_token_cookie')
    response.delete_cookie('refresh_token_cookie')
    return response

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user)
        resp = jsonify({'code': 0, 'msg': 'Token刷新成功'})
        set_access_cookies(resp, new_token)
        return resp
    except:
        return jsonify({'code': 1, 'msg': '刷新Token失败'}), 401