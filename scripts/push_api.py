# -*- coding: utf-8 -*-
"""把本地提交推送到 GitHub —— 走 REST API，绕开 git 的网络/代理问题。

只上传自上次成功推送以来改动过的文件（记在 .last_push 里）。
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
REPO = "pwm385/td2"
MARK = ROOT / ".last_push"


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def token() -> str:
    p = subprocess.run(["git", "credential", "fill"], cwd=str(ROOT), capture_output=True,
                       text=True, input="protocol=https\nhost=github.com\n\n")
    for line in (p.stdout or "").splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("拿不到 GitHub 凭证，请先手动 git push 一次")


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + token(), "Accept": "application/vnd.github+json",
        "Content-Type": "application/json", "User-Agent": "td2-local-bot"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> int:
    head = git("rev-parse", "HEAD")
    since = MARK.read_text(encoding="utf-8").strip() if MARK.exists() else ""
    if not since:
        since = git("rev-parse", "origin/main")
    if since and subprocess.run(["git", "cat-file", "-e", since], cwd=str(ROOT),
                                capture_output=True).returncode != 0:
        since = ""

    files = []
    if since and since != head:
        files = [f for f in git("diff", "--name-only", since, head).splitlines() if f]
    if not files:
        print("没有需要推送的改动")
        return 0

    ref = call("GET", f"/repos/{REPO}/git/ref/heads/main")
    base_sha = ref["object"]["sha"]
    base = call("GET", f"/repos/{REPO}/git/commits/{base_sha}")

    tree = []
    for f in files:
        p = ROOT / f
        if not p.exists():
            continue
        b64 = base64.b64encode(p.read_bytes()).decode()
        blob = call("POST", f"/repos/{REPO}/git/blobs", {"content": b64, "encoding": "base64"})
        tree.append({"path": f, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    if not tree:
        print("改动文件都不存在，跳过")
        return 0

    nt = call("POST", f"/repos/{REPO}/git/trees", {"base_tree": base["tree"]["sha"], "tree": tree})
    c = call("POST", f"/repos/{REPO}/git/commits",
             {"message": f"data: 本机更新 {len(tree)} 个文件", "tree": nt["sha"], "parents": [base_sha]})
    call("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": c["sha"]})
    MARK.write_text(head, encoding="utf-8")
    print(f"API 推送成功 {c['sha'][:7]}（{len(tree)} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
