# 使用官方 Python 运行时作为父镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 将依赖文件复制到工作目录
# 首先复制 requirements.txt 并安装，以便利用 Docker 的层缓存机制
COPY requirements.txt requirements.txt

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将项目代码复制到工作目录
COPY ./api /app/api
# 如果您有一个 main.py 在根目录启动应用，请包含它
# 如果您的启动脚本在 api 目录内，例如 api/chat_api.py，则上一行可能不需要

# 应用程序监听的端口
EXPOSE 8899

# 定义环境变量的预期，实际值应在运行时提供
# ENV SECURE_1PSID="your_secure_1psid_value_here"
# ENV SECURE_1PSIDTS="your_secure_1psidts_value_here"
# 更好的做法是在 docker run 命令中通过 -e 参数提供这些敏感值，而不是在 Dockerfile 中硬编码占位符

# 运行 uvicorn 服务器的命令
# 确保这里的路径 `api.chat_api:app` 是正确的，指向 FastAPI app 实例
CMD ["uvicorn", "api.chat_api:app", "--host", "0.0.0.0", "--port", "8899"]
