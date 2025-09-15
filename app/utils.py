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

def setup_logger():
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
    return structlog.get_logger()

# 在模块级别创建 logger 实例
logger = setup_logger()  # 初始化 logger