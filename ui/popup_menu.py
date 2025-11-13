# ui/popup_menu.py
# Mini popup for quick actions (Clean Text / Make List)

import sys
import tkinter as tk
import core.clipboard_manager as cm

IS_MAC = sys.platform == "darwin"
if IS_MAC:
    try:
        from AppKit import NSApplication
    except Exception:
        NSApplication = None
else:
    NSApplication = None

# Auto-close after N ms of inactivity
auto_close_time = 10_000  # ms


def show_popup(root: tk.Tk):
    # 1) Do not open over Settings window (if your settings code sets this flag)
    if getattr(root, "settings_window", None) and root.settings_window.winfo_exists():
        return

    # 2) Need history to be useful
    if not cm.clipboard_history:
        return

    # 3) If popup exists, reuse it
    if getattr(root, "popup_window", None) and root.popup_window.winfo_exists():
        win = root.popup_window
        _position_at_mouse(root, win)
        _reset_close_timer(win)
        try:
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            pass
        return

    # 4) Create new popup
    win = tk.Toplevel(root)
    root.popup_window = win

    # macOS: bring app to foreground so the click lands
    if IS_MAC and NSApplication is not None:
        try:
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass

    win.overrideredirect(True)
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass
    try:
        win.focus_force()
    except Exception:
        pass

    # Allow dragging the popup
    def start_drag(e):
        win._drag_x = e.x
        win._drag_y = e.y

    def do_drag(e):
        win.geometry(f"+{win.winfo_x() + e.x - getattr(win, '_drag_x', 0)}+"
                     f"{win.winfo_y() + e.y - getattr(win, '_drag_y', 0)}")

    win.bind("<Button-1>", start_drag)
    win.bind("<B1-Motion>", do_drag)

    # Close / cleanup
    def on_close():
        if hasattr(win, "close_timer"):
            try:
                win.after_cancel(win.close_timer)
            except Exception:
                pass
        if getattr(root, "popup_window", None) is win:
            root.popup_window = None
        try:
            win.destroy()
        except Exception:
            pass

    win.on_close = on_close
    win.protocol("WM_DELETE_WINDOW", on_close)
    win.bind("<Escape>", lambda e: on_close())

    # Reset close timer on any interaction
    for ev in ("<Motion>", "<Button>", "<Key>"):
        win.bind(ev, lambda e: _reset_close_timer(win))
    _reset_close_timer(win)

    # UI content
    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    def on_button_click(action):
        # Hide first so keystroke paste goes to the target app beneath
        try:
            win.withdraw()
        except Exception:
            pass
        action()
        win.on_close()

    clean_btn = tk.Button(frame, text="Clean Text",
                          command=lambda: on_button_click(cm.fix_paste_text))
    clean_btn.pack(fill="both", expand=True, pady=5)

    list_btn = tk.Button(frame, text="Make List",
                         command=lambda: on_button_click(cm.fix_paste_list))
    list_btn.pack(fill="both", expand=True, pady=5)

    for btn in (clean_btn, list_btn):
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#a855f7", fg="white"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="SystemButtonFace", fg="black"))

    # Place at mouse
    _position_at_mouse(root, win)


def _position_at_mouse(root: tk.Tk, win: tk.Toplevel):
    # initial near-mouse position
    x, y = root.winfo_pointerx(), root.winfo_pointery()
    # size (after one idle so width/height exist)
    try:
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
    except Exception:
        w, h = 220, 90

    # screen size
    try:
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    except Exception:
        sw, sh = 1920, 1080

    # clamp so it stays on-screen
    x = max(0, min(x, sw - w))
    y = max(0, min(y, sh - h))
    try:
        win.geometry(f"+{x}+{y}")
    except Exception:
        pass
    try:
        win.deiconify()
        win.lift()
    except Exception:
        pass


def _reset_close_timer(win: tk.Toplevel):
    if hasattr(win, "close_timer"):
        try:
            win.after_cancel(win.close_timer)
        except Exception:
            pass
    win.close_timer = win.after(auto_close_time, lambda: win.on_close())
