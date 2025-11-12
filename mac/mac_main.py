# mac/mac_main.py
import platform, threading, queue, time, tkinter as tk

from core.actions import Action
import core.settings as s
from core.clipboard_manager import monitor_clipboard
import core.clipboard_manager as cm
from core.shortcut_manager import ShortcutManager
from core.settings_manager import SettingsManager
from ui.settings import open_settings_window
from ui.status_icon import StatusIcon

from mac.permissions import (
    ensure_accessibility_trust,
    has_input_monitoring,
    open_accessibility_pane,
    open_input_monitoring_pane,
)

assert platform.system() == "Darwin", "mac_main.py is for macOS builds only."

_requests = queue.Queue()
_status_icon = None
_last_settings_open = 0.0
_SETTINGS_DEBOUNCE_SEC = 0.7


def process_requests(root: tk.Tk):
    global _last_settings_open
    try:
        while True:
            action = _requests.get_nowait()
            if action == Action.OPEN_PASTE_SELECTOR:
                # (Optional) if you have a popup selector
                pass
            elif action == Action.FIX_PASTE_LIST:
                cm.fix_paste_list()
            elif action == Action.FIX_PASTE_TEXT:
                cm.fix_paste_text()
            elif action == Action.SHOW_SETTING:
                now = time.time()
                if now - _last_settings_open >= _SETTINGS_DEBOUNCE_SEC:
                    _last_settings_open = now
                    root.after(0, lambda: open_settings_window(root))
    except queue.Empty:
        pass
    root.after(50, lambda: process_requests(root))


def _onboard_permissions(root: tk.Tk):
    """
    Make sure we have Accessibility (to send keys) and Input Monitoring (to listen to keys).
    This triggers the Accessibility prompt if needed and opens System Settings panes for both.
    """
    # 1) Accessibility: requestable via API (shows a prompt the first time).
    acc_ok = ensure_accessibility_trust(prompt=True)

    # 2) Input Monitoring: not programmatically promptable (tap will fail).
    im_ok = has_input_monitoring()

    if acc_ok and im_ok:
        return

    # Show a tiny guidance window once, so users know what to do.
    # Keep it minimal to avoid Tk issues when bundled.
    win = tk.Toplevel(root)
    win.title("Permissions required")
    win.geometry("420x220")
    win.resizable(False, False)

    import tkinter.ttk as ttk

    msg = []
    if not acc_ok:
        msg.append("• Accessibility (to paste keystrokes)")
    if not im_ok:
        msg.append("• Input Monitoring (to listen for global hotkeys)")
    label = ttk.Label(
        win,
        text=(
            "CopyCat needs the following permissions in\n"
            "System Settings → Privacy & Security:\n\n" + "\n".join(msg) +
            "\n\nAfter granting, quit and reopen the app."
        ),
        justify="left",
        anchor="w",
        padding=10,
    )
    label.pack(fill="both", expand=True)

    btns = ttk.Frame(win)
    btns.pack(pady=(0, 10))

    def _open_acc():
        open_accessibility_pane()

    def _open_im():
        open_input_monitoring_pane()

    ttk.Button(btns, text="Open Accessibility", command=_open_acc).grid(row=0, column=0, padx=6)
    ttk.Button(btns, text="Open Input Monitoring", command=_open_im).grid(row=0, column=1, padx=6)
    ttk.Button(btns, text="Close", command=win.destroy).grid(row=0, column=2, padx=6)


def main():
    global _status_icon

    root = tk.Tk()
    root.withdraw()

    # FIRST: ensure required macOS permissions
    _onboard_permissions(root)

    # Start dispatch loop
    root.after(50, lambda: process_requests(root))

    # Settings + hotkeys
    sm = ShortcutManager(_requests)
    settings_manager = SettingsManager(_requests, sm)
    s.SETTINGS_MANAGER = settings_manager  # or s.set_settings_manager(settings_manager)

    sm.update_shortcuts(settings_manager.settings["hotkeys"])
    sm.start_hotkey_listener()

    # Clipboard monitor in background
    threading.Thread(target=monitor_clipboard, daemon=True).start()

    def quit_app():
        global _status_icon
        if _status_icon is not None:
            _status_icon.remove()
            _status_icon = None
        root.quit()

    def open_settings_from_status():
        _requests.put(Action.SHOW_SETTING)

    _status_icon = StatusIcon(on_quit=quit_app, on_settings=open_settings_from_status)

    root.protocol("WM_DELETE_WINDOW", quit_app)

    try:
        root.mainloop()
    finally:
        if _status_icon is not None:
            _status_icon.remove()
        sm.stop()


if __name__ == "__main__":
    main()
