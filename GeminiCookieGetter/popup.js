document.addEventListener('DOMContentLoaded', function () {
    const sendButton = document.getElementById('sendButton');
    const statusDisplay = document.getElementById('statusDisplay');

    const targetUrlForCookies = "https://gemini.google.com";
    // 另外两个来自你的用户脚本。
    const cookieNamesToFetch = ["__Secure-1PSID", "__Secure-1PSIDTS"];
    const postDataUrl = 'http://192.168.202.190:8899/api/cookies';

    sendButton.addEventListener('click', async function () {
        sendButton.textContent = '正在发送...';
        sendButton.disabled = true;
        statusDisplay.textContent = ''; // 清除之前的状态

        try {
            const cookiesPayload = {};

            // 辅助函数，用于获取单个Cookie
            // 返回一个Promise，解析为cookie对象或null
            function getCookiePromise(name) {
                return new Promise((resolve, reject) => {
                    chrome.cookies.get({ url: targetUrlForCookies, name: name }, function (cookie) {
                        if (chrome.runtime.lastError) {
                            // 如果在获取cookie时发生错误 (例如，权限问题，虽然这里不太可能)
                            console.error(`获取Cookie ${name} 失败:`, chrome.runtime.lastError.message);
                            return reject(new Error(chrome.runtime.lastError.message));
                        }
                        resolve(cookie); // cookie可能是null（如果未找到）或cookie对象
                    });
                });
            }

            // 并行获取所有需要的cookies
            const cookiePromises = cookieNamesToFetch.map(name => getCookiePromise(name));
            const resolvedCookies = await Promise.all(cookiePromises);

            resolvedCookies.forEach((cookie, index) => {
                const name = cookieNamesToFetch[index];
                cookiesPayload[name] = cookie ? cookie.value : null;
                if (!cookie) {
                    console.warn(`未能找到 Cookie: ${name}`);
                }
            });

            console.log('准备发送的 Cookie 数据:', cookiesPayload);
            statusDisplay.textContent = '正在准备数据...';

            const response = await fetch(postDataUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(cookiesPayload)
            });

            const responseDataText = await response.text(); // 获取响应体文本以供调试

            if (response.ok) { // 状态码在 200-299 之间
                console.log('Cookie 数据成功发送:', responseDataText);
                statusDisplay.textContent = 'Cookies 已成功发送!';
                sendButton.textContent = '已发送!';
            } else {
                console.error('发送 Cookie 数据失败. 状态码:', response.status, '响应:', responseDataText);
                statusDisplay.textContent = `发送失败: ${response.status}. 服务器响应: ${responseDataText.substring(0, 100)}`; // 显示部分服务器响应
                sendButton.textContent = '发送失败!';
            }

        } catch (error) {
            console.error('在获取或发送 Cookie 数据时发生错误:', error);
            statusDisplay.textContent = `错误: ${error.message}`;
            sendButton.textContent = '发生错误!';
        } finally {
            // 3秒后恢复按钮状态
            setTimeout(() => {
                sendButton.textContent = '发送 Cookies';
                sendButton.disabled = false;
            }, 3000);
        }
    });
});