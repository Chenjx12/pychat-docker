# app/router.py
from flask import render_template

def register_routes(app):
    # 主页
    @app.route('/')
    def index():
        return render_template('index.html')

    # 认证
    @app.route('/auth')
    def auth():
        return render_template('auth.html')

    # 聊天室
    @app.route('/chat')
    def chat():
        return render_template('chat.html')

    # 个人中心
    @app.route('/center')
    def center():
        return render_template('center.html')

    # 联系页面
    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    # 健康检查
    @app.get('/health')
    def health():
        return {'status': 'ok'}
