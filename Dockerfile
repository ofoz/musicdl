FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 配置 pip 国内镜像源加速（阿里云镜像源，秒速下载依赖）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 先复制依赖清单并安装，利用 Docker 镜像分层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源代码
COPY . .

# 快速以可编辑模式安装当前模块
RUN pip install --no-cache-dir -e .

# 创建并声明下载持久化挂载目录
RUN mkdir -p /app/downloads
VOLUME ["/app/downloads"]

# 暴露 WebUI 服务端口
EXPOSE 5050

# 容器健康检查（使用 Python 原生 urllib 标准库，零系统外部命令依赖）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/')" || exit 1

# 启动 WebUI 默认监听全网卡 0.0.0.0:5050
CMD ["python", "-m", "musicdl.web", "--host", "0.0.0.0", "--port", "5050", "--work-dir", "/app/downloads", "--no-browser"]
