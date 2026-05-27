#!/usr/bin/env python3
"""Claude Code の PostToolUse フックから呼ばれ、ツール使用履歴を1行ログに追記する。

標準入力で受け取る JSON 例:
  {"session_id": "...", "tool_name": "Bash", "tool_input": {...}, "tool_response": {...}}
"""

import json
import sys
import datetime
from pathlib import Path


LOG_DIR = Path("/workspace/logs")
LOG_FILE = LOG_DIR / "all-agents.log"
MAX_INPUT_LEN = 200


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # フックの仕様が変わっていても落とさない
        return 0

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    tool_name = data.get("tool_name", "-")
    session_id = data.get("session_id", "-")
    tool_input = str(data.get("tool_input", ""))[:MAX_INPUT_LEN]

    line = f"[{timestamp}] session={session_id[:8]} tool={tool_name} input={tool_input}"

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
