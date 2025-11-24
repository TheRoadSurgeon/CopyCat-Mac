# core/clipboard_manager.py
# Cross-platform clipboard + paste helpers with HTML list paste support.
# - Uses pyperclip for text read/write everywhere
# - Uses native HTML paste on macOS (NSPasteboard) and Windows (win32clipboard/CF_HTML)
# - Falls back to plain text or typing if needed
# - Adds begin_shutdown() to suppress any last paste/restore on quit

import time
import threading
import sys
import platform

import pyperclip

import core.text_cleaner as tc
import core.settings as s
from utils.input_injector import send_paste_shortcut, type_text

IS_MAC = (sys.platform == "darwin") or (platform.system() == "Darwin")
IS_WINDOWS = platform.system() == "Windows"

clipboard_history = []
last_copied = ""

# When True, all paste/restore actions become no-ops (used on app quit)
_SHUTTING_DOWN = False


def begin_shutdown():
    """Call this before quitting to prevent any late paste/restore artifacts."""
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = True


# ---------- Clipboard primitives ----------

def _get_clipboard_text() -> str:
    try:
        txt = pyperclip.paste()
        return txt if isinstance(txt, str) else ""
    except Exception:
        return ""


def _safe_copy(text: str) -> bool:
    if _SHUTTING_DOWN:
        return False
    try:
        pyperclip.copy(text or "")
        return True
    except Exception:
        return False


def _restore_clipboard_async(original: str, delay_sec: float = 0.35) -> None:
    def _worker():
        # Wait a bit so the target app can read the cleaned text during paste
        time.sleep(delay_sec)
        if _SHUTTING_DOWN:
            return
        try:
            pyperclip.copy(original or "")
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def _paste_via_clipboard(text: str, restore_original: bool = True) -> bool:
    if _SHUTTING_DOWN:
        return False

    original = _get_clipboard_text() if restore_original else ""
    if not _safe_copy(text):
        return False

    try:
        time.sleep(0.06)
        if _SHUTTING_DOWN:
            return False
        send_paste_shortcut()
        if restore_original:
            _restore_clipboard_async(original)
        return True
    except Exception:
        return False


# ---------- Background monitor ----------

def monitor_clipboard():
    global last_copied
    while True:
        try:
            text = _get_clipboard_text()
            if isinstance(text, str) and text and text != last_copied:
                last_copied = text
                clipboard_history.append(text)
                if len(clipboard_history) > 50:
                    clipboard_history.pop(0)
        except Exception:
            pass
        time.sleep(0.3)


# ---------- Settings & transforms ----------

def _settings_transforms():
    sm = s.get_settings_manager()
    if not sm or not isinstance(sm.settings, dict):
        return {}
    return sm.settings.get("transforms", {}) or {}


def _apply_text_transforms(text: str) -> str:
    """
    Apply text transforms according to current settings.
    Order (friend's improvements + your original options):

      1) combine_words      -> fix words broken by hyphen/line breaks
      2) fix_whitespace     -> normalize spaces/tabs
      3) join_broken_lines  -> join soft line-wraps (preserve paragraphs)
      4) combine_paragraphs -> collapse paragraphs into one flowing block
      5) indent_mode        -> optional indentation of all lines
    """
    t = _settings_transforms()
    out = text or ""

    # 1) Combine broken words first (handles hyphenated line breaks)
    if t.get("combine_words"):
        try:
            cw = tc.combine_words(out)
            if isinstance(cw, str) and cw:
                out = cw
        except Exception:
            pass

    # 2) Whitespace normalization
    if t.get("fix_whitespace"):
        out = tc.clean_spaces(out)

    # 3) Join wrapped lines (preserve paragraph breaks where possible)
    if t.get("join_broken_lines"):
        join_lines = getattr(tc, "join_lines", None)
        if callable(join_lines):
            out = join_lines(out)
        else:
            # Fallback: treat as a full paragraph join if join_lines is missing
            join_paragraphs = getattr(tc, "join_paragraphs", None)
            if callable(join_paragraphs):
                out = join_paragraphs(out)

    # 4) Combine paragraphs into a single flowing block (no newlines)
    if t.get("combine_paragraphs"):
        join_paragraphs = getattr(tc, "join_paragraphs", None)
        if callable(join_paragraphs):
            out = join_paragraphs(out)
        else:
            # Fallback to combine_paragraphs if older helper exists
            combine_paragraphs = getattr(tc, "combine_paragraphs", None)
            if callable(combine_paragraphs):
                out = combine_paragraphs(out)

    # 5) Optional indentation
    mode = t.get("indent_mode", False)
    indent_on = (
        (mode is True)
        or (isinstance(mode, str) and mode.strip().lower() not in ("", "none", "false", "0"))
    )
    if indent_on:
        try:
            size = int(t.get("indent_size", 0) or 0)
        except Exception:
            size = 0
        if size > 0:
            out = tc.add_indent(out, size)

    return out


# ---------- HTML helpers ----------

def _set_clipboard_html_mac(html: str, plain_fallback: str = "") -> bool:
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeHTML, NSPasteboardTypeString
    except Exception:
        return False
    if _SHUTTING_DOWN:
        return False
    try:
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        # On macOS: put RAW HTML (no CF_HTML header) to avoid "Version:0.9 ..." artifacts
        pb.setString_forType_(html, NSPasteboardTypeHTML)
        if plain_fallback:
            pb.setString_forType_(plain_fallback, NSPasteboardTypeString)
        return True
    except Exception:
        return False


def _set_clipboard_html_win(cf_html: str) -> bool:
    try:
        import win32clipboard as cb
    except Exception:
        return False
    if _SHUTTING_DOWN:
        return False

    try:
        fmt = cb.RegisterClipboardFormat("HTML Format")
    except Exception:
        return False

    for _ in range(5):
        try:
            cb.OpenClipboard()
            try:
                cb.EmptyClipboard()
                cb.SetClipboardData(fmt, cf_html.encode("utf-8"))  # CF_HTML with header
                return True
            finally:
                cb.CloseClipboard()
        except Exception as e:
            if "denied" in str(e).lower():
                time.sleep(0.1)
                continue
            return False
    return False


# ---------- Public actions ----------

def fix_paste_text():
    if _SHUTTING_DOWN:
        return

    raw = last_copied or _get_clipboard_text()
    if not isinstance(raw, str):
        raw = str(raw) if raw is not None else ""
    if not raw.strip():
        return

    output = _apply_text_transforms(raw)

    if _paste_via_clipboard(output, restore_original=True):
        return

    # Final fallback: type it out
    try:
        if not _SHUTTING_DOWN:
            type_text(output)
    except Exception:
        pass


def fix_paste_list():
    if _SHUTTING_DOWN:
        return

    raw = (last_copied or _get_clipboard_text() or "").replace("\r\n", "\n").replace("\r", "\n")
    text = raw.strip()
    if not text:
        print("fix_paste_list: empty clipboard")
        return

    t = _settings_transforms()
    bullet_char = (t.get("bullet_char") or "•")
    bullet_char = bullet_char[0] if isinstance(bullet_char, str) and bullet_char else "•"
    bulletize_plain = bool(t.get("bulletize_lists", True))

    # Try parsing bullets
    bullets, items = [], []
    try:
        bullets, items = tc.extract_list_items_with_bullets(text)
    except Exception:
        pass

    if not (bullets and items):
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if lines and bulletize_plain:
            bullets = [bullet_char] * len(lines)
            items = lines
        elif lines:
            bullets = [""] * len(lines)
            items = lines

    # Plain-text fallback (always build)
    plain_lines = []
    for b, it in zip(bullets, items):
        cleaned = tc.clean_spaces(it)
        plain_lines.append(f"{(b + ' ') if b else ''}{cleaned}".rstrip())
    plain_result = "\n".join(plain_lines)
    if plain_result and not plain_result.endswith("\n"):
        plain_result += "\n"

    # Try rich path if available
    html_fragment = None          # raw <ul><li>…</li></ul> or similar
    cf_html_payload = None        # Windows CF_HTML with Version/StartHTML header

    try:
        if hasattr(tc, "list_to_html_fragment"):
            html_fragment = tc.list_to_html_fragment(items, bullets)
        if hasattr(tc, "create_rich_format_output"):
            cf_html_payload = tc.create_rich_format_output(html_fragment or "")
    except Exception:
        html_fragment = None
        cf_html_payload = None

    # macOS expects raw HTML (no CF_HTML header) to avoid artifacts
    if IS_MAC and html_fragment:
        original = _get_clipboard_text()
        if _set_clipboard_html_mac(html_fragment, plain_fallback=plain_result.strip("\n")):
            try:
                time.sleep(0.06)
                if not _SHUTTING_DOWN:
                    send_paste_shortcut()
                    _restore_clipboard_async(original)
                return
            except Exception:
                pass

    # Windows expects CF_HTML (with header/offsets)
    if IS_WINDOWS and cf_html_payload:
        original = _get_clipboard_text()
        if _set_clipboard_html_win(cf_html_payload):
            try:
                time.sleep(0.06)
                if not _SHUTTING_DOWN:
                    send_paste_shortcut()
                    _restore_clipboard_async(original)
                return
            except Exception:
                pass

    # Plain text path
    if _paste_via_clipboard(plain_result, restore_original=True):
        return

    # Final fallback: type
    try:
        if not _SHUTTING_DOWN:
            type_text(plain_result)
    except Exception:
        pass
