import json, logging, structlog
import os
import redis
from flask import Flask

# 定义全局 logger
logger = structlog.get_logger()

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