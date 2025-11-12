# TODO Priority:
# - Figure out pop up menu on Mac (possibly a drop down from menu bar with pyobjc)
# - Pop up window cannot be clicked while Settings menu is open
#       - Current fix: comment out code in settings.py line 111.
#                      keep an eye on this for future issues.
#       - Consider not allowing mini menu to open when settings is open
# 
# TODO Future features
# - Clipboard preview
# - Additional options
# - Animations/Transitions
# - Prettier UI

import tkinter as tk
import pyperclip
import core.clipboard_manager as cm
from core.text_cleaner import clean_spaces, combine_paragraphs, join_paragraphs, combine_words

# Set to close pop up window at 10 seconds
auto_close_time = 10000  # ms

def show_popup(root: tk.Tk):
    # Prevent popup menu when settings window is open
    if hasattr(root, "settings_window") and root.settings_window and root.settings_window.winfo_exists():
        return

    if not cm.clipboard_history:
        return
    
    # Reuse popup if it exists
    if hasattr(root, "popup_window") and root.popup_window and root.popup_window.winfo_exists():
        win = root.popup_window

        # Move to cursor position
        x, y = root.winfo_pointerx(), root.winfo_pointery()
        win.geometry(f"+{x}+{y}")

        _reset_close_timer(win, root)
        win.lift()
        return

    
    # Create new popup
    win = tk.Toplevel(root)
    root.popup_window = win

    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.focus_force()

    
    # Window drag handling
    def start_drag(e):
        win._drag_x = e.x
        win._drag_y = e.y

    def do_drag(e):
        win.geometry(f"+{win.winfo_x() + e.x - win._drag_x}+{win.winfo_y() + e.y - win._drag_y}")

    win.bind("<Button-1>", start_drag)
    win.bind("<B1-Motion>", do_drag)

    
    # Auto-close setup
    def on_close():
        if hasattr(win, "close_timer"):
            win.after_cancel(win.close_timer)
        root.popup_window = None
        win.destroy()

    win.on_close = on_close  # store for reuse
    win.protocol("WM_DELETE_WINDOW", on_close)
    win.bind("<Escape>", lambda e: on_close())
    _reset_close_timer(win, root)

    # Any interaction resets timer
    win.bind("<Motion>", lambda e: _reset_close_timer(win, root))
    win.bind("<Button>", lambda e: _reset_close_timer(win, root))
    win.bind("<Key>", lambda e: _reset_close_timer(win, root))

    
    # UI content
    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Close pop up window immediately on button click
    def on_button_click(action):
        win.withdraw()
        action()
        win.on_close()

    clean_btn = tk.Button(frame, text="Clean Text", command=lambda: on_button_click(cm.fix_paste_text))
    clean_btn.pack(fill="both", expand=True, pady=5)

    list_btn = tk.Button(frame, text="Make List", command=lambda: on_button_click(cm.fix_paste_list))
    list_btn.pack(fill="both", expand=True, pady=5)
    
    # clean_btn = tk.Button(frame, text="Clean Text", command=cm.fix_paste_text)
    # clean_btn.pack(fill="both", expand=True, pady=5)

    # list_btn = tk.Button(frame, text="Make List", command=cm.fix_paste_list)
    # list_btn.pack(fill="both", expand=True, pady=5)

    for btn in (clean_btn, list_btn):
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#a855f7", fg="white"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="SystemButtonFace", fg="black"))

    # Position initial popup at mouse
    x, y = root.winfo_pointerx(), root.winfo_pointery()
    win.geometry(f"+{x}+{y}")

# Helper: reset auto-close timer
def _reset_close_timer(win, root):
    if hasattr(win, "close_timer"):
        win.after_cancel(win.close_timer)
    win.close_timer = win.after(
        auto_close_time,
        lambda: win.on_close()
    )
