#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push.py — 把本地代码无线下发到 M5Stack CoreS3 (UIFlow2)

原理:
    把本地文件(默认为 src/key.py) 的内容写入 GitHub 仓库 bvcvb/led 的 src/key.py (master 分支)。
    设备端 device/loader.py 会通过 requests2.get(该文件的 raw 地址) 拉取并执行。

前置:
    1. 一个 GitHub 仓库 (本脚本默认 bvcvb/led, 可通过环境变量覆盖)。
    2. 一个 GitHub Personal Access Token (默认 fine-grained PAT),
       需要有该仓库的 Contents 读写权限。
       通过环境变量 GITHUB_TOKEN 传入。

用法:
    export GITHUB_TOKEN="github_pat_..."
    python3 push.py [local_file]    # 推送到 bvcvb/led 的 master/src/key.py (默认 src/key.py)

可选环境变量:
    GH_OWNER   仓库属主 (默认 bvcvb)
    GH_REPO    仓库名   (默认 led)
    GH_BRANCH  分支     (默认 master)
    GH_PATH    仓库内文件路径 (默认 src/key.py)

返回:
    成功时打印设备端可用的 raw 地址(fetch_url)。
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

# 默认目标
DEFAULT_OWNER = "bvcvb"
DEFAULT_REPO = "led"
DEFAULT_BRANCH = "master"
DEFAULT_PATH = "src/key.py"
DEFAULT_FILE = "src/key.py"

# GitHub API
API_CONTENTS = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"


def die(msg: str, code: int = 1) -> None:
    print(f"[push] 错误: {msg}", file=sys.stderr)
    sys.exit(code)


def api_request(req: urllib.request.Request, token: str, data: bytes = None) -> dict:
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        die(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        die(f"网络错误: {e.reason}")


def get_sha(owner, repo, path, branch, token):
    """取仓库里该文件当前 sha, 不存在返回 None。"""
    import urllib.parse
    url = API_CONTENTS.format(owner=owner, repo=repo,
                              path=urllib.parse.quote(path, safe="/"))
    url += f"?ref={branch}"
    req = urllib.request.Request(url, method="GET")
    try:
        data = api_request(req, token)
        return data.get("sha")
    except SystemExit:
        # 404 = 文件不存在, 允许创建
        return None


def push(owner, repo, path, branch, content, token):
    """把 content 写入仓库的 path 文件 (指定分支), 自动创建或更新。"""
    import urllib.parse
    url = API_CONTENTS.format(owner=owner, repo=repo,
                              path=urllib.parse.quote(path, safe="/"))
    sha = get_sha(owner, repo, path, branch, token)
    payload = {
        "message": f"update {path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(url, method="PUT")
    return api_request(req, token, data=json.dumps(payload).encode("utf-8"))


def read_local(path: str) -> str:
    if not os.path.isfile(path):
        die(f"本地文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main() -> None:
    local_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE

    owner = os.environ.get("GH_OWNER", DEFAULT_OWNER)
    repo = os.environ.get("GH_REPO", DEFAULT_REPO)
    branch = os.environ.get("GH_BRANCH", DEFAULT_BRANCH)
    path = os.environ.get("GH_PATH", DEFAULT_PATH)

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        die("缺少 GITHUB_TOKEN 环境变量 (需该仓库 Contents 读写权限)。")

    content = read_local(local_file)
    push(owner, repo, path, branch, content, token)

    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    print(f"[push] 已更新 {owner}/{repo}/{branch}/{path} ({len(content)} bytes)")
    print(f"[push] fetch_url (设备端 loader 用这个):\n       {raw_url}")


if __name__ == "__main__":
    main()
