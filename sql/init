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