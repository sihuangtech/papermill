#!/bin/bash

# 设置错误即停止
set -e

echo "--- 正在构建前端 ---"
cd frontend
npm install
npm run build

echo "--- 正在准备静态文件 ---"
cd ..
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

echo "--- 启动 FastAPI 后端服务 ---"
# 确保安装了所有依赖
pip install -r requirements.txt

# 启动服务
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
