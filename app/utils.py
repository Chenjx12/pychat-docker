"""
公共工具：Redis、日志、蓝图常用
"""
import json
import logging
import structlog
import redis
from flask import Flask
import os

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

    # 创建一个 logger 实例
    logger = structlog.get_logger()
    return logger

# 在模块级别创建 logger 实例
logger = setup_logger(None)  # 初始化 logger，传入 None 作为示例，实际使用时传入 Flask app 实例