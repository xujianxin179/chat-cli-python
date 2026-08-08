"""Run 20 consecutive rounds against DeepSeek and record token usage."""

import sys
import time
from pathlib import Path

from main import (
    SYSTEM_PROMPT,
    ask_deepseek_stream,
    get_api_key,
    trim_history,
)

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "test_results.md"

# 20 个测试问题：包含记忆、算术、总结等，用于验证多轮上下文
PROMPTS = [
    "你好",
    "请记住我的名字叫小明",
    "我叫什么名字？",
    "请只回复：收到",
    "3+4 等于几？",
    "请把 3+4 的结果再加上 10",
    "请记住我的城市是上海",
    "我的城市是哪里？",
    "请只回复：继续",
    "我们刚才在聊什么主题？",
    "请把我记住的名字和城市一起说出来",
    "用一句话总结当前对话",
    "请只回复：第13轮",
    "7 乘以 8 等于多少？",
    "请把上一个问题的答案减 1",
    "我的名字是张三，请改一下记忆",
    "现在我叫什么名字？",
    "请只回复：测试通过",
    "还剩几轮？",
    "这是第20轮，请总结整段对话",
]


def main() -> int:
    api_key = get_api_key()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    rows = []
    total_prompt = 0
    total_completion = 0
    total_usage = 0
    errors = []

    for index, prompt in enumerate(PROMPTS, start=1):
        # 与真实 CLI 一致：先加入用户消息，再裁剪历史
        messages.append({"role": "user", "content": prompt})
        trim_history(messages)

        # 每轮单独记录回复长度、Token 用量和错误信息
        row = {
            "round": index,
            "prompt": prompt,
            "reply_length": 0,
            "prompt_tokens": "-",
            "completion_tokens": "-",
            "total_tokens": "-",
            "error": "",
        }

        try:
            # 瞬时网络错误最多重试 3 次，避免一次 SSL 抖动导致整轮失败
            for attempt in range(1, 4):
                try:
                    reply, usage = ask_deepseek_stream(api_key, messages, print_stream=False)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < 3:
                        time.sleep(2)
                    else:
                        row["error"] = last_error
                        errors.append(last_error)
                        messages.pop()
            if not row["error"]:
                # 成功后把 assistant 回复写回历史，保证后续问题能参考前文
                messages.append({"role": "assistant", "content": reply})
                row["reply_length"] = len(reply)
                if usage:
                    # 累计整轮测试的 Token 消耗
                    row["prompt_tokens"] = usage.get("prompt_tokens", "-")
                    row["completion_tokens"] = usage.get("completion_tokens", "-")
                    row["total_tokens"] = usage.get("total_tokens", "-")
                    total_prompt += int(row["prompt_tokens"] or 0)
                    total_completion += int(row["completion_tokens"] or 0)
                    total_usage += int(row["total_tokens"] or 0)
        except Exception as exc:  # noqa: BLE001
            # 外层兜底：处理重试逻辑之外的意外错误
            row["error"] = f"{type(exc).__name__}: {exc}"
            errors.append(row["error"])
            messages.pop()

        rows.append(row)
        status = "OK" if not row["error"] else "ERR"
        print(f"第 {index:02d} 轮 {status}: {prompt[:20]} | 回复 {row['reply_length']} 字 | total={row['total_tokens']}")

    write_results(rows, total_prompt, total_completion, total_usage, len(errors))
    return 1 if errors else 0


def write_results(
    rows: list[dict],
    total_prompt: int,
    total_completion: int,
    total_usage: int,
    error_count: int,
) -> None:
    # 生成 Markdown 测试结果表，方便直接放进仓库或演示
    lines = [
        "# Day 6 连续 20 轮测试结果",
        "",
        "| 轮次 | 输入 | 回复字数 | prompt tokens | completion tokens | total tokens | 错误 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    # 每个测试问题输出一行记录
    for row in rows:
        lines.append(
            f"| {row['round']} | {row['prompt']} | {row['reply_length']} | "
            f"{row['prompt_tokens']} | {row['completion_tokens']} | {row['total_tokens']} | {row['error'] or '-'} |"
        )
    lines += [
        "",
        "## 汇总",
        "",
        f"- 总轮次：{len(rows)}",
        f"- 成功轮次：{len(rows) - error_count}",
        f"- 失败轮次：{error_count}",
        f"- prompt tokens 合计：{total_prompt}",
        f"- completion tokens 合计：{total_completion}",
        f"- total tokens 合计：{total_usage}",
    ]
    # 结果文件用 UTF-8 保存，避免中文乱码
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
