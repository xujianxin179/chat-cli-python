# chat-cli

第 1 周核心练习项目：命令行多轮对话 CLI。

## 功能

- 单轮问答：输入问题，调用 DeepSeek，打印回复
- 多轮对话：维护 system/user/assistant 消息历史
- 流式输出：逐 token 打印，带打字机效果
- 历史裁剪：超过 8000 Token 预算时删除最早的对话
- 20 轮自动测试：记录每轮 Token 消耗和错误

## 技术栈

- Python 3.9+
- DeepSeek HTTP API（OpenAI 兼容 Chat Completions）
- 标准库实现，不依赖第三方包

## 目录结构

```text
chat-cli/
├── main.py
├── test_20_rounds.py
├── test_results.md
├── README.md
├── .gitignore
└── .env.example
```

## 安装

1. 安装 Python 3.9 或更高版本。
2. 复制 `.env.example` 为 `.env`：

```powershell
Copy-Item .env.example .env
```

3. 编辑 `.env`，填入真实 Key：

```text
DEEPSEEK_API_KEY=sk-xxxx
```

## 运行

```powershell
python main.py
```

输入 `exit` 或 `quit` 退出。

## 自动测试

```powershell
python test_20_rounds.py
```

测试脚本对瞬时网络错误会自动重试 3 次，测试结果写入 `test_results.md`。

## 多轮对话原理

程序把所有消息保存在一个列表里：

```text
[system, user1, assistant1, user2, assistant2, ...]
```

每次请求都发送完整消息列表，所以模型能记住上下文。

## 历史裁剪

默认预算为 8000 Token。超过预算时，程序删除最早的 `user + assistant` 对话对，保留 system 提示和当前问题，避免上下文爆掉。

## 常见问题

### 提示缺少 DEEPSEEK_API_KEY

检查当前目录是否存在 `.env`，并确认变量名是 `DEEPSEEK_API_KEY`。

### 中文乱码

代码已强制 UTF-8 输出；如果终端仍乱码，请把终端编码切到 UTF-8。

### 请求超时

网络不稳定时会提示超时；测试脚本会自动重试 3 次，手动运行时重新输入即可。

### 输出不像流式

确认请求里 `stream` 为 `True`，并且打印时使用 `flush=True`。

## 安全说明

`.env` 已加入 `.gitignore`，不会被提交到 GitHub；仓库只保留 `.env.example` 占位文件。API Key 只出现在请求头中，不打印、不写日志。
