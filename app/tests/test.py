# tests/test.py
import pytest
import requests
from app.app import create_app
from app.models import db  # 使用绝对导入


@pytest.fixture
def app():
    app = create_app()
    app.config.from_mapping(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        JWT_SECRET_KEY='test_jwt_secret',
        SECRET_KEY='test_secret_key',
        REDIS_URL='redis://localhost:6379/0'
    )
    with app.app_context():
        db.create_all()  # 直接使用导入的db
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def socketio_client(app):
    # 使用应用实例中的socketio扩展
    return app.extensions['socketio'].test_client(app)


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}


def test_register_user(client):
    response = client.post('/reg', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert response.json['code'] == 0


def test_login_user(client):
    # Register a user first
    client.post('/reg', json={'username': 'testuser', 'password': 'testpass'})

    response = client.post('/login', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert response.json['code'] == 0


def test_message_history(client):
    # Register and login a user
    client.post('/reg', json={'username': 'testuser', 'password': 'testpass'})
    login_response = client.post('/login', json={'username': 'testuser', 'password': 'testpass'})

    # 使用JWT token设置cookie
    access_token = login_response.json['access_token']
    client.set_cookie('localhost', 'access_token_cookie', access_token)

    # Save a message
    response = client.post('/chat', json={'body': 'Hello, world!'})
    assert response.status_code == 200

    # Get message history
    response = client.get('/history')
    assert response.status_code == 200
    assert len(response.json['data']) == 1


def test_websocket_connect(socketio_client):
    # 连接时可能需要认证，这里简化处理
    socketio_client.connect()
    assert socketio_client.is_connected()
    socketio_client.disconnect()


def test_websocket_disconnect(socketio_client):
    socketio_client.connect()
    socketio_client.disconnect()
    assert not socketio_client.is_connected()
