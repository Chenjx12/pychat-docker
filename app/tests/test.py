import pytest
import requests
from app import create_app


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
        from .models import db
        db.create_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def socketio_client(app):
    from flask_socketio import SocketIO
    socketio = SocketIO(app)
    return socketio.test_client(app)


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}


def test_register_user(client):
    response = client.post('/reg', data={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert response.json['code'] == 0


def test_login_user(client):
    # Register a user first
    client.post('/reg', data={'username': 'testuser', 'password': 'testpass'})

    response = client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert response.json['code'] == 0


def test_message_history(client):
    # Register and login a user
    client.post('/reg', data={'username': 'testuser', 'password': 'testpass'})
    login_response = client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    token = login_response.json['access_token']

    # Save a message
    headers = {'Authorization': f'Bearer {token}'}
    client.post('/chat', json={'body': 'Hello, world!'}, headers=headers)

    response = client.get('/history')
    assert response.status_code == 200
    assert len(response.json['data']) == 1


def test_websocket_connect(socketio_client):
    socketio_client.connect()
    assert socketio_client.is_connected()


def test_websocket_disconnect(socketio_client):
    socketio_client.connect()
    socketio_client.disconnect()
    assert not socketio_client.is_connected()


def test_websocket_chat(socketio_client):
    socketio_client.connect()
    socketio_client.emit('chat', {'body': 'Hello, world!'})
    received = socketio_client.get_received()
    assert len(received) == 1
    assert received[0]['name'] == 'chat'