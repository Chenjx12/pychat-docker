USE pychat;
-- 创建 user 表
CREATE TABLE user (
    user_id VARCHAR(8) PRIMARY KEY,
    username VARCHAR(30) UNIQUE NOT NULL,
    pwd_hash TEXT NOT NULL,
    salt TEXT NOT NULL
);

-- 插入初始测试用户
INSERT INTO user (user_id, username, pwd_hash, salt) VALUES ('9999999', 'qwer', 'e6b773bdfbec009214c8004e029b3cd74a5286bad3e3a163ecb6251123cbb8e1', 'salt_value');
INSERT INTO user (user_id, username, pwd_hash, salt) VALUES ('10000000', 'test', '500b7c6bbe61e5fbdb3a28b4f2ee535f4f61c6ebeaed5787a1c0a1453b3486d7', 'salt_value');

-- 创建 room 表
CREATE TABLE room (
    room_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    group_flag BOOLEAN,
    name VARCHAR(255),
    owner VARCHAR(30),
    FOREIGN KEY (owner) REFERENCES user(user_id)
);
INSERT INTO room (room_id, group_flag, name, owner) VALUE (1, TRUE, '默认群聊', '10000000');

-- 创建 message 表
CREATE TABLE message (
    msg_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT,
    seq BIGINT,
    type INT,
    sender VARCHAR(8),
    body TEXT,
    status INT,
    ts DATETIME,
    FOREIGN KEY (room_id) REFERENCES room(room_id),
    FOREIGN KEY (sender) REFERENCES user(user_id)
);

-- 创建 room_member 表
CREATE TABLE room_member (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT,
    user_id VARCHAR(30),
    last_read_seq BIGINT,
    FOREIGN KEY (room_id) REFERENCES room(room_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

INSERT INTO room_member (room_id, user_id, last_read_seq) VALUE (1, '10000000', 0);
INSERT INTO room_member (room_id, user_id, last_read_seq) VALUE (1, '9999999', 0);

-- 创建 好友申请处理表
CREATE TABLE friend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(8),
    friend_id VARCHAR(8),
    status INT, -- 0: 待处理，1: 已接受，2: 已拒绝
    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (friend_id) REFERENCES user(user_id)
);
