"""Day 6 chat-cli: multi-turn DeepSeek chat with streaming output."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
TIMEOUT_SECONDS = 120
MAX_CONTEXT_TOKENS = 8000
SYSTEM_PROMPT = "你是一个乐于助人的中文 AI 助手，回答要准确、简洁。"

BASE_DIR = Path(__file__).resolve().parent


def find_env_path() -> Path:
    # 优先读取同目录 .env，找不到时回退到 day5 的 .env
    candidates = [BASE_DIR / ".env", BASE_DIR.parent / "day5" / ".env"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return BASE_DIR / ".env"


def load_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str:
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
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    parts: list[str] = []
    usage: dict | None = None
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if not choices:
                continue
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    api_key = get_api_key()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("chat-cli 已就绪：多轮对话 + 流式输出，输入 exit 或 quit 退出。")

    while True:
        try:
            user_text = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            print("输入不能为空，请重新输入。")
            continue

        messages.append({"role": "user", "content": user_text})
        trim_history(messages)

        try:
            reply, usage = ask_deepseek_stream(api_key, messages)
            messages.append({"role": "assistant", "content": reply})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", "-")
                completion_tokens = usage.get("completion_tokens", "-")
                print(f"[tokens: prompt={prompt_tokens}, completion={completion_tokens}]")
        except urllib.error.HTTPError as exc:
            messages.pop()
            print(f"模型接口返回错误 HTTP {exc.code}")
        except TimeoutError:
            messages.pop()
            print("请求超时，请重试。")
        except urllib.error.URLError as exc:
            messages.pop()
            print(f"网络请求失败: {exc.reason}")
        except (json.JSONDecodeError, KeyError, IndexError):
            messages.pop()
            print("接口返回内容无法解析，请稍后重试。")


if __name__ == "__main__":
    main()
