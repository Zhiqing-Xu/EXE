# -*- coding: utf-8 -*-
# Windows-only automation (SendInput) with cancellable worker thread and coord mode.
import sys, time, threading, ctypes
from ctypes import wintypes
import keyboard  # pip install keyboard
from typing import Optional

# =========================
# Logging & Utilities
# =========================
def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# Cancellable sleep (for responsive STOP)
def cancellable_sleep(sec: float, stop_event: threading.Event, tick: float = 0.02) -> bool:
    end = time.time() + sec
    while not stop_event.is_set():
        rem = end - time.time()
        if rem <= 0:
            return True
        time.sleep(min(tick, rem))
    return False

# Console countdown/loading bar
def sleep_with_progress(total_sec: float, label: str, stop_event: threading.Event):
    start = time.time()
    width = 32
    tick = 0.1
    while not stop_event.is_set():
        elapsed = time.time() - start
        if elapsed >= total_sec:
            break
        pct = min(1.0, elapsed / total_sec)
        filled = int(width * pct)
        bar = "[" + "=" * filled + ">" + "." * max(0, width - filled - 1) + "]"
        remaining = max(0, int(total_sec - elapsed))
        mm, ss = divmod(remaining, 60)
        sys.stdout.write(f"\r{label} {bar} {int(pct*100):3d}%  {mm:02d}:{ss:02d} remaining")
        sys.stdout.flush()
        if stop_event.wait(tick):
            break
    sys.stdout.write("\r" + " " * (len(label) + width + 28) + "\r")
    sys.stdout.flush()
    log(f"{label} {'done.' if not stop_event.is_set() else 'interrupted.'}")

# =========================
# Win32 Input (SendInput)
# =========================
user32 = ctypes.windll.user32

# Correct ULONG_PTR for 32/64-bit
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

# INPUT types
INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Keyboard flags
KEYEVENTF_KEYUP    = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Mouse flags
MOUSEEVENTF_MOVE      = 0x0001
MOUSEEVENTF_LEFTDOWN  = 0x0002
MOUSEEVENTF_LEFTUP    = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010
MOUSEEVENTF_ABSOLUTE  = 0x8000  # (not used; we use SetCursorPos for precision)

# Structures
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",       wintypes.WORD),
        ("wScan",     wintypes.WORD),
        ("dwFlags",   wintypes.DWORD),
        ("time",      wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",        wintypes.LONG),
        ("dy",        wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags",   wintypes.DWORD),
        ("time",      wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",     wintypes.DWORD),
        ("wParamL",  wintypes.WORD),
        ("wParamH",  wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii",   INPUT_UNION),
    ]

SendInput = user32.SendInput

# Cursor & key state (no pyautogui)
POINT = wintypes.POINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype  = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype  = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype  = ctypes.c_short
VK_LBUTTON = 0x01

def get_pos():
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError(ctypes.get_last_error())
    return pt.x, pt.y

def set_pos(x: int, y: int):
    if not user32.SetCursorPos(int(x), int(y)):
        raise ctypes.WinError(ctypes.get_last_error())

# Mouse events
def mouse_event(flags, dx=0, dy=0, data=0):
    pkt = INPUT(type=INPUT_MOUSE, ii=INPUT_UNION(mi=MOUSEINPUT(dx, dy, data, flags, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))

def left_click():
    mouse_event(MOUSEEVENTF_LEFTDOWN); time.sleep(0.1); mouse_event(MOUSEEVENTF_LEFTUP)

def right_click():
    mouse_event(MOUSEEVENTF_RIGHTDOWN); time.sleep(0.1); mouse_event(MOUSEEVENTF_RIGHTUP)

# Drift-free relative click: move absolutely based on current pos
def click_below_current(offset_y=80, button="left", return_cursor=True, stop_event=None):
    x0, y0 = get_pos()
    print("x0, y0: ", x0, y0)
    if stop_event and stop_event.is_set(): return False
    set_pos(x0, y0 + offset_y)
    time.sleep(0.02)
    if button == "right": right_click()
    else:                 left_click()
    time.sleep(0.02)
    if return_cursor:
        set_pos(x0, y0)
        time.sleep(0.01)
    return True

# ---- Anchor-relative mouse helpers ----
def click_at_offset(anchor_x, anchor_y, dx, dy, stop_event=None):
    """Move to (anchor_x+dx, anchor_y+dy) and left-click once."""
    if stop_event and stop_event.is_set(): 
        return False
    set_pos(anchor_x + dx, anchor_y + dy)
    if not cancellable_sleep(0.1, stop_event): return False
    left_click()
    return True

def multi_click_at_offset(anchor_x, anchor_y, dx, dy, n, gap_sec=0.2, stop_event=None):
    """Left-click repeatedly at (anchor+offset), with gap_sec between clicks."""
    if stop_event and stop_event.is_set(): 
        return False
    set_pos(anchor_x + dx, anchor_y + dy)
    if not cancellable_sleep(0.1, stop_event): return False
    for i in range(n):
        if stop_event and stop_event.is_set():
            return False
        left_click()
        if not cancellable_sleep(gap_sec, stop_event): return False
    return True





# =========================
# Keyboard (scancodes)
# =========================
# WASD/others scancodes (US layout)
W_SCAN = 0x11
A_SCAN = 0x1E
S_SCAN = 0x1F
D_SCAN = 0x20
R_SCAN = 0x13
F_SCAN = 0x21


# Scroll
MOUSEEVENTF_WHEEL = 0x0800

def scroll_at_offset(anchor_x, anchor_y, dx, dy, amount, stop_event=None):
    """Move to (anchor_x+dx, anchor_y+dy) and scroll vertically by 'amount' (negative = down)."""
    if stop_event and stop_event.is_set():
        return False
    set_pos(anchor_x + dx, anchor_y + dy)
    time.sleep(0.02)
    pkt = INPUT(type=INPUT_MOUSE,
                ii=INPUT_UNION(mi=MOUSEINPUT(0, 0, amount, MOUSEEVENTF_WHEEL, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))
    return True

def press_scancode(scan: int):
    pkt = INPUT(type=INPUT_KEYBOARD, ii=INPUT_UNION(ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))

def release_scancode(scan: int):
    flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    pkt = INPUT(type=INPUT_KEYBOARD, ii=INPUT_UNION(ki=KEYBDINPUT(0, scan, flags, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))

def press_for(scan: int, hold_sec: float, stop_event: threading.Event) -> bool:
    if stop_event.is_set(): return False
    press_scancode(scan)
    ok = cancellable_sleep(hold_sec, stop_event)
    release_scancode(scan)
    return ok and not stop_event.is_set()

def tap_key(scan: int, tap_sec: float, stop_event: threading.Event) -> bool:
    return press_for(scan, tap_sec, stop_event)

# =========================
# Action Sequences
# =========================

def extra_moves_after_small_loop_f(stop_event):
    """
    Extra steps anchored at (anchor_x, anchor_y).
    Original absolute points and their offsets from (1346, 615):
      (677, 979)  -> dx=-669, dy=+364
      (1344, 830) -> dx= -2,  dy=+215   [15 clicks]
      (609, 553)  -> dx=-737, dy= -62
      (769, 339)  -> dx=-577, dy=-276
      (1893, 972) -> dx=+547, dy=+357   [15 clicks]
      (610, 211)  -> dx=-736, dy=-404
    """
    # 1) press W for 1.5 sec
    log("[extra] press W 1.50s")
    if not press_for(W_SCAN, 1.50, stop_event): 
        return False


    """
    # 2) press F once (quick tap)
    log("[extra] tap F 0.50s")
    if not tap_key(F_SCAN, 0.50, stop_event):
        return False
    
    if not cancellable_sleep(2, stop_event): return False

    anchor_x, anchor_y = get_pos()
    print("anchor_x, anchor_y: ", anchor_x, anchor_y)

    # 3) left click (677, 979) -> (-669, +364)
    log(f"[extra] click ({anchor_x-669}, {anchor_y+364})")
    if not click_at_offset(anchor_x, anchor_y, -669, +364, stop_event): 
        return False

    if not cancellable_sleep(2, stop_event): return False


    # 4) left click (1344, 830) x15, 0.1s gap -> (-2, +215)
    log("[extra] 15x click (anchor-2, +215), 0.1s gap")
    if not multi_click_at_offset(anchor_x, anchor_y, -2, +215, n=15, gap_sec=0.2, stop_event=stop_event):
        return False

    if not cancellable_sleep(0.2, stop_event): return False


    # 5）Category.
    log("[extra] click [Category].")

    # 5-1) Click on Pesticide Category.
    if not cancellable_sleep(1, stop_event): return False
    if not click_at_offset(anchor_x, anchor_y, -737, -62, stop_event): 
        return False
    if not cancellable_sleep(1, stop_event): return False
    if not click_at_offset(anchor_x, anchor_y, -737, -62, stop_event): 
        return False
    if not cancellable_sleep(1, stop_event): return False

    # 5-2) Click on Item Category.
    # if not click_at_offset(anchor_x, anchor_y, 658-1404, 505-724, stop_event): 
    #     return False
    # if not cancellable_sleep(2, stop_event): return False
    # if not click_at_offset(anchor_x, anchor_y, 658-1404, 505-724, stop_event): 
    #     return False


    # 6）Items.
    log("[extra] click (Item)")


    # 6-2) Lv8 Fish Food 

    if not click_at_offset(anchor_x, anchor_y, 1660-1679, 434-564, stop_event): 
        return False
    if not cancellable_sleep(1, stop_event): return False
    if not click_at_offset(anchor_x, anchor_y, 1660-1679, 434-564, stop_event): 
        return False
    if not cancellable_sleep(1, stop_event): return False
    """
    


    # 6-3) Some Rock Wall.
    """
    if not click_at_offset(anchor_x, anchor_y, 658-1404, 505-724, stop_event): 
        return False
    if not cancellable_sleep(1, stop_event): return False

    if not click_at_offset(anchor_x, anchor_y, 1270-1404, 415-724, stop_event): 
        return False
    if not cancellable_sleep(2, stop_event): return False

    if not click_at_offset(anchor_x, anchor_y, 1107-1404, 1025-724, stop_event): 
        return False
    if not cancellable_sleep(3.5, stop_event): return False
    """



    """
    # 7) left click (1893, 972) x15, 0.1s gap -> (+547, +357)
    log("[extra] 15x click (anchor+547, +357), 0.1s gap")
    if not multi_click_at_offset(anchor_x, anchor_y, +547, +357, n=15, gap_sec=0.2, stop_event=stop_event):
        return False

    if not cancellable_sleep(1, stop_event): return False


    # 8) left click (610, 211) -> (-736, -404)
    log("[extra] click (anchor-736, -404)")
    if not click_at_offset(anchor_x, anchor_y, -736, -404, stop_event): 
        return False
    
    if not cancellable_sleep(3, stop_event): return False
    """



    # 9) press S for 1.20 sec
    log("[extra] press S 1.20s")
    if not press_for(S_SCAN, 0.9, stop_event): 
        return False


    return True


def small_loop_f(stop_event: threading.Event) -> bool:
    for i in range(41):
        if stop_event.is_set(): return False
        log(f"[small_loop_f] {i+1}/28: right_click()")
        right_click()
        if not cancellable_sleep(0.02, stop_event): return False

        log(f"[small_loop_f] {i+1}/28: press W 0.41s")
        if not press_for(W_SCAN, 0.41, stop_event): return False
        if not cancellable_sleep(0.02, stop_event): return False
    return True


def small_loop_b(stop_event: threading.Event) -> bool:
    for i in range(39): #39
        if stop_event.is_set(): return False



        log(f"[small_loop_b] {i+1}/28: press F 0.10s")
        if not press_for(F_SCAN, 0.10, stop_event): return False
        if not cancellable_sleep(0.8, stop_event): return False

        log(f"[small_loop_b] {i+1}/28: click below (offset_y=400, left, stay)")
        if not click_below_current(offset_y=400, button="left", return_cursor=True, stop_event=stop_event):
            return False

        if not cancellable_sleep(0.4, stop_event): return False

        log(f"[small_loop_b] {i+1}/28: press S 0.42s")
        if not press_for(S_SCAN, 0.42, stop_event): return False
        if not cancellable_sleep(0.02, stop_event): return False
    return True

def big_loop_once(stop_event: threading.Event) -> bool:

    # NEW: extra anchored actions
    if not extra_moves_after_small_loop_f(stop_event): return False

    wait_sec = 1 # 505 + 30*60 # 505
    sleep_with_progress(wait_sec, "[big_loop_once] long wait", stop_event)
    if stop_event.is_set(): return False


    log("[big_loop_once] small_loop_b() begin")
    if not small_loop_b(stop_event): return False
    log("[big_loop_once] small_loop_b() done")


    log("[big_loop_once] sleep 1.0s")
    if not cancellable_sleep(1.0, stop_event): return False


    steps = [
        ("press W 0.45s", lambda: press_for(W_SCAN, 0.45, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        
        ("tap R 0.20s",   lambda: tap_key(R_SCAN, 0.20, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        ("press W 3.30s", lambda: press_for(W_SCAN, 3.30, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        ("tap R 0.20s",   lambda: tap_key(R_SCAN, 0.20, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        ("press W 3.30s", lambda: press_for(W_SCAN, 3.30, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        ("tap R 0.20s",   lambda: tap_key(R_SCAN, 0.20, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),

        ("press S 3.60s", lambda: press_for(S_SCAN, 7.20, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
        ("press W 0.20s", lambda: press_for(W_SCAN, 0.20, stop_event)),
        ("sleep 0.5s",    lambda: cancellable_sleep(0.5, stop_event)),
    ]
    for name, fn in steps:
        if stop_event.is_set(): return False
        log(f"[big_loop_once] {name}")
        if not fn(): return False


    log("[big_loop_once] small_loop_f() begin")
    if not small_loop_f(stop_event): return False
    log("[big_loop_once] small_loop_f() done")


    return True

def worker(stop_event: threading.Event):
    while not stop_event.is_set():
        if not big_loop_once(stop_event):
            break

# =========================
# Main (Hotkeys & Modes)
# =========================
if __name__ == "__main__":
    keyboard_status = 0   # 0=stopped, 1=running, 2=coord mode
    worker_thread = None
    stop_event = threading.Event()
    prev_lmb_down = False

    log("Controls: '.+/' = START, '[+]' = STOP, '9+0' = COORD MODE")

    while True:
        try:
            # Hotkeys (your exact semantics)
            if keyboard.is_pressed('[+]'):
                if keyboard_status != 0: log("STOP requested")
                keyboard_status = 0

            elif keyboard.is_pressed('.+/'):
                if keyboard_status != 1: log("START requested")
                keyboard_status = 1

            elif (keyboard.is_pressed('9+0')):
                if keyboard_status != 2: log("COORD MODE requested")
                keyboard_status = 2

            elif (keyboard.is_pressed('7+8')):
                if keyboard_status != 3: log("COORD MODE requested")
                keyboard_status = 3

            elif (keyboard.is_pressed('-+=')):
                if keyboard_status != 4: log("Special MODE requested")
                keyboard_status = 4

            # Start worker on request
            if keyboard_status == 1:
                if worker_thread is None or not worker_thread.is_alive():
                    stop_event.clear()
                    worker_thread = threading.Thread(target=worker, args=(stop_event,), daemon=True)
                    worker_thread.start()

            # Stop worker when not in run mode
            if keyboard_status in (0, 2):
                if worker_thread is not None and worker_thread.is_alive():
                    stop_event.set()
                    worker_thread.join(timeout=0.2)

            # Mode behaviors
            if keyboard_status == 0:
                time.sleep(0.02)  # idle

            elif keyboard_status == 1:
                time.sleep(0.01)  # keep polling quickly while worker runs

            elif keyboard_status == 2:
                # Print coordinates on LMB down edge
                lmb_down = (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
                if lmb_down and not prev_lmb_down:
                    x, y = get_pos()
                    print(f"[{time.strftime('%H:%M:%S')}] LMB @ ({x}, {y})")
                prev_lmb_down = lmb_down
                time.sleep(0.01)

            elif keyboard_status == 3:
                x, y = get_pos()
                print(f"[{time.strftime('%H:%M:%S')}] LMB @ ({x}, {y})")
                time.sleep(1)


            elif keyboard_status == 4:
                DIK_Q    = 0x10
                DIK_F12  = 0x58
                press_scancode(DIK_F12)
                mouse_event(MOUSEEVENTF_LEFTDOWN)
                press_scancode(DIK_Q)
                time.sleep(0.01); release_scancode(DIK_F12);time.sleep(0.01)
                # Hold LMB + Q, then tap F12 after 0.01s
                time.sleep(0.01)
                release_scancode(DIK_Q)
                mouse_event(MOUSEEVENTF_LEFTUP)
                time.sleep(0.01)
                

                keyboard_status = 0  # prevent repeating every loop tick


        except KeyboardInterrupt:
            log("KeyboardInterrupt -> stopping.")
            stop_event.set()
            if worker_thread and worker_thread.is_alive():
                worker_thread.join(timeout=0.5)
            break


#====================================================================================================#
#define DIK_ESCAPE          0x01
#define DIK_1               0x02
#define DIK_2               0x03
#define DIK_3               0x04
#define DIK_4               0x05
#define DIK_5               0x06
#define DIK_6               0x07
#define DIK_7               0x08
#define DIK_8               0x09
#define DIK_9               0x0A
#define DIK_0               0x0B
#define DIK_MINUS           0x0C    /* - on main keyboard */
#define DIK_EQUALS          0x0D
#define DIK_BACK            0x0E    /* backspace */
#define DIK_TAB             0x0F
#define DIK_Q               0x10
#define DIK_W               0x11
#define DIK_E               0x12
#define DIK_R               0x13
#define DIK_T               0x14
#define DIK_Y               0x15
#define DIK_U               0x16
#define DIK_I               0x17
#define DIK_O               0x18
#define DIK_P               0x19
#define DIK_LBRACKET        0x1A
#define DIK_RBRACKET        0x1B
#define DIK_RETURN          0x1C    /* Enter on main keyboard */
#define DIK_LCONTROL        0x1D
#define DIK_A               0x1E
#define DIK_S               0x1F
#define DIK_D               0x20
#define DIK_F               0x21
#define DIK_G               0x22
#define DIK_H               0x23
#define DIK_J               0x24
#define DIK_K               0x25
#define DIK_L               0x26
#define DIK_SEMICOLON       0x27
#define DIK_APOSTROPHE      0x28
#define DIK_GRAVE           0x29    /* accent grave */
#define DIK_LSHIFT          0x2A
#define DIK_BACKSLASH       0x2B
#define DIK_Z               0x2C
#define DIK_X               0x2D
#define DIK_C               0x2E
#define DIK_V               0x2F
#define DIK_B               0x30
#define DIK_N               0x31
#define DIK_M               0x32
#define DIK_COMMA           0x33
#define DIK_PERIOD          0x34    /* . on main keyboard */
#define DIK_SLASH           0x35    /* / on main keyboard */
#define DIK_RSHIFT          0x36
#define DIK_MULTIPLY        0x37    /* * on numeric keypad */
#define DIK_LMENU           0x38    /* left Alt */
#define DIK_SPACE           0x39
#define DIK_CAPITAL         0x3A
#define DIK_F1              0x3B
#define DIK_F2              0x3C
#define DIK_F3              0x3D
#define DIK_F4              0x3E
#define DIK_F5              0x3F
#define DIK_F6              0x40
#define DIK_F7              0x41
#define DIK_F8              0x42
#define DIK_F9              0x43
#define DIK_F10             0x44
#define DIK_NUMLOCK         0x45
#define DIK_SCROLL          0x46    /* Scroll Lock */
#define DIK_NUMPAD7         0x47
#define DIK_NUMPAD8         0x48
#define DIK_NUMPAD9         0x49
#define DIK_SUBTRACT        0x4A    /* - on numeric keypad */
#define DIK_NUMPAD4         0x4B
#define DIK_NUMPAD5         0x4C
#define DIK_NUMPAD6         0x4D
#define DIK_ADD             0x4E    /* + on numeric keypad */
#define DIK_NUMPAD1         0x4F
#define DIK_NUMPAD2         0x50
#define DIK_NUMPAD3         0x51
#define DIK_NUMPAD0         0x52
#define DIK_DECIMAL         0x53    /* . on numeric keypad */
#define DIK_OEM_102         0x56    /* <> or \| on RT 102-key keyboard (Non-U.S.) */
#define DIK_F11             0x57
#define DIK_F12             0x58
#define DIK_F13             0x64    /*                     (NEC PC98) */
#define DIK_F14             0x65    /*                     (NEC PC98) */
#define DIK_F15             0x66    /*                     (NEC PC98) */
#define DIK_KANA            0x70    /* (Japanese keyboard)            */
#define DIK_ABNT_C1         0x73    /* /? on Brazilian keyboard */
#define DIK_CONVERT         0x79    /* (Japanese keyboard)            */
#define DIK_NOCONVERT       0x7B    /* (Japanese keyboard)            */
#define DIK_YEN             0x7D    /* (Japanese keyboard)            */
#define DIK_ABNT_C2         0x7E    /* Numpad . on Brazilian keyboard */
#define DIK_NUMPADEQUALS    0x8D    /* = on numeric keypad (NEC PC98) */
#define DIK_PREVTRACK       0x90    /* Previous Track (DIK_CIRCUMFLEX on Japanese keyboard) */
#define DIK_AT              0x91    /*                     (NEC PC98) */
#define DIK_COLON           0x92    /*                     (NEC PC98) */
#define DIK_UNDERLINE       0x93    /*                     (NEC PC98) */
#define DIK_KANJI           0x94    /* (Japanese keyboard)            */
#define DIK_STOP            0x95    /*                     (NEC PC98) */
#define DIK_AX              0x96    /*                     (Japan AX) */
#define DIK_UNLABELED       0x97    /*                        (J3100) */
#define DIK_NEXTTRACK       0x99    /* Next Track */
#define DIK_NUMPADENTER     0x9C    /* Enter on numeric keypad */
#define DIK_RCONTROL        0x9D
#define DIK_MUTE            0xA0    /* Mute */
#define DIK_CALCULATOR      0xA1    /* Calculator */
#define DIK_PLAYPAUSE       0xA2    /* Play / Pause */
#define DIK_MEDIASTOP       0xA4    /* Media Stop */
#define DIK_VOLUMEDOWN      0xAE    /* Volume - */
#define DIK_VOLUMEUP        0xB0    /* Volume + */
#define DIK_WEBHOME         0xB2    /* Web home */
#define DIK_NUMPADCOMMA     0xB3    /* , on numeric keypad (NEC PC98) */
#define DIK_DIVIDE          0xB5    /* / on numeric keypad */
#define DIK_SYSRQ           0xB7
#define DIK_RMENU           0xB8    /* right Alt */
#define DIK_PAUSE           0xC5    /* Pause */
#define DIK_HOME            0xC7    /* Home on arrow keypad */
#define DIK_UP              0xC8    /* UpArrow on arrow keypad */
#define DIK_PRIOR           0xC9    /* PgUp on arrow keypad */
#define DIK_LEFT            0xCB    /* LeftArrow on arrow keypad */
#define DIK_RIGHT           0xCD    /* RightArrow on arrow keypad */
#define DIK_END             0xCF    /* End on arrow keypad */
#define DIK_DOWN            0xD0    /* DownArrow on arrow keypad */
#define DIK_NEXT            0xD1    /* PgDn on arrow keypad */
#define DIK_INSERT          0xD2    /* Insert on arrow keypad */
#define DIK_DELETE          0xD3    /* Delete on arrow keypad */
#define DIK_LWIN            0xDB    /* Left Windows key */
#define DIK_RWIN            0xDC    /* Right Windows key */
#define DIK_APPS            0xDD    /* AppMenu key */
#define DIK_POWER           0xDE    /* System Power */
#define DIK_SLEEP           0xDF    /* System Sleep */
#define DIK_WAKE            0xE3    /* System Wake */
#define DIK_WEBSEARCH       0xE5    /* Web Search */
#define DIK_WEBFAVORITES    0xE6    /* Web Favorites */
#define DIK_WEBREFRESH      0xE7    /* Web Refresh */
#define DIK_WEBSTOP         0xE8    /* Web Stop */
#define DIK_WEBFORWARD      0xE9    /* Web Forward */
#define DIK_WEBBACK         0xEA    /* Web Back */
#define DIK_MYCOMPUTER      0xEB    /* My Computer */
#define DIK_MAIL            0xEC    /* Mail */
#define DIK_MEDIASELECT     0xED    /* Media Select */






