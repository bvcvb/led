# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Copyright (c) 2024. 本文件为设备端引导程序 (CoreS3 + UIFlow2 固件)
#
# loader.py — 设备端「主动拉取」引导程序  (UIFlow2 运行模型版)
#
# ⚠️ 重要: 这是给 UIFlow2 设备端用的 main.py。UIFlow2 会自动调用 setup()/loop(),
#          因此本文件【不要】写 if __name__ == "__main__" 主循环, 也不要 while True。
#          你只需提供 setup() 和 loop() 两个函数即可。
#
# 作用:
#   开机(此时 UIFlow2 固件已自动连 WiFi)周期性 requests2.get(<仓库 raw url>)
#   拉取代码并 exec 运行。dsh 通过 push.py 更新仓库后, 设备下个周期自动拉到新版。
#
# 部署:
#   在 UIFlow2 网页 IDE 里, 把本文件内容粘到「可执行 Python」代码块中,
#   点 Run Always 下载到设备。

import time
import gc
import requests2

# ---- 配置区 -------------------------------------------------------------
FETCH_URL = "https://raw.githubusercontent.com/bvcvb/led/master/key.py"
POLL_INTERVAL_MS = 5000          # 轮询间隔(毫秒)
FETCH_TIMEOUT_MS = 10000         # 单次 GET 超时(毫秒)
# ------------------------------------------------------------------------

_last_code = None


def _fetch():
    """拉取仓库 raw 内容, 失败返回 None(不抛异常)。"""
    global _last_code
    try:
        resp = requests2.get(FETCH_URL, timeout=FETCH_TIMEOUT_MS)
        text = resp.text
        if text is None:
            text = ""
        # 内容无变化则返回 None 让上层跳过
        if text == _last_code:
            return None
        _last_code = text
        return text
    except BaseException as e:
        print("[loader] GET failed:", e)
        return None


def _run(text):
    """exec 拉到的代码。捕获异常, 不让引导程序崩溃。"""
    try:
        ns = {"__name__": "__app__"}
        exec(text, ns)
    except BaseException as e:
        print("[loader] run error:", e)
    finally:
        gc.collect()


def setup():
    # 自检: 打印设备已启动 + 目标 URL (UIFlow2 启动时调用一次)
    print("[loader] started, polling:", FETCH_URL)


def loop():
    # UIFlow2 会不断调用 loop(), 在这里做周期拉取 + 运行
    code = _fetch()
    if code:
        print("[loader] got new code, (%d bytes)" % len(code))
        _run(code)
    time.sleep_ms(POLL_INTERVAL_MS)
