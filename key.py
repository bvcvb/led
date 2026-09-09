import M5
from M5 import *
from module import FacesKeyboard3Module
import machine


# 应用版本号 —— 显示在屏幕上, 便于核对设备运行的是哪个版本
APP_VERSION = "v1.0.2"
# 触控重启的判定阈值(横屏方向, y 越大越靠下; 用 x 靠右的一角)
RESTART_TOUCH_X = 280           # 触摸 x >= 此值 且 y 在下方 => 重启
RESTART_TOUCH_Y = 120


kb = None
mode = "NORMAL"
line = ""

lbl_mode = None
lbl_key = None
lbl_line = None
lbl_version = None

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
        lbl_key.setText("KEYS: --")
        lbl_line.setText("(press keys, see raw names)")
        safe_set_led(False, False)
    else:
        safe_set_led(False, False)  # still in DIRECT here, valid
        kb.set_mode(FacesKeyboard3Module.NORMAL)
        mode = "NORMAL"
        lbl_mode.setText("MODE: NORMAL (char)")
        lbl_key.setText("KEY: --")
        lbl_line.setText("(type on the keyboard)")


def handle_touch():
    if M5.Touch.getCount() <= 0:
        return
    detail = M5.Touch.getDetail(0)
    if not detail[6]:  # wasClicked -> fresh tap only
        return

    x = M5.Touch.getX()
    y = M5.Touch.getY()

    # 右上角触摸 => 重启设备 (快捷方式, 不干扰键盘输入)
    if x >= RESTART_TOUCH_X and y >= RESTART_TOUCH_Y:
        print("[app] restart triggered by touch (x=%d,y=%d)" % (x, y))
        machine.reset()

    # 底部触摸 => 切换 NORMAL / DIRECT
    if y >= 190:
        switch_mode()


def setup():
    global kb, lbl_mode, lbl_key, lbl_line, lbl_version
    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x222222)

    Widgets.Title("Faces Keyboard3 Test", 3, 0xFFFFFF, 0x0000FF,
                  Widgets.FONTS.Montserrat18)

    # 版本号: 放右上角, 文本短避免超宽截断
    lbl_version = Widgets.Label(APP_VERSION, 200, 6, 1.0,
                                0x00FFFF, 0x222222, Widgets.FONTS.DejaVu18)

    lbl_mode = Widgets.Label("MODE: NORMAL (char)", 3, 42, 1.0,
                             0x00FF00, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_key = Widgets.Label("KEY: --", 3, 78, 1.0,
                            0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_line = Widgets.Label("(type on the keyboard)", 3, 114, 1.0,
                             0xFFFF00, 0x222222, Widgets.FONTS.DejaVu18)
    Widgets.Label("TAP bottom: switch  |  TAP top-right: restart", 3, 200, 1.0,
                  0xFFFFFF, 0x0055AA, Widgets.FONTS.DejaVu18)

    kb = FacesKeyboard3Module(address=0x08)
    kb.set_callback(on_key)
    kb.set_mode(FacesKeyboard3Module.NORMAL)


def loop():
    M5.update()
    # 直接轮询键盘读取(而非 kb.tick() 的 schedule 队列), 每帧读到一个立即处理,
    # 从根源避免 schedule 队列覆盖导致的按键丢失。
    data = kb._read_key()
    if data is not None:
        # NORMAL 模式: _read_key 返回 1 字节; ENTER 会返回 b"\r\n"
        if len(data) == 2 and data[0] == 0x0D and data[1] == 0x0A:
            on_key(KEY_ENTER)
        else:
            on_key(data[0])
    handle_touch()
