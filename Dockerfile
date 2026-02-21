# Dockerfile for PSTDS - Phase 6 Task 7 (P6-T7)

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY pstds/ ./pstds/
COPY web/ ./web/
COPY config/ ./config/

# 创建数据目录
RUN mkdir -p /app/data/cache /app/data/db /app/data/logs /app/data/reports /app/data/vector_memory

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK CMD curl -f http://localhost:8501/healthz || exit 1

# 启动命令
CMD ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]
