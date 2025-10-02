import hashlib

import bcrypt
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import db, User
import logging
from werkzeug.utils import secure_filename
import os

center_bp = Blueprint('center', __name__, url_prefix='/center')

@center_bp.route('/')
@jwt_required()
def center():
    user = get_jwt_identity()
    return render_template('center.html', user=user)

@center_bp.post('/upload-avatar')
@jwt_required()
def upload_avatar():
    user = get_jwt_identity()
    if 'avatar' not in request.files:
        return jsonify({'code': 1, 'msg': '未上传文件'}), 400

    avatar = request.files['avatar']
    if avatar.filename == '':
        return jsonify({'code': 1, 'msg': '未选择文件'}), 400

    filename = secure_filename(avatar.filename)
    avatar.save(os.path.join('/app/upload', filename))
    return jsonify({'code': 0, 'msg': '头像上传成功'})

@center_bp.post('/update-username')
@jwt_required()
def update_username():
    user_id = get_jwt_identity()
    data = request.json
    new_username = data['newUsername']

    if not new_username:
        return jsonify({'code': 1, 'msg': '新用户名不能为空'}), 400

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'code': 1, 'msg': '用户不存在'}), 404

    user.username = new_username
    db.session.commit()
    return jsonify({'code': 0, 'msg': '用户名修改成功'})

@center_bp.post('/update-password')
@jwt_required()
def update_password():
    user_id = get_jwt_identity()
    data = request.json
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')

    if not current_password or not new_password:
        return jsonify({'code': 1, 'msg': '当前密码和新密码不能为空'}), 400

    # 根据用户名查找用户
    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'code': 1, 'msg': '用户不存在'}), 404

    # 验证当前密码
    pwd = current_password + user.salt
    pwd_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
    if pwd_hash != user.pwd_hash:
        return jsonify({'code': 1, 'msg': '当前密码错误'}), 401

    # 验证新密码长度
    if len(new_password) < 8 or len(new_password) > 12:
        return jsonify({'code': 1, 'msg': '新密码必须在 8-12 位之间'}), 400

    # 生成新的盐值
    salt = os.urandom(16).hex()

    # 将新密码和新盐值拼接后进行哈希处理
    new_pwd_hash = hashlib.sha256((new_password + salt).encode()).hexdigest()

    # 更新用户密码和盐值
    user.pwd_hash = new_pwd_hash
    user.salt = salt
    db.session.commit()

    return jsonify({'code': 0, 'msg': '密码修改成功'})