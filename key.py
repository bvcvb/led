import M5
from M5 import *
from module import FacesKeyboard3Module
import machine
from machine import Pin


# 应用版本号 —— 显示在屏幕上, 便于核对设备运行的是哪个版本
APP_VERSION = "v1.0.3"           # 此次: IRQ 中断采集 + 可见重启按钮
# 触控重启按钮的屏幕区域(横屏 CoreS3 320x240; 放右上角)
RESTART_BTN_X = 250              # 按钮区域左边界
RESTART_BTN_Y = 6                # 按钮区域上边界
RESTART_BTN_W = 66               # 按钮区域宽
RESTART_BTN_H = 40               # 按钮区域高


kb = None
mode = "NORMAL"
line = ""

lbl_mode = None
lbl_key = None
lbl_line = None
lbl_version = None

# 用 IRQ 中断捕获的按键队列: 中断里入队, 主循环里逐个取出处理, 避免快速连按丢键
key_queue = []


def safe_set_led(left, right):
    # set_led() only works in DIRECT mode; guard against firmware quirks.
    try:
        kb.set_led(left, right)
    except Exception:
        pass


def on_key(arg):
    global line
    # 回调绝不允许抛异常: 一旦抛错会中断队列处理。UI/日志全部包进 try/except。
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


def _key_irq_handler(pin):
    """IRQ 边沿触发回调: 在按键电平跳变的瞬间入队, 不让主循环错过快速连按。

    注意: 中断回调里不能做阻塞操作/分配内存。这里只读 I2C 键码并入队(短)。
    """
    try:
        data = kb._read_key()
        if data is not None:
            key_queue.append(data)
            if len(key_queue) > 64:      # 限制队列长度, 避免内存膨胀
                key_queue.pop(0)
    except BaseException:
        pass


def handle_touch():
    if M5.Touch.getCount() <= 0:
        return
    detail = M5.Touch.getDetail(0)
    if not detail[6]:  # wasClicked -> fresh tap only
        return

    x = M5.Touch.getX()
    y = M5.Touch.getY()

    # 右上角按钮区域 => 重启设备
    if (RESTART_BTN_X <= x <= RESTART_BTN_X + RESTART_BTN_W
            and RESTART_BTN_Y <= y <= RESTART_BTN_Y + RESTART_BTN_H):
        print("[app] restart triggered by touch (x=%d,y=%d)" % (x, y))
        machine.reset()
        return

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

    # 版本号: 放左侧, 文本短避免超宽截断
    lbl_version = Widgets.Label(APP_VERSION, 6, 6, 1.0,
                                0x00FFFF, 0x222222, Widgets.FONTS.DejaVu18)

    # 可见的重启按钮: 右上角, 用矩形 + 字母"R"标出
    M5.Lcd.fillRect(RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_W, RESTART_BTN_H,
                    0xCC0000)
    M5.Lcd.drawRect(RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_W, RESTART_BTN_H,
                    0xFFFFFF)
    Widgets.Label("R", RESTART_BTN_X + 26, RESTART_BTN_Y + 10, 1.0,
                  0xFFFFFF, 0xCC0000, Widgets.FONTS.Montserrat18)

    lbl_mode = Widgets.Label("MODE: NORMAL (char)", 3, 42, 1.0,
                             0x00FF00, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_key = Widgets.Label("KEY: --", 3, 78, 1.0,
                            0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_line = Widgets.Label("(type on the keyboard)", 3, 114, 1.0,
                             0xFFFF00, 0x222222, Widgets.FONTS.DejaVu18)
    Widgets.Label("TAP R: restart  |  TAP bottom: switch", 3, 200, 1.0,
                  0xFFFFFF, 0x0055AA, Widgets.FONTS.DejaVu18)

    kb = FacesKeyboard3Module(address=0x08)
    kb.set_callback(on_key)
    kb.set_mode(FacesKeyboard3Module.NORMAL)
    # 用 IRQ 中断捕获按键(边沿触发), 彻底解决快速连按丢键
    try:
        kb._irq.irq(trigger=Pin.IRQ_FALLING, handler=_key_irq_handler)
        print("[app] key IRQ enabled")
    except BaseException as e:
        print("[app] key IRQ setup failed:", e)


def loop():
    M5.update()
    # 从 IRQ 采集的队列中逐个取出按键处理(不丢快速连按)
    try:
        while key_queue:
            data = key_queue.pop(0)
            if len(data) == 2 and data[0] == 0x0D and data[1] == 0x0A:
                on_key(KEY_ENTER)
            else:
                on_key(data[0])
    except BaseException as e:
        print("[app] queue process error:", e)
    handle_touch()
