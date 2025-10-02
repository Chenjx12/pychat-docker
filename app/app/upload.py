"""
文件上传
- MIME 校验 + 后缀白名单
- UUID 重命名
- 图片压缩（JPEG 85%）
"""
import os
import uuid
import io
from PIL import Image
from flask import Blueprint, request, send_from_directory
from flask_jwt_extended import jwt_required
from flask_limiter import Limiter
import magic
from flask_limiter.util import get_remote_address

upload_bp = Blueprint('upload', __name__, url_prefix='')
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'upload')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOW_EXT = {'jpg', 'jpeg', 'png', 'gif', 'pdf'}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

@upload_bp.post('/upload')
@jwt_required()
@limiter.limit('30 per minute')
def upload():
    f = request.files['file']
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOW_EXT:
        return {'code': 1, 'msg': '非法后缀'}, 415

    blob = f.read()
    if len(blob) > MAX_SIZE:
        return {'code': 1, 'msg': '文件过大'}, 413

    mime = magic.from_buffer(blob, mime=True)
    if mime not in ('image/jpeg', 'image/png', 'image/gif', 'application/pdf'):
        return {'code': 1, 'msg': 'MIME 不符'}, 415

    if mime.startswith('image'):
        img = Image.open(io.BytesIO(blob))
        img = img.convert('RGB')
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=85, optimize=True)
        blob = out.getvalue()
        ext = 'jpg'

    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, 'wb') as fp:
        fp.write(blob)
    return {'code': 0, 'url': f'/upload/{filename}'}

@upload_bp.get('/upload/<path:name>')
def uploaded_file(name):
    return send_from_directory(UPLOAD_DIR, name)
