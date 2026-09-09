import M5
from M5 import *
from module import FacesKeyboard3Module


# 应用版本号 —— 显示在屏幕上, 便于核对设备运行的是哪个版本
APP_VERSION = "v1.2.0"           # UI 基础优化: 分区布局 + 状态彩色高亮
# UI 颜色
BANNER_BG = 0x000080            # 顶部标题栏背景(深蓝)
BANNER_FG = 0xFFFFFF            # 标题栏文字
MAIN_BG = 0x1E1E1E              # 主内容区背景(浅灰)
HINT_BG = 0x003366              # 底部提示栏背景
MODE_NORM_FG = 0x00FF00         # NORMAL 文字(绿)
MODE_DIRECT_FG = 0xFFA500       # DIRECT 文字(橙)
TXT_FG = 0xFFFFFF
LINE_FG = 0xFFFF00
VER_FG = 0x808080               # 版本号(灰, 低调)


kb = None
mode = "NORMAL"
line = ""

lbl_mode = None
lbl_key = None
lbl_line = None
lbl_version = None

# 键盘控制键的 ASCII 码(与 FacesKeyboard3 一致)
KEY_BACKSPACE = 0x08
KEY_ENTER = 0x0D
KEY_DELETE = 0x7F


def safe_set_led(left, right):
    # set_led() only works in DIRECT mode; guard against firmware quirks.
    try:
        kb.set_led(left, right)
    except Exception:
        pass


def on_key(arg):
    global line
    # 回调绝不允许抛异常: micropython.schedule 的回调一旦抛错会破坏调度器,
    # 导致后续按键回调全部丢失。UI/日志全部包进 try/except。
    try:
        if mode == "NORMAL":
            code = int(arg)
            if code == KEY_BACKSPACE:
                line = line[:-1]
                lbl_key.setText("KEY: BACKSPACE")
            elif code == KEY_ENTER:
                line += "\n"
                lbl_key.setText("KEY: ENTER")
            elif code == KEY_DELETE:
                line = line[:-1]
                lbl_key.setText("KEY: DELETE")
            elif 32 <= code <= 126:
                line += chr(code)
                lbl_key.setText("KEY: '%s' (0x%02X)" % (chr(code), code))
            else:
                lbl_key.setText("KEY: 0x%02X" % code)

            if line:
                lbl_line.setText("> " + line[-36:].replace("\n", " | "))
            else:
                lbl_line.setText("(type on the keyboard)")
        else:
            # DIRECT mode: callback receives a tuple of pressed key names.
            names = arg
            if names:
                lbl_key.setText("KEYS: " + str(names))
                safe_set_led(True, True)
            else:
                lbl_key.setText("KEYS: (none)")
                safe_set_led(False, False)

        print("key event:", mode, repr(arg))
    except BaseException as e:
        # 仅打印, 绝不再抛, 保住 schedule 调度器
        print("[on_key] handler error:", e)


def switch_mode():
    global mode, line
    line = ""
    if mode == "NORMAL":
        kb.set_mode(FacesKeyboard3Module.DIRECT)
        mode = "DIRECT"
        lbl_mode.setText("MODE: DIRECT (matrix)")
        # 用 setColor 改文字颜色(固件 Label 支持的确定方法)
        try:
            lbl_mode.setColor(MODE_DIRECT_FG)
        except BaseException:
            pass
        lbl_key.setText("KEYS: --")
        lbl_line.setText("(press keys, see raw names)")
        safe_set_led(False, False)
    else:
        safe_set_led(False, False)  # still in DIRECT here, valid
        kb.set_mode(FacesKeyboard3Module.NORMAL)
        mode = "NORMAL"
        lbl_mode.setText("MODE: NORMAL (char)")
        try:
            lbl_mode.setColor(MODE_NORM_FG)
        except BaseException:
            pass
        lbl_key.setText("KEY: --")
        lbl_line.setText("(type on the keyboard)")


def handle_touch():
    if M5.Touch.getCount() <= 0:
        return
    detail = M5.Touch.getDetail(0)
    if not detail[6]:  # wasClicked -> fresh tap only
        return

    # 底部触摸 => 切换 NORMAL / DIRECT (重启已统一到 menu, 这里不再做)
    if M5.Touch.getY() >= 190:
        switch_mode()


def setup():
    global kb, lbl_mode, lbl_key, lbl_line, lbl_version
    M5.begin()
    Widgets.setRotation(1)

    # --- 分区布局: 顶部标题栏 + 主内容区 + 底部提示栏 ---
    Widgets.fillScreen(MAIN_BG)
    # 顶部标题栏(深蓝)
    M5.Lcd.fillRect(0, 0, 320, 38, BANNER_BG)
    Widgets.Label("Faces Keyboard3 Test", 8, 8, 1.0,
                  BANNER_FG, BANNER_BG, Widgets.FONTS.Montserrat18)
    # 底部提示栏
    M5.Lcd.fillRect(0, 190, 320, 50, HINT_BG)
    Widgets.Label("TAP bottom: switch mode (restart in menu)",
                  3, 208, 1.0, 0xFFFFFF, HINT_BG, Widgets.FONTS.DejaVu18)

    # 版本号: 左下角, 小号, 低调
    lbl_version = Widgets.Label(APP_VERSION, 8, 196, 0.8,
                                VER_FG, HINT_BG, Widgets.FONTS.DejaVu12)

    # --- 主内容区 ---
    lbl_mode = Widgets.Label("MODE: NORMAL (char)", 8, 48, 1.2,
                             MODE_NORM_FG, MAIN_BG, Widgets.FONTS.DejaVu18)
    lbl_key = Widgets.Label("KEY: --", 8, 96, 2.0,
                            TXT_FG, MAIN_BG, Widgets.FONTS.Montserrat18)
    lbl_line = Widgets.Label("(type on the keyboard)", 8, 140, 1.0,
                             LINE_FG, MAIN_BG, Widgets.FONTS.DejaVu18)

    kb = FacesKeyboard3Module(address=0x08)
    kb.set_callback(on_key)
    kb.set_mode(FacesKeyboard3Module.NORMAL)


def loop():
    M5.update()
    # 直接轮询键盘读取(不走 kb.tick() 的 schedule 队列), 每帧读到一个立即处理,
    # 避免 schedule 队列覆盖导致的按键丢失。
    data = kb._read_key()
    if data is not None:
        # NORMAL 模式: _read_key 返回 1 字节; ENTER 会返回 b"\r\n"
        if len(data) == 2 and data[0] == 0x0D and data[1] == 0x0A:
            on_key(KEY_ENTER)
        else:
            on_key(data[0])
    handle_touch()
