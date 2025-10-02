FROM python:3.11-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（curl 用于 healthcheck，libmagic 用于 python-magic）
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libmagic1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再复制源码
COPY . .

# 开放端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# 使用 gunicorn 启动应用
CMD ["gunicorn", "-w", "4", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "--bind", "0.0.0.0:5000", "app.factory:app"]
