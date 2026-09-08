# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Copyright (c) 2024. 本文件为设备端引导程序 (CoreS3 + UIFlow2 固件)
#
# loader.py — 设备端「主动拉取」引导程序
#
# 作用:
#   作为设备 main.py 部署后, 开机(此时 UIFlow2 固件已自动连 WiFi)周期性
#   requests2.get(<gist raw url>) 拉取代码并 exec 运行。
#   这样 dsh 通过 push.py 更新 gist 后, 设备下个周期自动拉到新版。
#
# 用法:
#   1) 把本文件作为 main.py 部署到设备 (见 ./docs/device-flash-notes.md)
#   2) 修改下面的 FETCH_URL 为 push.py 输出的 raw 地址
#   3) 修改 POLL_INTERVAL_MS 控制轮询间隔

import time
import gc
import requests2

# ---- 配置区 -------------------------------------------------------------
FETCH_URL = "https://gist.githubusercontent.com/<user>/<gist_id>/raw/key.py"
POLL_INTERVAL_MS = 5000          # 轮询间隔(毫秒)
MAX_INLINE_BYTES = 20 * 1024     # 超过此大小不做 inline 提示(仅日志用)
FETCH_TIMEOUT_MS = 10000         # 单次 GET 超时(毫秒)
# ------------------------------------------------------------------------

last_code = None


def fetch_code():
    """拉取 Gist 内容, 失败返回 None(不抛异常)。"""
    global last_code
    try:
        resp = requests2.get(FETCH_URL, timeout=FETCH_TIMEOUT_MS)
        text = resp.text
        if text is None:
            text = ""
        # 内容无变化则返回 None 让上层跳过
        if text == last_code:
            return None
        last_code = text
        return text
    except BaseException as e:
        print("[loader] GET failed:", e)
        return None


def run_code(text):
    """exec 拉到的代码。捕获异常, 不让引导程序崩溃。"""
    try:
        # 在独立的命名空间执行, 避免与 loader 自身符号冲突
        ns = {"__name__": "__app__"}
        exec(text, ns)
    except BaseException as e:
        print("[loader] run error:", e)
    finally:
        gc.collect()


def setup():
    # 简单自检: 打印设备已启动 + 目标 URL
    print("[loader] started, polling:", FETCH_URL)


def loop():
    code = fetch_code()
    if code:
        print("[loader] got new code, (%d bytes)" % len(code))
        run_code(code)
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
            print("please update to latest firmware")
