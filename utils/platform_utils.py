"""
utils/platform_utils.py
Detect OS and define cross-platform defaults (notably global hotkeys).

Exports:
- OS_NAME, IS_MAC, IS_WINDOWS, IS_LINUX
- default_modifier1, default_modifier2
- default_hotkeys  (Action -> '<combo>' mapping)
"""

import platform as _platform
from core.actions import Action

# --- OS detection ---
OS_NAME = _platform.system()
IS_MAC = OS_NAME == "Darwin"
IS_WINDOWS = OS_NAME == "Windows"
IS_LINUX = OS_NAME == "Linux"

# --- Default modifiers by platform ---
if IS_MAC:
    default_modifier1 = "<cmd>"
    default_modifier2 = "<shift>"
else:
    # Windows & Linux: use Ctrl+Shift to avoid Alt (menu accelerator) conflicts
    default_modifier1 = "<ctrl>"
    default_modifier2 = "<shift>"

# --- Default global hotkeys (Action -> combo) ---
# Keep these aligned with your UI hints and docs.
default_hotkeys = {
    Action.OPEN_PASTE_SELECTOR: f"{default_modifier1}+{default_modifier2}+v",
    Action.FIX_PASTE_TEXT:      f"{default_modifier1}+{default_modifier2}+t",
    Action.FIX_PASTE_LIST:      f"{default_modifier1}+{default_modifier2}+l",
    # On macOS, Cmd+S is nice; on Win/Linux keep Ctrl+Shift+S to avoid collisions.
    Action.SHOW_SETTING:        f"{default_modifier1}+{default_modifier2}+s",
}

# (Optional) tiny helpers
def is_mac() -> bool: return IS_MAC
def is_windows() -> bool: return IS_WINDOWS
def is_linux() -> bool: return IS_LINUX
