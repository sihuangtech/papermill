# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 安装 Node.js 用于构建前端
RUN apt-get update && apt-get install -y \
    curl \
    git \
    texlive-full \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制项目文件
COPY . .

# 构建前端
RUN cd frontend && npm install && npm run build
RUN mkdir -p backend/static && cp -r frontend/dist/* backend/static/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动脚本
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
