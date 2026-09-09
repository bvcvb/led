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
APPS_URL = "https://raw.githubusercontent.com/bvcvb/led/master/src/apps.json"
BIN_URL = "https://raw.githubusercontent.com/bvcvb/led/master/src/"   # 应用 .py 所在目录
FETCH_TIMEOUT_MS = 10000
POLL_CHECK_MS = 3000         # 菜单展示期: 周期性拉 apps.json 检查版本(毫秒)
ROW_Y0 = 80                 # 第一行应用列表的 y
ROW_STEP = 50               # 每行间距
# ------------------------------------------------------------------------

apps = []                   # [{name,file,version}, ...]
_sel_ns = None
_sel_ready = False
_last_apps = None
_loaded_ver = {}            # file -> 已加载应用的 version(用于判断是否需重新下载)
_poll_at = 0                # 下次检查版本的时间点(ticks_ms)
_redraw = False             # 列表内容变化, 需要重绘


def _poll_check():
    """菜单展示期周期性拉 apps.json; 内容变化则重绘列表(显示最新版本)。"""
    global _poll_at, _redraw
    now = time.ticks_ms()
    if time.ticks_diff(now, _poll_at) < 0:
        return
    _poll_at = now + POLL_CHECK_MS
    if fetch_apps():
        _redraw = True


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


def _version_of(file):
    """返回 apps 列表中该 file 的声明版本, 找不到返回 None。"""
    for it in apps:
        if it.get("file") == file:
            return it.get("version")
    return None


def fetch_apps():
    """拉取 apps.json(版本源), 更新 apps 列表。返回是否内容有变化。"""
    global apps, _last_apps
    text = _get(APPS_URL)
    if text is None or text == _last_apps:
        return False
    _last_apps = text
    apps = _parse_apps(text)
    return True


def run_app(file):
    """运行指定应用。仅在版本变化或未加载时下载 .py, 否则复用已加载的命名空间。"""
    global _sel_ns, _sel_ready
    ver = _version_of(file)
    need_dl = ver != _loaded_ver.get(file)
    if not need_dl and _sel_ns is not None:
        # 版本没变且已加载过 -> 复用, 不下载
        print("[menu] reuse app:", file, "ver", ver)
        _sel_ready = True
        if "setup" in _sel_ns:
            _sel_ns["setup"]()
        return True

    text = _get(BIN_URL + file)
    if text is None:
        print("[menu] fetch app failed:", file)
        return False
    try:
        ns = {"__name__": "__app__"}
        exec(text, ns)
        _sel_ns = ns
        _selected_file = file
        _loaded_ver[file] = ver or "0"
        _sel_ready = True
        if "setup" in ns:
            ns["setup"]()
        print("[menu] run app:", file, "ver", ver)
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
        ver = it.get("version")
        label = "%s   v%s" % (name, ver) if ver else name
        Widgets.Label(label, 3, y, 1.0,
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
            # 点选前先拉一次 apps.json, 保证版本对比基于最新清单
            fetch_apps()
            run_app(file)


def loop():
    global _sel_ready, _redraw
    if _sel_ready and _sel_ns is not None:
        try:
            if "loop" in _sel_ns:
                _sel_ns["loop"]()
        except BaseException as e:
            print("[menu] app loop error:", e)
        return
    M5.update()
    # 菜单展示期: 周期性拉 apps.json 检查版本
    _poll_check()
    if _redraw:
        _redraw = False
        _render_list()
    _handle_touch()
    time.sleep_ms(10)
