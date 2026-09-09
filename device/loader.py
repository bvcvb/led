# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Copyright (c) 2024. 本文件为设备端引导程序 (CoreS3 + UIFlow2 固件)
#
# loader.py — 设备端「主动拉取」引导程序  (作为设备 /main.py 部署)
#
# 角色: 这是设备开机自启的 main.py。它负责:
#   1. 周期从仓库拉取应用代码(默认 key.py)
#   2. 把应用代码 exec 到一个命名空间, 并调用其 setup()/loop()
#
# ⚠️ 结构说明:
#   - 本文件是标准 MicroPython 脚本, 作为 /main.py 运行时 __name__=="__main__",
#     因此用 if __name__ == "__main__": 启动主循环(与 boot.py 的做法一致)。
#   - 应用代码(key.py)由它通过 exec() 动态加载, 因此 key.py【不要再放死循环】,
#     只提供 setup()/loop(); 由本 loader 的 while True 统一调度。
#
# 部署(mpremote, 在你自己电脑上):
#   mpremote connect /dev/ttyACM0 cp device/loader.py :main.py
#   mpremote connect /dev/ttyACM0 reset
# 之后业务更新走: python3 push.py  (自动推 key.py 到 bvcvb/led/master/key.py)

import time
import gc
import requests2

# ---- 配置区 -------------------------------------------------------------
FETCH_URL = "https://raw.githubusercontent.com/bvcvb/led/master/key.py"
POLL_INTERVAL_MS = 5000          # 拉取/轮询间隔(毫秒)
FETCH_TIMEOUT_MS = 10000         # 单次 GET 超时(毫秒)
# ------------------------------------------------------------------------

_last_code = None
_app_ns = None                   # 应用代码的命名空间


def fetch_code():
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


def load_app(text):
    """把新拉到的应用代码 exec 进独立命名空间, 保存供后续渲染循环使用。"""
    global _app_ns
    try:
        ns = {"__name__": "__app__"}
        exec(text, ns)
        _app_ns = ns
        return True
    except BaseException as e:
        print("[loader] load error:", e)
        return False


def app_setup():
    if _app_ns is not None and "setup" in _app_ns:
        _app_ns["setup"]()


def app_loop():
    if _app_ns is not None and "loop" in _app_ns:
        _app_ns["loop"]()


def setup():
    # loader 自身自检
    print("[loader] started, polling:", FETCH_URL)


def loop():
    # 1) 拉取新代码: 有更新就加载并重建应用上下文
    code = fetch_code()
    if code:
        print("[loader] got new code, (%d bytes)" % len(code))
        if load_app(code):
            print("[loader] app loaded")
            app_setup()
    # 2) 驱动应用渲染循环(若已加载)
    try:
        app_loop()
    except BaseException as e:
        print("[loader] app loop error:", e)
    time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg

            print_error_msg(e)
        except Exception:
            print("run error:", e)
