# mac/mac_main.py
import platform
import threading
import queue
import time
import signal
import atexit
import tkinter as tk

from core.actions import Action
import core.settings as s
import core.clipboard_manager as cm
from core.clipboard_manager import monitor_clipboard
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
from ui.popup_menu import show_popup

assert platform.system() == "Darwin", "mac_main.py is for macOS builds only."

_requests = queue.Queue()
_status_icon = None
_last_settings_open = 0.0
_SETTINGS_DEBOUNCE_SEC = 0.7


def process_requests(root: tk.Tk):
    """Pump the action queue and dispatch UI-safe operations on the Tk main thread."""
    global _last_settings_open
    try:
        while True:
            action = _requests.get_nowait()
            # Debug (optional)
            # print("ACTION:", action)

            if action == Action.OPEN_PASTE_SELECTOR:
                # Same behavior as main.pyw: show the popup selector
                root.after(0, lambda: show_popup(root))

            elif action == Action.FIX_PASTE_LIST:
                cm.fix_paste_list()

            elif action == Action.FIX_PASTE_TEXT:
                cm.fix_paste_text()

            elif action == Action.APPLY_SETTINGS:
                # Hook here if you ever want to react live to settings changes
                pass

            elif action == Action.SHOW_HISTORY:
                print("SHOW_HISTORY triggered")

            elif action == Action.SHOW_SETTING:
                now = time.time()
                if now - _last_settings_open >= _SETTINGS_DEBOUNCE_SEC:
                    _last_settings_open = now
                    root.after(0, lambda: open_settings_window(root))

    except queue.Empty:
        pass
    # tick again
    root.after(50, lambda: process_requests(root))


def _onboard_permissions(root: tk.Tk):
    """
    Ensure we have Accessibility (to paste keystrokes) and Input Monitoring (to listen globally).
    Shows guidance window with buttons to open the relevant System Settings panes if needed.
    """
    acc_ok = ensure_accessibility_trust(prompt=True)
    im_ok = has_input_monitoring()

    if acc_ok and im_ok:
        return

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

    ttk.Button(btns, text="Open Accessibility", command=open_accessibility_pane)\
        .grid(row=0, column=0, padx=6)
    ttk.Button(btns, text="Open Input Monitoring", command=open_input_monitoring_pane)\
        .grid(row=0, column=1, padx=6)
    ttk.Button(btns, text="Close", command=win.destroy)\
        .grid(row=0, column=2, padx=6)


def main():
    global _status_icon

    root = tk.Tk()
    root.withdraw()

    # Ensure permissions up front
    _onboard_permissions(root)

    # Start dispatch loop
    root.after(50, lambda: process_requests(root))

    # Hotkeys + settings
    sm = ShortcutManager(_requests)
    settings_manager = SettingsManager(_requests, sm)
    # Make the manager discoverable by ui/settings.py via core.settings
    s.SETTINGS_MANAGER = settings_manager

    # Apply initial hotkeys and start listener
    sm.update_shortcuts(settings_manager.settings["hotkeys"])
    sm.start_hotkey_listener()

    # Clipboard monitor (daemon; exits with process)
    threading.Thread(target=monitor_clipboard, daemon=True).start()

    # --- Clean shutdown helpers ---------------------------------------------

    def _shutdown_sequence():
        """Idempotent: safe to call multiple times."""
        try:
            cm.begin_shutdown()  # stop any late paste/restore artifacts
        except Exception:
            pass
        try:
            sm.stop()  # detach global hotkey tap cleanly
        except Exception:
            pass
        try:
            if _status_icon is not None:
                _status_icon.remove()
        except Exception:
            pass

    def quit_app():
        """Quit action from the status menu or window close."""
        _shutdown_sequence()
        try:
            root.quit()
            root.destroy()
        except Exception:
            pass
        # Last line: ensure process exit
        import sys
        sys.exit(0)

    # Ensure we also guard against external kill/TERM and normal interpreter exit
    atexit.register(_shutdown_sequence)
    signal.signal(signal.SIGTERM, lambda *_: quit_app())
    signal.signal(signal.SIGINT,  lambda *_: quit_app())

    # Status icon menu hooks
    def open_settings_from_status():
        _requests.put(Action.SHOW_SETTING)

    _status_icon = StatusIcon(on_quit=quit_app, on_settings=open_settings_from_status)

    # If a Tk window ever shows, close = quit
    root.protocol("WM_DELETE_WINDOW", quit_app)

    try:
        root.mainloop()
    finally:
        _shutdown_sequence()


if __name__ == "__main__":
    main()
