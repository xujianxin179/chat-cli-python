# Day 6 chat-cli

基于 Day 5 升级为多轮对话 + 流式输出 + 历史裁剪的命令行程序。

## 功能

- 多轮对话：维护 system/user/assistant 消息历史
- 流式输出：逐 token 打印，带打字机效果
- 历史裁剪：超过 8000 token 预算时删除最早的对话
- 20 轮自动测试：记录每轮 token 消耗和错误

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

## 安全说明

`.env` 已加入 `.gitignore`，不会被提交到 GitHub；仓库只保留 `.env.example` 占位文件。API Key 只出现在请求头中，不打印、不写日志。
