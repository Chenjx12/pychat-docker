# Py chat

仅个人写项目图便捷使用



## 文件结构

```
pychat-docker/
.
├── app
│   ├── Dockerfile
│   ├── app
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── center.py
│   │   ├── extensions.py
│   │   ├── factory.py
│   │   ├── friends.py
│   │   ├── message.py
│   │   ├── models.py
│   │   ├── room.py
│   │   ├── router.py
│   │   ├── static
│   │   │   ├── css
│   │   │   │   ├── center_styles.css
│   │   │   │   ├── chat_styles.css
│   │   │   │   ├── contact_styles.css
│   │   │   │   ├── index_styles.css
│   │   │   │   ├── login_styles.css
│   │   │   │   └── reg_styles.css
│   │   │   └── js
│   │   │       ├── chat.js
│   │   │       ├── contact.js
│   │   │       ├── friend.js
│   │   │       ├── jquery-3.6.0.min.js
│   │   │       ├── login.js
│   │   │       ├── profile.js
│   │   │       ├── reg.js
│   │   │       └── utils.js
│   │   ├── templates
│   │   │   ├── 1.html
│   │   │   ├── center.html
│   │   │   ├── chat.html
│   │   │   ├── contact.html
│   │   │   ├── index.html
│   │   │   ├── login.html
│   │   │   └── reg.html
│   │   ├── upload.py
│   │   └── utils.py
│   ├── requirements.txt
│   └── tests
├── docker-compose.yml
├── nginx
│   └── default.conf
├── sql
│   └── init.sql
└── ssl
    ├── cert.pem
    ├── key.pem
    └── public.pem
```



## docker-compose

```yaml

services:
  db:
    image: mysql:8.0
    container_name: pychat-db
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    env_file: .env
    volumes:
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
      - db_data:/var/lib/mysql
    networks:
      - pychat-net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: pychat-redis
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
    networks:
      - pychat-net

  app:
    build: ./app
    container_name: pychat-app
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    env_file: .env
    depends_on:
      - db
      - redis
    networks:
      - pychat-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: pychat-nginx
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "10000:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - app_upload:/app/upload:ro
    depends_on:
      - app
    networks:
      - pychat-net

volumes:
  db_data:
  app_upload:

networks:
  pychat-net:
```
