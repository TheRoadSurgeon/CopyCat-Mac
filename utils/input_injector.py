# utils/input_injector.py
# Cross-platform input injection helpers using pynput.
# - send_paste_shortcut(): issues the OS Paste keystroke (Cmd+V on macOS, Ctrl+V elsewhere)
# - type_text(text): types the provided text character-by-character (fallback)
#
# NOTE (macOS): To affect other apps, grant Accessibility permission to your terminal
# (or to your packaged .app) in System Settings → Privacy & Security → Accessibility.

import time
import platform
from pynput import keyboard as kb

_CONTROLLER = kb.Controller()

def _press_and_release(*keys, delay_between: float = 0.0):
    """
    Press and release a sequence of keys in order.
    Optional tiny delay between individual presses to avoid missed events.
    """
    for key in keys:
        _CONTROLLER.press(key)
        if delay_between > 0:
            time.sleep(delay_between)
    # Release in reverse order for modifier safety
    for key in reversed(keys):
        _CONTROLLER.release(key)
        if delay_between > 0:
            time.sleep(delay_between)

def send_paste_shortcut():
    """
    Issue the standard Paste shortcut to the frontmost app.
    macOS -> Cmd+V, Windows/Linux -> Ctrl+V
    """
    is_mac = platform.system() == "Darwin"
    mod = kb.Key.cmd if is_mac else kb.Key.ctrl

    # Small delays help some targets reliably register the combo.
    _press_and_release(mod, 'v', delay_between=0.003)

def type_text(text: str, per_char_delay: float = 0.001):
    """
    Type text character-by-character.
    Handles newline and tab explicitly.
    per_char_delay keeps apps from getting flooded.
    """
    if text is None:
        return

    for ch in str(text):
        if ch == '\n':
            _CONTROLLER.press(kb.Key.enter)
            _CONTROLLER.release(kb.Key.enter)
        elif ch == '\t':
            _CONTROLLER.press(kb.Key.tab)
            _CONTROLLER.release(kb.Key.tab)
        else:
            # Using .type for a single character avoids layout surprises.
            _CONTROLLER.type(ch)

        if per_char_delay > 0:
            time.sleep(per_char_delay)
