# -*- coding: utf-8 -*-
"""本机每日更新：抓数据 → 提交 → 推送（推到失败会自动改用 GitHub API）。

计划任务在 16:00 / 16:01 各触发一次；如果源站还没换轮，这里会每 60 秒重试一次，
最多重试 6 分钟，抓到就停。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
LOCK = ROOT / ".update.lock"
LOG = ROOT / ".update.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    # 防止两次触发重叠
    if LOCK.exists():
        age = time.time() - LOCK.stat().st_mtime
        if age < 900:
            log(f"已有任务在跑（{int(age)}秒前），退出")
            return 0
    LOCK.write_text(str(time.time()), encoding="utf-8")
    try:
        changed = False
        for attempt in range(7):
            rc, out = run([PY, str(ROOT / "scripts" / "fetch.py"), "--days", "3"])
            tail = " / ".join(out.strip().splitlines()[-2:])
            log(f"第{attempt + 1}次抓取: {tail}")
            if "[OK]" in out:
                changed = True
                break
            if "[未更新]" not in out:
                # 没有新东西可抓（已经是最新）→ 不用等
                log("数据已是最新，无需重试")
                return 0
            if attempt < 6:
                time.sleep(60)
        if not changed:
            log("源站暂未换轮，本次结束（云端任务会继续兜底）")
            return 0

        run(["git", "add", "-A", "data", "assets"])
        rc, out = run(["git", "commit", "-m", f"data: {time.strftime('%Y-%m-%d')}"])
        if rc != 0 and "nothing to commit" not in out:
            log("提交失败: " + out.strip()[-200:])
            return 1

        rc, out = run(["git", "push"], timeout=120)
        if rc == 0:
            head = run(["git", "rev-parse", "HEAD"])[1].strip()
            (ROOT / ".last_push").write_text(head, encoding="utf-8")
            log("已通过 git 推送")
            return 0
        log("git 推送失败，改用 GitHub API")
        rc2, out2 = run([PY, str(ROOT / "scripts" / "push_api.py")])
        log(out2.strip()[-300:])
        return 0 if rc2 == 0 else 1
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
