"""Day 5 chat-cli: one-round DeepSeek chat from the command line."""

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
# 单次请求最长等待 60 秒
TIMEOUT_SECONDS = 60

# 以脚本所在目录为基准，方便读取同目录下的 .env
BASE_DIR = Path(__file__).resolve().parent


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
    env = load_env_file(BASE_DIR / ".env")
    key = env.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        print("缺少 DEEPSEEK_API_KEY，请检查 .env")
        sys.exit(1)
    return key


def ask_deepseek(api_key: str, user_text: str) -> str:
    # 构造 OpenAI 兼容的 chat/completions 请求体
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_text}],
        "stream": False,
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
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    # 返回模型回复文本
    return data["choices"][0]["message"]["content"]


def main() -> None:
    # 强制 UTF-8 输出，避免 Windows 控制台中文乱码
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    api_key = get_api_key()
    print("chat-cli 已就绪，输入 exit 或 quit 退出。")

    # 主循环：读取输入、校验输入、调用模型、打印回复
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

        try:
            reply = ask_deepseek(api_key, user_text)
            print("DeepSeek:", reply)
        except urllib.error.HTTPError as exc:
            # HTTPError 是 URLError 的子类，必须放在前面才能拿到状态码
            print(f"模型接口返回错误 HTTP {exc.code}")
        except TimeoutError:
            print("请求超时，请重试。")
        except urllib.error.URLError as exc:
            print(f"网络请求失败: {exc.reason}")
        except (json.JSONDecodeError, KeyError, IndexError):
            # 接口返回非 JSON，或 JSON 里缺少预期字段时统一提示
            print("接口返回内容无法解析，请稍后重试。")


if __name__ == "__main__":
    main()
