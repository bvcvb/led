# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Copyright (c) 2024. 本文件为设备端「应用选择器」(CoreS3 + UIFlow2 固件)
#
# menu.py — 应用菜单: 列出仓库里的应用, 点选后下载并运行
#
# 角色: 由 device/loader.py 拉取并作为主应用运行。它负责:
#   1. 请求仓库根目录下的 apps.json, 拿到应用清单
#   2. 在屏幕上列出应用条目, 用户点选
#   3. 点选后拉取该应用的 .py, exec 并运行(setup/loop)
#
# ⚠️ 与 loader 的关系: 本文件只提供 setup()/loop(), 由 loader 的 while True 调度。
#    运行选中应用时, 每轮把执行权交给该应用的 loop()。

import time

import M5
from M5 import Widgets

import requests2

# ---- 配置区 -------------------------------------------------------------
APPS_URL = "https://raw.githubusercontent.com/bvcvb/led/master/apps.json"
BIN_URL = "https://raw.githubusercontent.com/bvcvb/led/master/"   # 应用 .py 所在目录
FETCH_TIMEOUT_MS = 10000
ROW_Y0 = 80                 # 第一行应用列表的 y
ROW_STEP = 50               # 每行间距
# ------------------------------------------------------------------------

apps = []                   # [{name,file}, ...]
_sel_ns = None
_sel_ready = False
_last_apps = None


def _get(url):
    try:
        return requests2.get(url, timeout=FETCH_TIMEOUT_MS).text
    except BaseException as e:
        print("[menu] GET failed:", e)
        return None


def _parse_apps(text):
    if text is None:
        return []
    try:
        data = json_loads(text)
        return data.get("apps", [])
    except BaseException as e:
        print("[menu] parse apps.json error:", e)
        return []


def _load_json():
    try:
        import json
        return json.loads
    except Exception:
        import ujson
        return ujson.loads


json_loads = _load_json()


def fetch_apps():
    global apps, _last_apps
    text = _get(APPS_URL)
    if text is None or text == _last_apps:
        return
    _last_apps = text
    apps = _parse_apps(text)


def run_app(file):
    global _sel_ns, _sel_ready
    text = _get(BIN_URL + file)
    if text is None:
        print("[menu] fetch app failed:", file)
        return False
    try:
        ns = {"__name__": "__app__"}
        exec(text, ns)
        _sel_ns = ns
        _sel_ready = True
        if "setup" in ns:
            ns["setup"]()
        print("[menu] running app:", file)
        return True
    except BaseException as e:
        print("[menu] app load error:", e)
        _sel_ready = False
        return False


def setup():
    M5.begin()
    Widgets.setRotation(1)
    _render_list()


def _render_list():
    Widgets.fillScreen(0x222222)
    Widgets.Title("App Menu", 3, 0xFFFFFF, 0x0000FF,
                  Widgets.FONTS.Montserrat18)
    fetch_apps()
    rows = apps if apps else []
    if not rows:
        Widgets.Label("(no apps found)", 3, ROW_Y0, 1.0,
                      0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
        return
    y = ROW_Y0
    for it in rows:
        name = it.get("name", it.get("file", "?"))
        Widgets.Label(name, 3, y, 1.0,
                      0xFFFF00, 0x222222, Widgets.FONTS.DejaVu18)
        y += ROW_STEP


def _handle_touch():
    if M5.Touch.getCount() <= 0:
        return
    detail = M5.Touch.getDetail(0)
    if not detail[6]:
        return
    y = M5.Touch.getY()
    if not apps or y < ROW_Y0:
        return
    idx = (y - ROW_Y0) // ROW_STEP
    if 0 <= idx < len(apps):
        file = apps[idx].get("file")
        if file:
            run_app(file)


def loop():
    if _sel_ready and _sel_ns is not None:
        try:
            if "loop" in _sel_ns:
                _sel_ns["loop"]()
        except BaseException as e:
            print("[menu] app loop error:", e)
        return
    M5.update()
    _handle_touch()
    time.sleep_ms(10)
