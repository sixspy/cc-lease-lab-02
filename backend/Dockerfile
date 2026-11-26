FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    端口=8600 数据目录=/data 夹具目录=/fixtures \
    会话密钥=lease-lab-session-dev-key-8600
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY app ./app
COPY tests ./tests
EXPOSE 8600
CMD ["python", "-m", "app.main"]