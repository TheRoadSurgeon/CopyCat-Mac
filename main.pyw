# main.py
import threading
import queue
import tkinter as tk
import sys
import time   # NEW: for simple debouncing

import core.settings as s
from core.clipboard_manager import monitor_clipboard
from ui.popup_menu import show_popup
from core.shortcut_manager import ShortcutManager
from core.actions import Action
import core.clipboard_manager as cm
from core.settings_manager import SettingsManager
from ui.settings import open_settings_window
from ui.status_icon import StatusIcon

_requests = queue.Queue()
_status_icon = None

# NEW: simple debounce timestamp to prevent double-opening Settings
_last_settings_open = 0.0
_SETTINGS_DEBOUNCE_SEC = 0.7


def process_requests(root: tk.Tk):
    """Handle queued actions on the Tk main thread."""
    global _last_settings_open

    try:
        while True:
            action = _requests.get_nowait()
            print("ACTION:", action)

            if action == Action.OPEN_PASTE_SELECTOR:
                show_popup(root)

            elif action == Action.FIX_PASTE_LIST:
                cm.fix_paste_list()

            elif action == Action.FIX_PASTE_TEXT:
                cm.fix_paste_text()

            elif action == Action.APPLY_SETTINGS:
                # hook if you ever need to apply settings live
                pass

            elif action == Action.SHOW_HISTORY:
                print("SHOW_HISTORY triggered")

            elif action == Action.SHOW_SETTING:
                # Ensure settings window opens from the Tk thread, with debounce
                now = time.time()
                if now - _last_settings_open >= _SETTINGS_DEBOUNCE_SEC:
                    _last_settings_open = now
                    root.after(0, lambda: open_settings_window(root))

    except queue.Empty:
        pass

    # Schedule next poll
    root.after(50, lambda: process_requests(root))


def main():
    global _status_icon

    # Single hidden Tk root for the whole app
    root = tk.Tk()
    root.withdraw()

    # Start dispatch loop for queued actions
    root.after(50, lambda: process_requests(root))

    # Settings & hotkeys
    sm = ShortcutManager(_requests)
    settings_manager = SettingsManager(_requests, sm)
    s.SETTINGS_MANAGER = settings_manager  # or s.set_settings_manager(settings_manager)

    # Apply current hotkeys and start listener
    sm.update_shortcuts(settings_manager.settings["hotkeys"])
    sm.start_hotkey_listener()

    # Clipboard monitor in background
    threading.Thread(target=monitor_clipboard, daemon=True).start()

    print("hotkey_listener is running")
    print("Running clipboard manager in background…")
    print(settings_manager.settings["hotkeys"])

    # ---- Quit / Settings callbacks used by status icon ----

    def quit_app():
        """Quit cleanly when user selects 'Quit CopyCat'."""
        global _status_icon
        if _status_icon is not None:
            _status_icon.remove()
            _status_icon = None
        root.quit()

    def open_settings_from_status():
        """Triggered from status icon 'Settings' menu item."""
        _requests.put(Action.SHOW_SETTING)

    # Cross-platform status icon:
    # - macOS: NSStatusBar (implemented in StatusIcon)
    # - Windows/Linux: pystray (in StatusIcon)
    _status_icon = StatusIcon(
        on_quit=quit_app,
        on_settings=open_settings_from_status,
    )

    # If you ever show a main window, closing it should quit the app
    root.protocol("WM_DELETE_WINDOW", quit_app)

    try:
        root.mainloop()
    finally:
        if _status_icon is not None:
            _status_icon.remove()
        sm.stop()


if __name__ == "__main__":
    main()
