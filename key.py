import M5
from M5 import *
from module import FacesKeyboard3Module


kb = None
mode = "NORMAL"
line = ""

lbl_mode = None
lbl_key = None
lbl_line = None

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
    if M5.Touch.getY() >= 190:
        switch_mode()


def setup():
    global kb, lbl_mode, lbl_key, lbl_line
    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x222222)

    Widgets.Title("Faces Keyboard3 Test", 3, 0xFFFFFF, 0x0000FF,
                  Widgets.FONTS.Montserrat18)

    lbl_mode = Widgets.Label("MODE: NORMAL (char)", 3, 42, 1.0,
                             0x00FF00, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_key = Widgets.Label("KEY: --", 3, 78, 1.0,
                            0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    lbl_line = Widgets.Label("(type on the keyboard)", 3, 114, 1.0,
                             0xFFFF00, 0x222222, Widgets.FONTS.DejaVu18)
    Widgets.Label("TAP HERE: switch NORMAL / DIRECT", 3, 200, 1.0,
                  0xFFFFFF, 0x0055AA, Widgets.FONTS.DejaVu18)

    kb = FacesKeyboard3Module(address=0x08)
    kb.set_callback(on_key)
    kb.set_mode(FacesKeyboard3Module.NORMAL)


def loop():
    M5.update()
    kb.tick()
    handle_touch()


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")
