# Day 5 chat-cli

用命令行完成一轮 DeepSeek 问答：输入一句话，调用 DeepSeek，打印回复。

## 文件结构

```text
week1/day5/
├── main.py
├── .env          # 真实 API Key，已被 .gitignore 忽略
├── .env.example  # 占位配置，可提交
├── .gitignore
└── README.md
```

## 运行

1. 确认 `.env` 里存在 `DEEPSEEK_API_KEY`。
2. 运行：

```bash
python main.py
```

3. 输入问题后回车，等待模型回复；输入 `exit` 或 `quit` 退出。

## 错误处理

- 空输入：提示重新输入。
- 缺少 Key：退出并提示检查 `.env`。
- 网络超时：提示请求超时。
- 模型报错：打印 HTTP 状态码。
- 返回内容解析失败：提示稍后重试。

## 安全说明

`.env` 已加入 `.gitignore`，不会被提交到 GitHub；仓库只保留 `.env.example` 占位文件。代码不会打印 API Key，也不会在日志中输出请求头。
