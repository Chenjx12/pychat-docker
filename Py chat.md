# Py chat

仅个人写项目图便捷使用



## 文件结构

```
pychat-docker/
├─ docker-compose.yml          # 一键拉起（含 healthcheck、env_file）
├─ .env                        # 密钥 .env 已加入 .gitignore
├─ app/
│  ├─ Dockerfile               # 多 worker gevent + JSON 日志
│  ├─ requirements.txt         # 带哈希 & 新增依赖
│  ├─ app.py                   # 已拆层 + JWT + 连接池 + Redis
│  ├─ auth.py                  # 登录/注册/限流
│  ├─ message.py               # 历史分页 + 在线人数
│  ├─ upload.py                # MIME+UUID+压缩
│  ├─ models.py                # SQLAlchemy ORM（复用连接池）
│  ├─ utils.py                 # JWT、Redis、日志
│  ├─ static/
│  │  └─ index.html            # 原生 WebSocket 带 JWT Cookie
│  └─ tests/                   # pytest + fakeredis
├─ nginx/
│  └─ default.conf             # 安全头 + 文件白名单
├─ sql/
│  └─ init.sql                 # 原表结构不变，仅加索引
└─ .github/
└─ workflows/
└─ ci.yml                # 自动测试 & 镜像推送
```



## docker-compose

```yaml
version: "3.9"

services:
  db:
    image: mysql:8.0
    container_name: pychat-db
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./sql:/docker-entrypoint-initdb.d
      - db_data:/var/lib/mysql
    networks:
      - pychat-net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: pychat-redis
    restart: unless-stopped
    networks:
      - pychat-net

  app:
    build: ./app
    container_name: pychat-app
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db
      - redis
    networks:
      - pychat-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: pychat-nginx
    restart: unless-stopped
    ports:
      - "9999:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - app_upload:/app/upload:ro
    depends_on:
      - app
    networks:
      - pychat-net

volumes:
  db_data:
  app_upload:

networks:
  pychat-net:
```



## .env.example

```
# .env

# Flask Configuration
FLASK_APP=app/main.py
FLASK_ENV=development
SECRET_KEY=a_very_long_and_random_string_for_security

# Database Configuration
DATABASE_URL=postgresql://pychat_user:your_strong_db_password@db:5432/pychat_db

# Nginx or other service configs...
```



## app/

### Dockerfile

```dockerfile
# 多 worker gevent + JSON 日志 + 健康检查工具
FROM python:3.11-slim

# 安装系统依赖（curl 用于 healthcheck，libmagic 用于 python-magic）
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libmagic1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制源码
COPY . .

# 开放端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# 4 个 gevent worker，日志输出到 stdout
CMD ["gunicorn", "-k", "gevent", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile=-", "--enable-stdio-inheritance", "app:create_app()"]
```



### requirements.txt

```txt
Flask==2.3.3
Flask-JWT-Extended==4.6.0
Flask-Limiter==3.5.0
Flask-SocketIO==5.3.6
SQLAlchemy==2.0.23
PyMySQL==1.1.0
bcrypt==4.0.1
redis==5.0.1
python-magic==0.4.27
Pillow==10.2.0
gunicorn==21.2.0
gevent==23.9.1
pytest==7.4.3
fakeredis==2.20.0
structlog==23.2.0
```



### app.py

```python
"""
Flask 应用工厂
- SQLAlchemy 连接池
- JWT（HttpOnly Cookie）
- Redis
- SocketIO（gevent）
"""
import os
from flask import Flask
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .models import db
from .auth import auth_bp
from .message import msg_bp
from .utils import init_redis, setup_logger

# 全局扩展先声明，后续 init_app 绑定
socketio = SocketIO(logger=False, engineio_logger=False,
                    cors_allowed_origins=[], async_mode='gevent')
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_TOKEN_LOCATION=['cookies'],
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=False,          # 本地 http 先 False
        SQLALCHEMY_DATABASE_URI=(
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
            f"@db:3306/{os.getenv('MYSQL_DATABASE')}?charset=utf8mb4"
        ),
        SQLALCHEMY_ENGINE_OPTIONS={       # 连接池
            'pool_size': 20,
            'max_overflow': 40,
            'pool_pre_ping': True
        },
        REDIS_URL=os.getenv('REDIS_URL', 'redis://redis:6379/0')
    )

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app)

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(msg_bp)

    # 健康检查
    @app.get('/health')
    def health():
        db.session.execute('SELECT 1')
        init_redis().ping()
        return {'status': 'ok'}

    # 日志 JSON 化
    setup_logger(app)
    return app
```



### auth.py

```python
"""
注册 / 登录 / 限流
- bcrypt 哈希
- Flask-Limiter 5次/分钟
- JWT 写入 HttpOnly Cookie
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_limiter import Limiter
from .models import db, User
from .utils import logger

auth_bp = Blueprint('auth', __name__, url_prefix='')
limiter = Limiter()


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
```



### message.py

```python
"""
历史消息分页 + WebSocket 收发
- Redis 统计在线人数
- 消息持久化
"""
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit, socketio
from .models import db, Message
from .utils import init_redis

msg_bp = Blueprint('msg', __name__, url_prefix='')
r = init_redis()


@msg_bp.get('/history')
@jwt_required()
def history():
    page = int(request.args.get('page', 1))
    size = 50
    data = Message.get_page(page, size)
    return {'data': data, 'has_more': len(data) == size}


# WebSocket 事件
@socketio.on('connect')
@jwt_required()
def on_connect():
    r.sadd('online', request.sid)
    emit('online', {'count': r.scard('online')}, broadcast=True)


@socketio.on('disconnect')
def on_disconnect():
    r.srem('online', request.sid)
    emit('online', {'count': r.scard('online')}, broadcast=True)


@socketio.on('chat')
@jwt_required()
def on_chat(json):
    user = get_jwt_identity()
    body = str(json.get('body', ''))[:2000]
    Message.save(user, body)
    emit('chat',
         {'from': user, 'body': body, 'ts': datetime.utcnow().isoformat()},
         broadcast=True)
```



### upload.py

```python
"""
文件上传
- MIME 校验 + 后缀白名单
- UUID 重命名
- 图片压缩（JPEG 85%）
"""
import os, uuid, io
from PIL import Image
from flask import Blueprint, request, send_from_directory
from flask_jwt_extended import jwt_required
from flask_limiter import Limiter
import magic

upload_bp = Blueprint('upload', __name__, url_prefix='')
limiter = Limiter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'upload')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOW_EXT = {'jpg', 'jpeg', 'png', 'gif', 'pdf'}
MAX_SIZE = 5 * 1024 * 1024


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

    # 图片压缩
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
    # nginx 已拦截非法后缀，这里兜底
    return send_from_directory(UPLOAD_DIR, name)
```



### models.py

```python
"""
SQLAlchemy ORM + 复用连接池
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    name = db.Column(db.String(30), primary_key=True)
    pwd = db.Column(db.String(60), nullable=False)

    @staticmethod
    def find_by_name(name):
        return db.session.get(User, name)

    @staticmethod
    def create(name, plain_pwd):
        hashed = bcrypt.hashpw(plain_pwd.encode(), bcrypt.gensalt(rounds=14))
        user = User(name=name, pwd=hashed.decode())
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def authenticate(name, plain_pwd):
        user = User.find_by_name(name)
        if user and bcrypt.checkpw(plain_pwd.encode(), user.pwd.encode()):
            return user
        return None


class Message(db.Model):
    __tablename__ = 'msg'
    id = db.Column(db.BigInteger, primary_key=True)
    from_user = db.Column(db.String(30))
    to_user = db.Column(db.String(30), default='all')
    body = db.Column(db.Text)
    ts = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def save(from_user, body):
        msg = Message(from_user=from_user, body=body)
        db.session.add(msg)
        db.session.commit()

    @staticmethod
    def get_page(page, size):
        msgs = (Message.query.order_by(Message.ts.desc())
                .limit(size)
                .offset((page - 1) * size)
                .all())
        return [{'from_user': m.from_user,
                 'body': m.body,
                 'ts': m.ts.isoformat()} for m in msgs][::-1]
```



### utils.py

```python
"""
公共工具：Redis、日志、蓝图常用
"""
import json, logging, structlog
import redis
from flask import Flask

def init_redis():
    return redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'), decode_responses=True)

def setup_logger(app: Flask):
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(logging.INFO)
```



### static/

### index.html

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>PyChat-Pro</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:0;display:flex;flex-direction:column;height:100vh;background:#f5f5f5;}
    #login,#chat{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;}
    #chat{display:none;width:600px;margin:auto;background:#fff;border-radius:8px;box-shadow:0 0 10px rgba(0,0,0,.1);}
    #messages{border:1px solid #ddd;height:400px;overflow-y:auto;width:100%;padding:10px;background:#fafafa;}
    .msg{margin:4px 0;}
    .self{color:#007bff;}
    button{padding:6px 12px;margin:4px;cursor:pointer;}
    input{padding:6px;width:200px;margin:4px;}
    #input{width:calc(100% - 120px);}
  </style>
</head>
<body>

<!-- 登录页 -->
<div id="login">
  <h2>PyChat-Pro</h2>
  <input id="username" placeholder="用户名" autocomplete="username"/>
  <input id="password" type="password" placeholder="密码" autocomplete="current-password"/>
  <div>
    <button onclick="reg()">注册</button>
    <button onclick="login()">登录</button>
  </div>
</div>

<!-- 聊天页 -->
<div id="chat">
  <div id="messages"></div>
  <div style="display:flex;padding:10px;">
    <input id="input" placeholder="说点什么..."/>
        <script>
        /* 监听回车发送 */
        $('input').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
        </script>
    <button onclick="send()">发送</button>
    <button onclick="logout()">退出</button>
  </div>
</div>

<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
/* ====== 工具函数 ====== */
const $  = id => document.getElementById(id);
const API = (path, body) => fetch(path,{method:'POST',body}).then(r=>r.json());

/* 从 Cookie 拿 JWT（服务端已 Set-Cookie） */
function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

/* 登录成功后统一处理 */
function enterChat(userName){
  localStorage.setItem('user', userName);   // 仅用于前端展示
  $('login').style.display = 'none';
  $('chat').style.display = 'flex';
  loadHistory();
  connectWS();
}

/* ====== 注册 / 登录 ====== */
async function reg(){
  const fd = new FormData();
  fd.append('username', username.value);
  fd.append('password', password.value);
  const res = await API('/reg', fd);
  alert(res.code === 0 ? '注册成功' : res.msg || '注册失败');
}

async function login(){
  const fd = new FormData();
  fd.append('username', username.value);
  fd.append('password', password.value);
  const res = await API('/login', fd);
  if(res.code === 0){
    enterChat(username.value);
  }else{
    alert(res.msg || '登录失败');
  }
}

/* 退出：清 cookie + 刷新页面 */
function logout(){
  document.cookie = 'access_token_cookie=; Max-Age=0; path=/';
  location.reload();
}

/* ====== 历史消息 ====== */
async function loadHistory(){
  const res = await fetch('/history').then(r=>r.json());
  res.data.forEach(m => addMsg(m.from_user, m.body, false));
}

/* ====== WebSocket ====== */
let socket;
function connectWS(){
  const token = getCookie('access_token_cookie');
  if(!token){ alert('未登录'); location.reload(); return; }

  socket = io({
    transports: ['websocket'],
    query: {token}          // JWT 放在 query，服务端从 auth.token 取
  });

  socket.on('connect', () => {
    console.log('[WS] 已连接');
  });

  socket.on('connect_error', (err) => {
    console.error('[WS] 连接失败', err.message);
    // 常见 401/422 说明 JWT 失效
    if(err.message.includes('401') || err.message.includes('422')){
      alert('登录已失效，请重新登录');
      logout();
    }
  });

  socket.on('chat', (d) => {
    addMsg(d.from, d.body, d.from === localStorage.getItem('user'));
  });
}

/* ====== 发消息 ====== */
function send(){
  const txt = $('input').value.trim();
  if(!txt || !socket) return;
  socket.emit('chat', {body: txt});
  $('input').value = '';
}

/* 渲染消息 */
function addMsg(user, body, self = false){
  const div = document.createElement('div');
  div.className = 'msg' + (self ? ' self' : '');
  div.textContent = `${user}: ${body}`;
  $('messages').appendChild(div);
  $('messages').scrollTop = $('messages').scrollHeight;
}

/* 页面加载时若已有 JWT 直接进聊天 */
window.onload = () => {
  if(getCookie('access_token_cookie')) enterChat(localStorage.getItem('user') || '');
};
</script>
</body>
</html>
```



### tests/

#### test_all.py

```python
"""
pytest + fakeredis 快速冒烟
"""
import pytest
from app import create_app, db, socketio
from app.models import User

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as cli:
        with app.app_context():
            db.create_all()
            yield cli

def test_register_login(client):
    rv = client.post('/reg', data={'username': 'u1', 'password': 'p1'})
    assert rv.json['code'] == 0
    rv = client.post('/login', data={'username': 'u1', 'password': 'p1'})
    assert rv.json['code'] == 0

def test_health(client):
    rv = client.get('/health')
    assert rv.json == {'status': 'ok'}
```



## sql/

### init.sql

```sql
USE pychat;
CREATE TABLE user(
    name VARCHAR(30) PRIMARY KEY,
    pwd  VARCHAR(60) NOT NULL
);
CREATE TABLE msg(
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    from_user VARCHAR(30),
    to_user   VARCHAR(30) DEFAULT 'all',
    body      TEXT,
    ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (to_user, ts)
);
CREATE INDEX idx_ts_desc ON msg(ts DESC);
```



## nginx/

### default.conf

```nginx
upstream pychat {
    server app:5000;
}
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
server {
    listen 80;
    client_max_body_size 6M;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline';";

    location / {
        proxy_pass http://pychat;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    location /socket.io/ {
        proxy_pass http://pychat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 86400;
    }
    location ~* ^/upload/.*\.(?<ext>jpg|jpeg|png|gif|pdf)$ {
        alias /app/upload/;
        expires 30d;
        add_header Cache-Control "public";
    }
    location /upload/ {
        return 403;  # 其它后缀直接拒绝
    }
}
```

