#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push.py — 把本地代码无线下发到 M5Stack CoreS3 (UIFlow2)

原理:
    把本地文件(默认为 key.py) 的内容写入 GitHub Gist 的某个文件。
    设备端 device/loader.py 会通过 requests2.get(该 Gist 文件的 raw 地址) 拉取并执行。

前置:
    1. 一个 GitHub Gist (先在网页上建一个, 记下其 gist_id)。
    2. 一个 GitHub Personal Access Token, 权限勾选 "gist"。
       通过环境变量 GITHUB_TOKEN 传入。

用法:
    export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
    python3 push.py <GIST_ID> [local_file]        # 更新 gist 里的 <basename(local_file)>
    python3 push.py <GIST_ID>            # 默认更新 key.py
    GITHUB_TOKEN=xxx python3 push.py <GIST_ID> key.py

返回:
    成功时打印设备端可用的 raw 地址(fetch_url)。
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

# Gist 文件更新接口
API = "https://api.github.com/gists/{gist_id}"
# 默认本地文件
DEFAULT_FILE = "key.py"


def die(msg: str, code: int = 1) -> None:
    print(f"[push] 错误: {msg}", file=sys.stderr)
    sys.exit(code)


def read_local(path: str) -> str:
    if not os.path.isfile(path):
        die(f"本地文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def push(gist_id: str, content: str, filename: str, token: str) -> dict:
    """用 GitHub API 把 content 写入 gist 的 filename 文件。"""
    url = API.format(gist_id=gist_id)
    payload = {"files": {filename: {"content": content}}}
    req = urllib.request.Request(url, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        die(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        die(f"网络错误: {e.reason} ({url})")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        die("用法: python3 push.py <GIST_ID> [local_file]")
    gist_id = args[0]
    local_file = args[1] if len(args) > 1 else DEFAULT_FILE

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        die("缺少 GITHUB_TOKEN 环境变量 (需 gist 权限)。")

    filename = os.path.basename(local_file)
    content = read_local(local_file)
    result = push(gist_id, content, filename, token)

    # 从返回中找到该文件的 raw 地址
    files = result.get("files", {})
    entry = files.get(filename)
    raw_url = (entry or {}).get("raw_url")

    print(f"[push] 已更新 gist 文件: {filename}")
    print(f"[push] gist_url: {result.get('html_url', '')}")
    if raw_url:
        print(f"[push] fetch_url (设备端 loader 用这个):\n       {raw_url}")
    else:
        print("[push] 警告: 未取到 raw_url, 请从 gist 网页手动复制 raw 地址。")


if __name__ == "__main__":
    main()
