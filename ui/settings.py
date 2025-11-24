# ui/settings.py

import sys
import tkinter as tk
from tkinter import ttk

from pynput import keyboard as pk  # for validating combos with HotKey.parse

import core.settings as s
from core.actions import Action

copycat_purple = "#6312cd"  # currently used only for active states / future tweaks

IS_MAC = sys.platform == "darwin"
if IS_MAC:
    try:
        from AppKit import NSApplication
    except Exception:
        NSApplication = None
else:
    NSApplication = None


# ---------- Tiny tooltip helper ----------

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tip = tk.Toplevel(self.widget)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        lbl = tk.Label(
            self.tip,
            text=self.text,
            bg="#ffffe0",
            relief="solid",
            borderwidth=1,
        )
        lbl.pack(ipadx=4, ipady=2)
        self.tip.geometry(f"+{x}+{y}")

    def _hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------- Shortcut recording helpers ----------

# Map Tk keysyms for modifiers to tokens pynput understands
MOD_TK_TO_TOKEN = {
    "Control_L": "<ctrl>", "Control_R": "<ctrl>",
    "Alt_L": "<alt>", "Alt_R": "<alt>",
    "Shift_L": "<shift>", "Shift_R": "<shift>",
}
if IS_MAC:
    MOD_TK_TO_TOKEN.update({"Meta_L": "<cmd>", "Meta_R": "<cmd>", "Command": "<cmd>"})

# Known special non-modifier keys
SPECIAL_TO_TOKEN = {
    "Return": "<enter>", "Tab": "<tab>", "Escape": "<esc>", "BackSpace": "<backspace>",
    "Space": "<space>",
}


def _normalize_base_key(keysym: str) -> str | None:
    if keysym in SPECIAL_TO_TOKEN:
        return SPECIAL_TO_TOKEN[keysym]
    if keysym.startswith("F") and keysym[1:].isdigit():
        return f"<{keysym.lower()}>"
    if len(keysym) == 1:
        return keysym.lower()
    return None


def _compose_shortcut(mods: set[str], base_tok: str) -> str:
    order = ["<cmd>", "<ctrl>", "<alt>", "<shift>"]
    mod_list = [m for m in order if m in mods]
    return "+".join(mod_list + ([base_tok] if base_tok else []))


def _is_valid_combo(combo: str) -> bool:
    try:
        pk.HotKey.parse(combo)
        return True
    except Exception:
        return False


def _duplicate_map(named_values: list[tuple[str, str]]) -> dict[str, list[str]]:
    # returns {combo: [names...]} for combos that appear 2+ times (non-empty)
    counts = {}
    for name, val in named_values:
        v = (val or "").strip()
        if not v:
            continue
        counts.setdefault(v, []).append(name)
    return {k: v for k, v in counts.items() if len(v) > 1}


def record_shortcut(parent: tk.Tk, target_var: tk.StringVar, sibling_vars: list[tk.StringVar]):
    """Open modal, capture one chord, write into target_var if valid and not duplicate."""
    top = tk.Toplevel(parent)
    top.title("Rebind Shortcut")
    top.transient(parent)
    top.attributes("-topmost", True)

    msg = ttk.Label(top, text="Press the new shortcut… (Esc to cancel)")
    msg.pack(padx=14, pady=(12, 6))
    # use a neutral, subtle color like the original
    preview = ttk.Label(top, text="", foreground="#666")
    preview.pack(padx=14, pady=(0, 10))

    # Center-ish
    try:
        top.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - top.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - top.winfo_height()) // 3)
        top.geometry(f"+{x}+{y}")
    except Exception:
        pass

    try:
        top.grab_set()
    except Exception:
        pass
    top.focus_force()

    pressed_mods: set[str] = set()

    def on_press(ev):
        keysym = ev.keysym
        tok = MOD_TK_TO_TOKEN.get(keysym)
        if tok:
            pressed_mods.add(tok)
            preview.configure(text=_compose_shortcut(pressed_mods, "…"))
            return

        base_tok = _normalize_base_key(keysym)
        if not base_tok:
            preview.configure(text="Unsupported key")
            return

        if not pressed_mods:
            preview.configure(text="Add Ctrl/Alt/Shift (or Cmd on macOS)")
            return

        combo = _compose_shortcut(pressed_mods, base_tok)
        if not _is_valid_combo(combo):
            preview.configure(text="Invalid combo")
            return

        # Block duplicates against current sibling values
        siblings = {v.get().strip() for v in sibling_vars}
        if combo in siblings:
            preview.configure(text="Already in use")
            return

        target_var.set(combo)
        try:
            top.grab_release()
        except Exception:
            pass
        top.destroy()

    def on_release(ev):
        keysym = ev.keysym
        tok = MOD_TK_TO_TOKEN.get(keysym)
        if tok and tok in pressed_mods:
            pressed_mods.discard(tok)
            preview.configure(text=_compose_shortcut(pressed_mods, "…") if pressed_mods else "")

    def cancel(_=None):
        try:
            top.grab_release()
        except Exception:
            pass
        top.destroy()

    top.bind("<KeyPress>", on_press)
    top.bind("<KeyRelease>", on_release)
    top.bind("<Escape>", cancel)


# ---------- Settings window ----------

def open_settings_window(root: tk.Tk):
    """
    Open (or focus) the CopyCat Settings window.
    """
    sm = s.get_settings_manager()
    if sm is None:
        print("SettingsManager not initialized")
        return

    settings = sm.settings
    hotkeys = settings["hotkeys"]
    transforms = settings["transforms"]

    # If already open, just focus & raise it.
    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel) and w.title() == "CopyCat Settings & Shortcuts":
            try:
                if IS_MAC and NSApplication is not None:
                    try:
                        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
                    except Exception as e:
                        print("NSApp activate (existing) failed:", e)
                w.deiconify()
                w.lift()
                w.focus_force()
                w.attributes("-topmost", True)
                w.after(400, lambda: w.attributes("-topmost", False))
            except Exception as e:
                print("Error refocusing settings window:", e)
            return

    # --- Create new settings window ---
    win = tk.Toplevel(root)
    win.title("CopyCat Settings & Shortcuts")
    win.geometry("700x600")

    # macOS: bring app to foreground first
    if IS_MAC and NSApplication is not None:
        try:
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception as e:
            print("NSApp activate failed:", e)

    # Raise/focus the window
    win.update_idletasks()
    win.deiconify()
    win.lift()
    win.focus_force()
    win.attributes("-topmost", True)
    win.after(500, lambda: win.attributes("-topmost", False))

    frm = ttk.Frame(win)
    frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
    frm.grid_columnconfigure(0, weight=1)
    frm.grid_columnconfigure(1, weight=1)

    # ===== Header =====
    hdr = ttk.Label(frm, text="CopyCat Settings & Shortcuts", anchor="w")
    try:
        hdr.configure(font=("Segoe UI", 14, "bold"))
    except Exception:
        pass
    hdr.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    # ===== Shortcuts =====
    ttk.Label(frm, text="Shortcuts (use Rebind; fields are read-only)").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    # StringVars for read-only entries
    var_hist = tk.StringVar(value=hotkeys[Action.OPEN_PASTE_SELECTOR])
    var_set = tk.StringVar(value=hotkeys[Action.SHOW_SETTING])
    var_qp = tk.StringVar(value=hotkeys.get(Action.FIX_PASTE_TEXT, "<ctrl>+<alt>+t"))
    var_pl = tk.StringVar(value=hotkeys.get(Action.FIX_PASTE_LIST, "<ctrl>+<alt>+l"))

    # Helper to make row with readonly entry + Rebind button
    def make_bind_row(row_label: str, row_index: int, var: tk.StringVar, siblings: list[tk.StringVar]):
        ttk.Label(frm, text=row_label).grid(row=row_index, column=0, sticky="w")
        row = ttk.Frame(frm)
        row.grid(row=row_index + 1, column=0, sticky="we", padx=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        entry = ttk.Entry(row, width=28, textvariable=var, state="readonly")
        entry.grid(row=0, column=0, sticky="we")
        ttk.Button(row, text="Rebind", width=8,
                   command=lambda: record_shortcut(win, var, siblings)).grid(row=0, column=1, padx=(6, 0))
        return entry

    def make_bind_row_right(row_label: str, row_index: int, var: tk.StringVar, siblings: list[tk.StringVar]):
        ttk.Label(frm, text=row_label).grid(row=row_index, column=1, sticky="w")
        row = ttk.Frame(frm)
        row.grid(row=row_index + 1, column=1, sticky="we", padx=(8, 0))
        row.grid_columnconfigure(0, weight=1)
        entry = ttk.Entry(row, width=28, textvariable=var, state="readonly")
        entry.grid(row=0, column=0, sticky="we")
        ttk.Button(row, text="Rebind", width=8,
                   command=lambda: record_shortcut(win, var, siblings)).grid(row=0, column=1, padx=(6, 0))
        return entry

    # Row 1: Open Paste Selector, Open Settings
    e_hist = make_bind_row("Open Paste Selector Pop-Up", 2, var_hist, [var_set, var_qp, var_pl])
    Tooltip(e_hist, "Example: <ctrl>+<alt>+v  or  <cmd>+<shift>+v")
    e_set = make_bind_row_right("Open Settings", 2, var_set, [var_hist, var_qp, var_pl])
    Tooltip(e_set, "Example: <ctrl>+<alt>+,  or  <cmd>+s")

    # Row 2: Quick Paste, Paste List
    e_qp = make_bind_row("Quick Paste", 4, var_qp, [var_hist, var_set, var_pl])
    Tooltip(e_qp, "Example: <ctrl>+<alt>+t  or  <cmd>+<shift>+t")
    e_pl = make_bind_row_right("Paste List", 4, var_pl, [var_hist, var_set, var_qp])
    Tooltip(e_pl, "Example: <ctrl>+<alt>+l  or  <cmd>+<shift>+l")

    ttk.Separator(frm).grid(row=6, column=0, columnspan=2, sticky="we", pady=(12, 10))

    # ===== Quick Paste Options =====
    ttk.Label(frm, text="Quick Paste Options").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    v_fix_whitespace = tk.BooleanVar(value=transforms.get("fix_whitespace", False))
    cb_whitespace = ttk.Checkbutton(frm, text="Fix Whitesapce", variable=v_fix_whitespace)
    cb_whitespace.grid(row=8, column=0, columnspan=2, sticky="w")
    Tooltip(cb_whitespace, "Remove excess whitespace")

    v_combine = tk.BooleanVar(value=transforms.get("combine_paragraphs", False))
    cb_combine = ttk.Checkbutton(frm, text="Combine paragraphs", variable=v_combine)
    cb_combine.grid(row=9, column=0, columnspan=2, sticky="w")
    Tooltip(cb_combine, "Flatten paragraph breaks between blocks")

    v_join = tk.BooleanVar(value=transforms.get("join_broken_lines", False))
    cb_join = ttk.Checkbutton(frm, text="Join lines", variable=v_join)
    cb_join.grid(row=10, column=0, columnspan=2, sticky="w")
    Tooltip(cb_join, "Merge wrapped lines where appropriate")

    v_fix_broken_words = tk.BooleanVar(value=transforms.get("combine_words", False))
    cb_fix = ttk.Checkbutton(frm, text="Fix Broken Words", variable=v_fix_broken_words)
    cb_fix.grid(row=11, column=0, columnspan=2, sticky="w")
    Tooltip(cb_fix, "Fix words split by new lines")

    v_indent_on = tk.BooleanVar(value=transforms.get("indent_mode", False))
    cb_indent = ttk.Checkbutton(frm, text="Indent paragraphs", variable=v_indent_on)
    cb_indent.grid(row=12, column=0, sticky="w")
    Tooltip(cb_indent, "Indent pastes by " + str(transforms.get("indent_size", 4)) + " spaces")

    ttk.Label(frm, text="Indent size (spaces)").grid(row=12, column=1, sticky="w")
    v_size = tk.IntVar(value=int(transforms.get("indent_size", 4)))
    scl = tk.Scale(
        frm,
        from_=0,
        to=8,
        resolution=1,
        orient="horizontal",
        tickinterval=1,
        showvalue=True,
        variable=v_size,
        length=260,
    )
    scl.grid(row=13, column=1, sticky="we", padx=(8, 0))

    def _toggle_indent(*_):
        state = tk.NORMAL if v_indent_on.get() else tk.DISABLED
        try:
            scl.configure(state=state)
        except Exception:
            pass

    _toggle_indent()
    v_indent_on.trace_add("write", _toggle_indent)

    ttk.Separator(frm).grid(row=14, column=0, columnspan=2, sticky="we", pady=(12, 10))

    # ===== Paste List Options =====
    ttk.Label(frm, text="Paste List Options").grid(
        row=15, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    v_bul = tk.BooleanVar(value=transforms.get("bulletize_lists", False))
    cb_bul = ttk.Checkbutton(frm, text="Turn new lines into bullet points", variable=v_bul)
    cb_bul.grid(row=16, column=0, columnspan=2, sticky="w")

    # Derive UI style from bullet_char only (no bullet_style persisted)
    ch = transforms.get("bullet_char", "•")
    default_style = "numbered" if ch == "1" else ("dash" if ch == "-" else "bullet")
    v_style = tk.StringVar(value=default_style)

    style_frame = ttk.Frame(frm)
    style_frame.grid(row=16, column=1, sticky="w")

    rb_bullet = ttk.Radiobutton(style_frame, text="• Bullet", value="bullet", variable=v_style)
    rb_dash = ttk.Radiobutton(style_frame, text="- Dash", value="dash", variable=v_style)
    rb_num = ttk.Radiobutton(style_frame, text="1. 2. 3.", value="numbered", variable=v_style)
    rb_bullet.grid(row=0, column=0, padx=(0, 10))
    rb_dash.grid(row=0, column=1, padx=(0, 10))
    rb_num.grid(row=0, column=2)

    def _toggle_style(*_):
        state = "normal" if v_bul.get() else "disabled"
        for w in (rb_bullet, rb_dash, rb_num):
            try:
                w.state([state])
            except Exception:
                w.configure(state=state)

    _toggle_style()
    v_bul.trace_add("write", _toggle_style)

    ttk.Separator(frm).grid(row=98, column=0, columnspan=2, sticky="we", pady=(8, 8))

    # Status line
    status = ttk.Label(frm, text="", anchor="e")
    status.grid(row=100, column=0, columnspan=2, sticky="we")

    # ---- Save / Close -------------------------------------------------------

    def save_settings():
        # Read strings from readonly vars
        c_hist = var_hist.get().strip()
        c_set = var_set.get().strip()
        c_qp = var_qp.get().strip()
        c_pl = var_pl.get().strip()

        # Validate syntax
        combos = [("Open Paste", c_hist), ("Open Settings", c_set),
                  ("Quick Paste", c_qp), ("Paste List", c_pl)]
        for name, val in combos:
            if not val or not _is_valid_combo(val):
                status.configure(text=f"Invalid shortcut: {name}")
                status.after(1800, lambda: status.configure(text=""))
                return

        # Check duplicates
        dups = _duplicate_map(combos)
        if dups:
            # Build friendly error
            first = next(iter(dups.values()))
            if len(first) >= 2:
                status.configure(text=f"Duplicate shortcuts: {first[0]} & {first[1]}")
            else:
                status.configure(text="Duplicate shortcuts")
            status.after(2000, lambda: status.configure(text=""))
            return

        try:
            # Hotkeys
            hotkeys[Action.OPEN_PASTE_SELECTOR] = c_hist
            hotkeys[Action.SHOW_SETTING] = c_set
            hotkeys[Action.FIX_PASTE_TEXT] = c_qp
            hotkeys[Action.FIX_PASTE_LIST] = c_pl

            # Text transforms
            transforms["combine_paragraphs"] = bool(v_combine.get())
            transforms["join_broken_lines"] = bool(v_join.get())
            if v_indent_on.get():
                transforms["indent_mode"] = True
                transforms["indent_size"] = int(v_size.get() or 0)
            else:
                transforms["indent_mode"] = False
            transforms["fix_whitespace"] = bool(v_fix_whitespace.get())
            transforms["combine_words"] = bool(v_fix_broken_words.get())

            # List transforms
            transforms["bulletize_lists"] = bool(v_bul.get())
            style = v_style.get() if v_bul.get() else "bullet"
            if style == "dash":
                transforms["bullet_char"] = "-"
            elif style == "numbered":
                transforms["bullet_char"] = "1"  # sentinel for numbered
            else:
                transforms["bullet_char"] = "•"

            sm.save_settings()

            # Rebind hotkeys (macOS defers, to avoid crash during callback)
            if IS_MAC:
                win.after_idle(sm.rebind_hotkeys)
            else:
                sm.rebind_hotkeys()

            # Close settings window on successful save
            win.destroy()
            return
        except Exception as e:
            print("Error while saving settings:", e)
            status.configure(text="Save failed")
            status.after(1500, lambda: status.configure(text=""))

    btns = ttk.Frame(frm)
    btns.grid(row=99, column=0, columnspan=2, pady=(8, 0), sticky="e")
    ttk.Button(btns, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=6)
    ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.RIGHT)
