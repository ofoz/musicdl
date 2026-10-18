FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 替换为国内 Debian 镜像源（兼容 debian.sources 与 sources.list 格式）加速 apt 下载
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
        sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi

# 安装系统运行依赖 (ffmpeg 保证音频处理与元数据支持，curl 用于容器健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 国内镜像源加速
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 先复制依赖描述并安装，利用 Docker 缓存层
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源代码
COPY . .

# 快速以开发/可编辑模式安装当前模块
RUN pip install --no-cache-dir -e .

# 创建并声明下载持久化挂载目录
RUN mkdir -p /app/downloads
VOLUME ["/app/downloads"]

# 暴露 WebUI 服务端口
EXPOSE 5050

# 容器健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5050/ || exit 1

# 启动 WebUI 默认监听全网卡 0.0.0.0:5050
CMD ["python", "-m", "musicdl.web", "--host", "0.0.0.0", "--port", "5050", "--work-dir", "/app/downloads", "--no-browser"]
