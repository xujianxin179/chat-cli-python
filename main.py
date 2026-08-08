"""Day 6 chat-cli: multi-turn DeepSeek chat with streaming output."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# DeepSeek 的 OpenAI 兼容接口地址
API_URL = "https://api.deepseek.com/chat/completions"
# DeepSeek 通用对话模型
MODEL = "deepseek-chat"
# 单次请求最长等待 120 秒，流式回复可能耗时较长
TIMEOUT_SECONDS = 120
# 上下文 Token 预算，超过后裁剪最早的历史消息
MAX_CONTEXT_TOKENS = 8000
# 系统提示词，定义助手的整体行为
SYSTEM_PROMPT = "你是一个乐于助人的中文 AI 助手，回答要准确、简洁。"

# 脚本所在目录，用于定位 .env 和测试结果
BASE_DIR = Path(__file__).resolve().parent


def find_env_path() -> Path:
    # 优先读取同目录 .env，找不到时回退到 day5 的 .env
    candidates = [BASE_DIR / ".env", BASE_DIR.parent / "day5" / ".env"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return BASE_DIR / ".env"


def load_env_file(path: Path) -> dict[str, str]:
    # 手动解析 .env，避免引入 python-dotenv 等第三方依赖
    values = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # 跳过空行、注释行和缺少等号的行
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # 去掉 Key/Value 两端的空白和引号
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str:
    # 优先读取 .env，其次读取系统环境变量
    env = load_env_file(find_env_path())
    key = env.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        print("缺少 DEEPSEEK_API_KEY，请检查 .env")
        sys.exit(1)
    return key


def estimate_tokens(text: str) -> int:
    # 简单估算：中文字符约 2 字符 1 token，英文单词额外计 token
    return max(1, len(text) // 2 + len(text.split()))


def history_tokens(messages: list[dict[str, str]]) -> int:
    # 累加所有消息的估算 Token 数
    return sum(estimate_tokens(message.get("content", "")) for message in messages)


def trim_history(messages: list[dict[str, str]], budget: int = MAX_CONTEXT_TOKENS) -> None:
    # 超过预算时删除最早的 user + assistant 对话对，保留 system 和当前问题
    while len(messages) > 2 and history_tokens(messages) > budget:
        del messages[1:3]


def ask_deepseek_stream(
    api_key: str,
    messages: list[dict[str, str]],
    print_stream: bool = True,
) -> tuple[str, dict | None]:
    # stream=True 让接口逐 token 返回；include_usage 让最后一帧携带用量统计
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    # ensure_ascii=False 保留中文，避免请求体变成难以排查的转义序列
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            # API Key 只放进请求头，不打印、不写日志
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    parts: list[str] = []
    usage: dict | None = None
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        # 流式响应按行读取，只处理 SSE 格式的 data: 数据
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            # [DONE] 表示整个流结束
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            # 最后一帧可能携带整轮请求的 usage 统计
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if not choices:
                continue
            # 从 delta 里取出本次增量文本，逐字打印形成打字机效果
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                parts.append(content)
                if print_stream:
                    print(content, end="", flush=True)

    if print_stream:
        print()
    return "".join(parts), usage


def main() -> None:
    # 强制 UTF-8 输出，避免 Windows 控制台中文乱码
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    api_key = get_api_key()
    # 多轮对话核心：整个消息历史都保存在 messages 里
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("chat-cli 已就绪：多轮对话 + 流式输出，输入 exit 或 quit 退出。")

    # 主循环：读取输入、追加历史、调用模型、保存回复
    while True:
        try:
            user_text = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C 或管道输入结束也正常退出
            print()
            break

        # 支持 exit / quit 退出
        if user_text.lower() in {"exit", "quit"}:
            break
        # 空输入不调用接口，直接提示重新输入
        if not user_text:
            print("输入不能为空，请重新输入。")
            continue

        # 先把用户问题加入历史，再裁剪，最后发送给模型
        messages.append({"role": "user", "content": user_text})
        trim_history(messages)

        try:
            reply, usage = ask_deepseek_stream(api_key, messages)
            # 模型回复也存入历史，下一次提问才能记住上下文
            messages.append({"role": "assistant", "content": reply})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", "-")
                completion_tokens = usage.get("completion_tokens", "-")
                print(f"[tokens: prompt={prompt_tokens}, completion={completion_tokens}]")
        except urllib.error.HTTPError as exc:
            # 请求失败时移除刚才的用户消息，避免失败内容污染历史
            messages.pop()
            print(f"模型接口返回错误 HTTP {exc.code}")
        except TimeoutError:
            messages.pop()
            print("请求超时，请重试。")
        except urllib.error.URLError as exc:
            messages.pop()
            print(f"网络请求失败: {exc.reason}")
        except (json.JSONDecodeError, KeyError, IndexError):
            # 接口返回非 JSON，或 JSON 里缺少预期字段时统一提示
            messages.pop()
            print("接口返回内容无法解析，请稍后重试。")


if __name__ == "__main__":
    main()
