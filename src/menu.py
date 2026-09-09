# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Copyright (c) 2024. 本文件为设备端「应用选择器」(CoreS3 + UIFlow2 固件)
#
# menu.py — 应用菜单: 列出仓库里的应用, 点击选中, 再点击运行
#
# 角色: 由 device/loader.py 拉取并作为主应用运行。它负责:
#   1. 请求仓库 src/apps.json, 拿到应用清单(含 version)
#   2. 屏幕上列出应用, 首次点击高亮选中, 再次点击运行
#   3. 运行前按 version 对比, 版本变了才下载 .py, 否则复用
#
# 性能注意:
#   - 选中不整屏重建(仅更新受影响行), 保证点击响应快
#   - 下载用短超时 + 一次性动作, 不长期阻塞主循环导致"没反应"
#   - 菜单展示期低频拉 apps.json, 点选时不再二次网络请求

import time

import M5
from M5 import Widgets
import machine

import requests2

# ---- 配置区 -------------------------------------------------------------
MENU_VERSION = "v1.3.0"          # menu 自身版本号
APPS_URL = "https://raw.githubusercontent.com/bvcvb/led/master/src/apps.json"
BIN_URL = "https://raw.githubusercontent.com/bvcvb/led/master/src/"   # 应用 .py 所在目录
FETCH_TIMEOUT_MS = 4000          # 网络超时(短), 避免长时间卡死主循环
POLL_CHECK_MS = 5000             # 菜单展示期: 周期性拉 apps.json 检查版本(毫秒)
ROW_Y0 = 80                      # 第一行应用列表的 y
ROW_STEP = 50                    # 每行间距
HINT_Y = 200                     # 底部提示行 y
# 重启按钮区域(右上角)
RESTART_BTN_X = 250
RESTART_BTN_Y = 6
RESTART_BTN_W = 66
RESTART_BTN_H = 40
# 颜色
C_BG = 0x222222
C_SEL_BG = 0x00FF00              # 选中行背景
C_SEL_FG = 0x000000              # 选中行文字
C_NORM_FG = 0xFFFF00             # 普通行文字
C_RESTART_FG = 0xFF5555          # 重启条目文字(偏红, 醒目)
# ------------------------------------------------------------------------

apps = []                   # [{name,file,version}, ...]
_sel_ns = None
_sel_ready = False
_last_apps = None
_loaded_ver = {}            # file -> 已加载应用的 version(用于判断是否需重新下载)
_poll_at = 0                # 下次检查版本的时间点(ticks_ms)
_cursor = -1                # 当前选中的行号(-1 表示未选中)
_rows = []                  # 每行的 Label 对象 [ [label_obj, idx], ... ]


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
    for it in apps:
        if it.get("file") == file:
            return it.get("version")
    return None


def fetch_apps():
    """拉取 apps.json, 更新 apps 清单。返回是否内容变化。"""
    global apps, _last_apps
    text = _get(APPS_URL)
    if text is None or text == _last_apps:
        return False
    _last_apps = text
    apps = _parse_apps(text)
    return True


def _row_label(idx):
    """构造第 idx 行的显示字符串。"""
    it = apps[idx]
    name = it.get("name", it.get("file", "?"))
    ver = it.get("version")
    return ("%s   v%s" % (name, ver)) if ver else name


def _render_list():
    """整屏绘制菜单列表(仅在需要时调用一次)。"""
    global _rows
    Widgets.fillScreen(C_BG)
    Widgets.Title("App Menu", 3, 0xFFFFFF, 0x0000FF,
                  Widgets.FONTS.Montserrat18)

    # 右上角重置按钮(固定): 点它重启设备
    M5.Lcd.fillRect(RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_W, RESTART_BTN_H,
                    0xCC0000)
    M5.Lcd.drawRect(RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_W, RESTART_BTN_H,
                    0xFFFFFF)
    Widgets.Label("R", RESTART_BTN_X + 26, RESTART_BTN_Y + 10, 1.0,
                  0xFFFFFF, 0xCC0000, Widgets.FONTS.Montserrat18)

    _rows = []
    fetch_apps()
    rows = apps if apps else []
    if not rows:
        Widgets.Label("(no apps found)", 3, ROW_Y0, 1.0,
                      0xFFFFFF, C_BG, Widgets.FONTS.DejaVu18)
        return
    y = ROW_Y0
    for i in range(len(rows)):
        lbl = Widgets.Label("  " + _row_label(i), 3, y, 1.0,
                            0xFFFFFF, C_BG, Widgets.FONTS.DejaVu18)
        _rows.append(lbl)
        y += ROW_STEP
    Widgets.Label("tap to select | tap again to run | R: restart", 3, HINT_Y, 1.0,
                  0xFFFFFF, 0x0055AA, Widgets.FONTS.DejaVu18)


def _refresh_row(idx):
    """重绘第 idx 行(选中/未选中), 不再整屏重建。"""
    if idx < 0 or idx >= len(_rows):
        return
    lbl = _rows[idx]
    text = _row_label(idx)
    if idx == _cursor:
        lbl.set_text_color(C_SEL_FG, C_SEL_BG)
        lbl.setText("> " + text)
    else:
        lbl.set_text_color(0xFFFFFF, C_BG)
        lbl.setText("  " + text)


def _render_immediate_or_schedule():
    """选中变化后: 重绘旧选中行(刷回未选中) 和 新选中行(高亮)。"""
    for i in range(len(_rows)):
        _refresh_row(i)


def run_app(file):
    """运行指定应用。版本变化或未加载才下载 .py; 否则复用。"""
    global _sel_ns, _sel_ready, _loaded_ver
    ver = _version_of(file)
    need_dl = ver != _loaded_ver.get(file)
    if not need_dl and _sel_ns is not None:
        print("[menu] reuse app:", file, "ver", ver)
        _sel_ready = True
        if "setup" in _sel_ns:
            _sel_ns["setup"]()
        return True

    print("[menu] downloading:", file)
    text = _get(BIN_URL + file)
    if text is None:
        print("[menu] fetch app failed:", file)
        return False
    try:
        ns = {"__name__": "__app__"}
        exec(text, ns)
        _sel_ns = ns
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


def _handle_touch():
    global _cursor
    if M5.Touch.getCount() <= 0:
        return
    detail = M5.Touch.getDetail(0)
    if not detail[6]:        # wasClicked -> 仅点击触发(避免拖动误触)
        return
    x = M5.Touch.getX()
    y = M5.Touch.getY()

    # 右上角 R 按钮: 重启设备
    if (RESTART_BTN_X <= x <= RESTART_BTN_X + RESTART_BTN_W
            and RESTART_BTN_Y <= y <= RESTART_BTN_Y + RESTART_BTN_H):
        print("[menu] restart triggered (x=%d,y=%d)" % (x, y))
        machine.reset()
        return

    if not apps or y < ROW_Y0:
        return
    idx = (y - ROW_Y0) // ROW_STEP
    if 0 <= idx < len(apps):
        if idx == _cursor:
            file = apps[idx].get("file")
            if file:
                run_app(file)
        else:
            _cursor = idx
            _render_immediate_or_schedule()


def setup():
    M5.begin()
    Widgets.setRotation(1)
    _render_list()


def loop():
    global _sel_ready, _poll_at
    if _sel_ready and _sel_ns is not None:
        try:
            if "loop" in _sel_ns:
                _sel_ns["loop"]()
        except BaseException as e:
            print("[menu] app loop error:", e)
        return
    M5.update()
    # 菜单展示期低频拉 apps.json 检查版本(不阻塞太久)
    now = time.ticks_ms()
    if time.ticks_diff(now, _poll_at) >= 0:
        _poll_at = now + POLL_CHECK_MS
        if apps and fetch_apps():
            _render_list()
    _handle_touch()
    time.sleep_ms(10)
