FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV TG_ENV=production
ENV TG_AUTH_DISABLED=true

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY tg_suite/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY tg_suite/ /app/

EXPOSE 8000

CMD ["sh", "-c", "python3 -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
