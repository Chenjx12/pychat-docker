# 多 worker gevent + JSON 日志 + 健康检查工具
FROM python:3.11-slim

# 安装系统依赖（curl 用于 healthcheck，libmagic 用于 python-magic）
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libmagic1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制源码
COPY . .

# 开放端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# 4 个 gevent worker，日志输出到 stdout
CMD ["gunicorn", "-k", "gevent", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile=-", "--enable-stdio-inheritance", "app:create_app()"]