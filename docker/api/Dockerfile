FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /data/backups && chmod 755 /data/backups
RUN mkdir -p /app/logs && chmod 755 /app/logs
RUN mkdir -p /app/dict && chmod 755 /app/dict

# 确保字典文件存在并有正确权限
RUN if [ ! -f /app/dict/usernames.txt ]; then \
    echo "# 默认用户名字典" > /app/dict/usernames.txt && \
    echo "admin\nroot\nuser\nproxy\nguest\ntest" >> /app/dict/usernames.txt; \
    fi && \
    if [ ! -f /app/dict/passwords.txt ]; then \
    echo "# 默认密码字典" > /app/dict/passwords.txt && \
    echo "admin\npassword\n123456\nroot\nadmin123\nproxy\n12345678" >> /app/dict/passwords.txt; \
    fi && \
    chmod 644 /app/dict/*.txt

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5000

# 设置容器启动命令
CMD ["python", "main.py", "--mode", "api"] 