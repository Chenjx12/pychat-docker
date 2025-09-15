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