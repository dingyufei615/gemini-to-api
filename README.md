# Gemini OpenAI 兼容 API

本项目提供了一个与 OpenAI API 兼容的接口，其后端通过 `gemini-webapi`库与 Google Gemini 模型进行交互，模拟Gemini网页端进行聊天交互。

## 功能

-   模拟 OpenAI 的 `/v1/chat/completions` 端点。
-   支持流式和非流式响应。
-   通过环境变量配置 Gemini 的认证凭据。

## 先决条件

-   Python 3.8+
-   Docker (推荐用于部署)
-   有效的 `Secure_1PSID` 和 `Secure_1PSIDTS` Cookie 值用于访问 Gemini，建议您拥有Advance账号最好。

## 环境变量

在运行此应用之前，您需要设置以下环境变量：

-   `SECURE_1PSID`: 您的 Gemini网页端 `__Secure-1PSID` Cookie 值。
-   `SECURE_1PSIDTS`: 您的 Gemini网页端 `__Secure-1PSIDTS` Cookie 值。
-   `GEMINI_PROXY` (可选): 用于访问 Gemini API 的代理服务器地址，例如 `http://localhost:7890` 或 `socks5://localhost:1080`。如果您的网络环境需要代理才能访问 Google 服务，请设置此项。

浏览器打开Gemini网页端登录后，通过开发者工具查看Cookie中 `__Secure-1PSID` 和 `__Secure-1PSIDTS` 的值。

## 如何运行

### 使用 Docker (推荐)

1.  **构建 Docker 镜像:**
    ```bash
    docker build -t gemini-openai-api .
    ```

2.  **运行 Docker 容器:**
    将 `YOUR_SECURE_1PSID_VALUE` 和 `YOUR_SECURE_1PSIDTS_VALUE` 替换为您的实际 Cookie 值。
    ```bash
    docker run -d -p 8899:8899 \
      -e SECURE_1PSID="YOUR_SECURE_1PSID_VALUE" \
      -e SECURE_1PSIDTS="YOUR_SECURE_1PSIDTS_VALUE" \
      -e GEMINI_PROXY="YOUR_PROXY_URL_IF_NEEDED" \
      --name gemini_api gemini-openai-api
    ```
    如果您不需要代理，可以省略 `-e GEMINI_PROXY="YOUR_PROXY_URL_IF_NEEDED"` 这一行。

### 本地运行 (用于开发)

1.  **克隆仓库:**
    ```bash
     git clone https://github.com/dingyufei615/gemini-to-api.git
     cd gemini-to-api
    ```

2.  **创建并激活虚拟环境 (推荐):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate  # Windows
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **设置环境变量:**
    ```bash
    export SECURE_1PSID="YOUR_SECURE_1PSID_VALUE"
    export SECURE_1PSIDTS="YOUR_SECURE_1PSIDTS_VALUE"
    export GEMINI_PROXY="YOUR_PROXY_URL_IF_NEEDED" # 如果需要代理，请设置此项
    ```
    对于 Windows，使用 `set SECURE_1PSID=YOUR_SECURE_1PSID_VALUE`，`set SECURE_1PSIDTS=YOUR_SECURE_1PSIDTS_VALUE` 和 `set GEMINI_PROXY=YOUR_PROXY_URL_IF_NEEDED`。如果不需要代理，可以省略 GEMINI_PROXY 相关的设置。

5.  **启动应用 (使用 Uvicorn):**
    ```bash
    uvicorn api.chat_api:app --host 0.0.0.0 --port 8000 --reload
    ```
    `--reload` 标志用于在代码更改时自动重新加载服务器，非常适合开发。

## API 端点

### `POST /v1/chat/completions`

此端点与 OpenAI 的 chat completions API 兼容。

**请求体示例:**

```json
{
    "model": "gemini-2.5-exp-advanced",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好，Gemini！请介绍一下你自己。"}
    ],
    "stream": true
}
```

## 模型

unspecified - Default model

gemini-2.0-flash - Gemini 2.0 Flash

gemini-2.0-flash-thinking - Gemini 2.0 Flash Thinking Experimental

gemini-2.5-flash - Gemini 2.5 Flash

gemini-2.5-pro - Gemini 2.5 Pro (daily usage limit imposed)


Models pending update (may not work as expected):

gemini-2.5-exp-advanced - Gemini 2.5 Experimental Advanced (requires Gemini Advanced account)

gemini-2.0-exp-advanced - Gemini 2.0 Experimental Advanced (requires Gemini Advanced account)


**响应:**

-   如果 `stream: false`，响应将是一个包含完整聊天回复的 JSON 对象。
-   如果 `stream: true`，响应将是一个 `text/event-stream`，其中包含一系列服务器发送事件 (SSE)。

## 注意事项

-   **Cookie 有效性**: `Secure_1PSID` 和 `Secure_1PSIDTS` Cookie 可能会过期或失效。您需要确保它们是有效的。
-   **错误处理**: 如果未提供有效的 Cookie 或 `gemini-webapi` 无法初始化，API 将返回错误。
-   **`gemini-webapi` 库**: 此项目依赖于 `gemini-webapi` 库。该库与非官方的 Gemini Web API 交互，其行为可能会随 Google 对 Gemini Web API 的更改而更改。

## 贡献
感谢 https://github.com/HanaokaYuzu/Gemini-API 提供的 gemini-webapi 实现。
本项目代码99.99% 由 Gemini-2.5-pro + Aider 共同完成。
欢迎提出问题、错误报告和PR。
