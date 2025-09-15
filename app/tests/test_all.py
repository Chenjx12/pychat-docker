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