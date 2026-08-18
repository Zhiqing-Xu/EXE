# -*- coding: utf-8 -*-
# Windows-only macro (SendInput): START/STOP + coord mode.

import time
import ctypes
import keyboard  # pip install keyboard
import threading

from ctypes import wintypes
from typing import Tuple, Optional

def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def cancellable_sleep(sec: float, stop_event: threading.Event, tick: float = 0.02) -> bool:
    """Sleep up to sec; returns False if stop_event is set."""
    end = time.time() + float(sec)
    while not stop_event.is_set():
        rem = end - time.time()
        if rem <= 0:
            return True
        time.sleep(min(tick, rem))
    return False


# =====================
# Win32 SendInput
# =====================
if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong

user32 = ctypes.windll.user32

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP    = 0x0002
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004
MOUSEEVENTF_WHEEL    = 0x0800

VK_LBUTTON           = 0x01


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", INPUT_UNION)]


SendInput = user32.SendInput

POINT = wintypes.POINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


def get_pos() -> Tuple[int, int]:
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(pt.x), int(pt.y)


def set_pos(x: int, y: int) -> None:
    if not user32.SetCursorPos(int(x), int(y)):
        raise ctypes.WinError(ctypes.get_last_error())


def _send_mouse(flags: int, data: int = 0) -> None:
    pkt = INPUT(type=INPUT_MOUSE, ii=INPUT_UNION(mi=MOUSEINPUT(0, 0, data, flags, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))


def left_click() -> None:
    _send_mouse(MOUSEEVENTF_LEFTDOWN)
    time.sleep(0.05)
    _send_mouse(MOUSEEVENTF_LEFTUP)


def click_at_offset(anchor_x: int, anchor_y: int, dx: int, dy: int, stop_event: threading.Event) -> bool:
    """Move to (anchor + offset) then left-click."""
    if stop_event.is_set():
        return False
    set_pos(anchor_x + int(dx), anchor_y + int(dy))
    if not cancellable_sleep(0.08, stop_event):
        return False
    left_click()
    return not stop_event.is_set()


def multi_click_at_offset(
    anchor_x: int,
    anchor_y: int,
    dx: int,
    dy: int,
    n: int,
    gap_sec: float,
    stop_event: threading.Event,
) -> bool:
    """Repeated left-click at (anchor + offset)."""
    if stop_event.is_set():
        return False
    set_pos(anchor_x + int(dx), anchor_y + int(dy))
    if not cancellable_sleep(0.08, stop_event):
        return False
    for _ in range(int(n)):
        if stop_event.is_set():
            return False
        left_click()
        if not cancellable_sleep(float(gap_sec), stop_event):
            return False
    return True


def scroll_at_offset(anchor_x: int, anchor_y: int, dx: int, dy: int, amount: int, stop_event: threading.Event) -> bool:
    """Move to (anchor + offset) then scroll (negative=down)."""
    if stop_event.is_set():
        return False
    set_pos(anchor_x + int(dx), anchor_y + int(dy))
    if not cancellable_sleep(0.05, stop_event):
        return False
    pkt = INPUT(type=INPUT_MOUSE, ii=INPUT_UNION(mi=MOUSEINPUT(0, 0, int(amount), MOUSEEVENTF_WHEEL, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))
    return not stop_event.is_set()


# =====================
# Keyboard (scancodes)
# =====================
ESC_SCAN = 0x01
F_SCAN = 0x21


def press_scancode(scan: int) -> None:
    pkt = INPUT(type=INPUT_KEYBOARD, ii=INPUT_UNION(ki=KEYBDINPUT(0, int(scan), KEYEVENTF_SCANCODE, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))


def release_scancode(scan: int) -> None:
    flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    pkt = INPUT(type=INPUT_KEYBOARD, ii=INPUT_UNION(ki=KEYBDINPUT(0, int(scan), flags, 0, ULONG_PTR(0))))
    SendInput(1, ctypes.byref(pkt), ctypes.sizeof(pkt))


def press_for(scan: int, hold_sec: float, stop_event: threading.Event) -> bool:
    if stop_event.is_set():
        return False
    press_scancode(scan)
    ok = cancellable_sleep(float(hold_sec), stop_event)
    release_scancode(scan)
    return ok and (not stop_event.is_set())


def tap_key(scan: int, tap_sec: float, stop_event: threading.Event) -> bool:
    return press_for(scan, tap_sec, stop_event)


# ===========================================================#
#    `7MMF' `YMM'`7MM"""YMM `YMM'   `MM'                     #
#      MM   .M'    MM    `7   VMA   ,V                __,    #
#      MM .d"      MM   d      VMA ,V                `7MM    #
#      MMMMM.      MMmmMM       VMMP                   MM    #
#      MM  VMA     MM   Y  ,     MM         mmmmm      MM    #
#      MM   `MM.   MM     ,M     MM                    MM    #
#    .JMML.   MMb.JMMmmmmMMM   .JMML.                .JMML.  #
# ===========================================================#

def run_macro_1(stop_event: threading.Event) -> bool:

    # Set Anchor
    if not tap_key(F_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    if not tap_key(ESC_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    if not tap_key(F_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    anchor_x, anchor_y = get_pos()

    # Calibration

    offsets_1_prime = [
        (1439, 593, 698 , 363) , # Category 1
        (1439, 593, 1142, 279) , # Category 1.1
    ]

    offsets_2_prime = [
        (1439, 593, 1000, 692) , # Item : ZhiJiaoJiMu
        (1439, 593, 1000, 692) , # Item : ZhiJiaoJiMu

        # (1439, 593, 1284, 572) , # Item : ZhengFang JiMu
        # (1439, 593, 1284, 572) , # Item : ZhengFang JiMu

        # (1439, 593, 1418, 572) , # Item : SiLengZhui JiMu
        # (1439, 593, 1418, 572) , # Item : SiLengZhui JiMu

        # (1439, 593, 1557, 572) , # Item : ShanXing JiMu
        # (1439, 593, 1557, 572) , # Item : ShanXing JiMu

        (1439, 593, 1983, 952) , # Press : Make
        (1439, 593, 1579, 720) , # Press : OK
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1983, 952) , # Press : Make
        (1439, 593, 806 , 955) , # Press : Queue
        (1439, 593, 1713, 441) , # Press : Accelerate
        (1439, 593, 1587, 612) , # Press : RightMost
        (1439, 593, 1446, 706) , # Press : Confirm
        (1439, 593, 1446, 806) , # Press : Collect
        (1439, 593, 1446, 806) , # Press : Collect
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1845, 350) , # Press : Cancel
    ]

    offsets_1 = [(x - x_p, y - y_p) 
                for (x_p, y_p, x, y) in offsets_1_prime ]

    offsets_2 = [(x - x_p, y - y_p) 
                for (x_p, y_p, x, y) in offsets_2_prime ]
    
    # Main Loop
    for _ in range(111):
        if stop_event.is_set():
            return False
        
        # Preset
        for dx, dy in offsets_1:
            if not click_at_offset(anchor_x, anchor_y, dx, dy, stop_event):
                return False
            if not cancellable_sleep(1, stop_event):
                return False
        
        # Scroll: use current cursor as a temporary anchor
        if not scroll_at_offset(anchor_x, anchor_y, 0, 0, -120 * 57, stop_event):  # -120 = scroll down 1 notch
            return False
        if not cancellable_sleep(1, stop_event):
            return False

        for dx, dy in offsets_2:
            if not click_at_offset(anchor_x, anchor_y, dx, dy, stop_event):
                return False
            if not cancellable_sleep(1, stop_event):
                return False
        
        if not cancellable_sleep(1, stop_event):
            return False

        if not tap_key(ESC_SCAN, 0.5, stop_event):
            return False
        if not cancellable_sleep(1, stop_event):
            return False

        if not tap_key(F_SCAN, 0.5, stop_event):
            return False
        if not cancellable_sleep(1, stop_event):
            return False

    return not stop_event.is_set()

def macro_worker_1(stop_event: threading.Event, done_event: threading.Event) -> None:
    try:
        run_macro_1(stop_event)
    finally:
        done_event.set()



# ===========================================================#
#    `7MMF' `YMM'`7MM"""YMM `YMM'   `MM'           pd""b.    #
#      MM   .M'    MM    `7   VMA   ,V            (O)  `8b   #
#      MM .d"      MM   d      VMA ,V                  ,89   #
#      MMMMM.      MMmmMM       VMMP                 ""Yb.   #
#      MM  VMA     MM   Y  ,     MM       mmmmm         88   #
#      MM   `MM.   MM     ,M     MM               (O)  .M'   #
#    .JMML.   MMb.JMMmmmmMMM   .JMML.              bmmmd'    #
# ===========================================================#

def run_macro_3(stop_event: threading.Event) -> bool:

    # Set Anchor
    if not tap_key(F_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    if not tap_key(ESC_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    if not tap_key(F_SCAN, 0.06, stop_event):
        return False
    if not cancellable_sleep(1, stop_event):
        return False

    anchor_x, anchor_y = get_pos()

    # Calibration

    offsets_1_prime = [
        (1439, 593, 698 , 363) , # Category 1
        (1439, 593, 1142, 279) , # Category 1.1
    ]

    offsets_2_prime = [

        (1439, 593, 1139, 572) , # Item : MuYun ChuGui
        (1439, 593, 1139, 572) , # Item : MuYun ChuGui

        (1439, 593, 1983, 952) , # Press : Make
        (1439, 593, 806 , 955) , # Press : Queue
        (1439, 593, 1713, 441) , # Press : Accelerate
        (1439, 593, 1587, 612) , # Press : RightMost
        (1439, 593, 1446, 706) , # Press : Confirm
        (1439, 593, 1446, 806) , # Press : Collect
        (1439, 593, 1446, 806) , # Press : Collect
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1845, 350) , # Press : Cancel
        (1439, 593, 1845, 350) , # Press : Cancel
    ]

    offsets_1 = [(x - x_p, y - y_p) 
                for (x_p, y_p, x, y) in offsets_1_prime ]

    offsets_2 = [(x - x_p, y - y_p) 
                for (x_p, y_p, x, y) in offsets_2_prime ]
    
    # Main Loop
    for _ in range(100):
        if stop_event.is_set():
            return False
        
        # Preset
        for dx, dy in offsets_1:
            if not click_at_offset(anchor_x, anchor_y, dx, dy, stop_event):
                return False
            if not cancellable_sleep(1, stop_event):
                return False
        
        # Scroll: use current cursor as a temporary anchor
        if not scroll_at_offset(anchor_x, anchor_y, 0, 0, -120 * 57, stop_event):  # -120 = scroll down 1 notch
            return False
        if not cancellable_sleep(1, stop_event):
            return False

        for dx, dy in offsets_2:
            if not click_at_offset(anchor_x, anchor_y, dx, dy, stop_event):
                return False
            if not cancellable_sleep(1, stop_event):
                return False
        
        if not cancellable_sleep(1, stop_event):
            return False

        if not tap_key(ESC_SCAN, 0.5, stop_event):
            return False
        if not cancellable_sleep(1, stop_event):
            return False

        if not tap_key(F_SCAN, 0.5, stop_event):
            return False
        if not cancellable_sleep(1, stop_event):
            return False

    return not stop_event.is_set()

def macro_worker_3(stop_event: threading.Event, done_event: threading.Event) -> None:
    try:
        run_macro_3(stop_event)
    finally:
        done_event.set()

# =====================
# Main
# =====================
if __name__ == "__main__":
    keyboard_status = 0  # 0=idle, 1=macro, 2=coord mode

    stop_event = threading.Event()
    done_event = threading.Event()
    worker_thread: Optional[threading.Thread] = None

    prev_lmb_down = False

    log("Controls: '.+/'=START, '[+]'=STOP, '9+0'=COORD")

    while True:
        try:
            if keyboard.is_pressed("[+]"):
                keyboard_status = 0
            elif keyboard.is_pressed(".+/"):
                keyboard_status = 1
            elif keyboard.is_pressed("9+0"):
                keyboard_status = 2
            elif keyboard.is_pressed("-+="):
                keyboard_status = 3



            if keyboard_status == 1:
                if worker_thread is None or not worker_thread.is_alive():
                    stop_event.clear()
                    done_event.clear()
                    worker_thread = threading.Thread(target=macro_worker_1, args=(stop_event, done_event), daemon=True)
                    worker_thread.start()

            elif keyboard_status == 3:
                if worker_thread is None or not worker_thread.is_alive():
                    stop_event.clear()
                    done_event.clear()
                    worker_thread = threading.Thread(target=macro_worker_3, args=(stop_event, done_event), daemon=True)
                    worker_thread.start()

            else:
                if worker_thread is not None and worker_thread.is_alive():
                    stop_event.set()
                    worker_thread.join(timeout=0.2)

            if keyboard_status in (1, 3) and done_event.is_set():
                keyboard_status = 0

            if keyboard_status == 0:
                time.sleep(0.02)
            elif keyboard_status in (1, 3):
                time.sleep(0.01)
            elif keyboard_status == 2:
                lmb_down = (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
                if lmb_down and not prev_lmb_down:
                    x, y = get_pos()
                    print(f"[{time.strftime('%H:%M:%S')}] LMB @ ({x}, {y})")
                prev_lmb_down = lmb_down
                time.sleep(0.01)

        except KeyboardInterrupt:
            log("KeyboardInterrupt -> stopping")
            stop_event.set()
            if worker_thread is not None and worker_thread.is_alive():
                worker_thread.join(timeout=0.5)
            break
