import pytest
from app import create_app, db
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    # 创建应用并使用测试配置
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
        'JWT_COOKIE_CSRF_PROTECT': False,  # 测试中禁用 CSRF
        'REDIS_URL': 'redis://localhost:6379/0'
    })

    # 初始化数据库
    with app.app_context():
        db.create_all()

    # 模拟 Redis 连接
    with patch('app.utils.init_redis') as mock_redis:
        mock_redis.return_value = MagicMock()

        # 创建测试客户端
        with app.test_client() as client:
            yield client

    # 清理数据库
    with app.app_context():
        db.drop_all()

def test_register_login(client):
    # 测试注册 - 注意路由可能需要调整
    rv = client.post('/reg', json={
        'username': 'u1',
        'password': 'p1'
    })
    assert rv.status_code == 200
    assert 'code' in rv.json

    # 测试登录
    rv = client.post('/login', json={
        'username': 'u1',
        'password': 'p1'
    })
    assert rv.status_code == 200
    assert 'code' in rv.json
    assert rv.json['code'] == 0

def test_health(client):
    # 模拟数据库和 Redis 检查
    with patch('app.models.db.session.execute') as mock_db:
        with patch('app.utils.init_redis') as mock_redis:
            mock_db.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.ping.return_value = True

            rv = client.get('/health')
            assert rv.status_code == 200
            assert rv.json == {'status': 'ok'}