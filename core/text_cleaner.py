# core/text_cleaner.py
# Formatting helpers for CopyCat.
# Simple + predictable:
# - clean_spaces: collapse runs of spaces/tabs; trim trailing spaces per line
# - combine_paragraphs: collapse 2+ newlines (blank-line paragraph breaks) to ONE space
# - join_paragraphs: remove ALL newlines -> one flowing paragraph
# - add_indent & combine_words: kept simple
# - List helpers: detect bullets at line starts; CF_HTML offsets in BYTES

import re

# ---------- Basic whitespace / paragraph utilities ----------

_NEWLINES_RE = re.compile(r"\r\n?")  # \r\n or \r -> \n

def _nl(s: str) -> str:
    """Normalize all newlines to \\n."""
    return _NEWLINES_RE.sub("\n", s)

def clean_spaces(text: str) -> str:
    """
    Collapse runs of spaces/tabs/NBSPs to a single *space* on each line.
    Leaves line breaks intact, but trims extra horizontal whitespace around them.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # Normalize newlines for consistent line processing
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    # For each line: collapse horizontal whitespace to one space and trim edges
    lines = [re.sub(r"[ \t\u00A0]+", " ", ln).strip() for ln in lines]

    return "\n".join(lines)


def combine_paragraphs(text: str) -> str:
    """
    Merge paragraphs by turning ANY run of newlines (\\n, \\r\\n, \\r) into a single space.
    Also collapses repeated horizontal whitespace to one space and trims edges.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # Normalize newlines to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Treat one-or-more newlines as a paragraph separator -> single space
    text = re.sub(r"\n+", " ", text)
    # Collapse spaces/tabs/NBSP runs to single space
    text = re.sub(r"[ \t\u00A0]+", " ", text)
    return text.strip()


def join_paragraphs(text: str) -> str:
    """
    Remove ALL newlines so the content becomes one flowing paragraph.
    Then collapse any extra spaces produced and trim ends.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = _nl(text).replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def add_indent(text: str, space_number: int) -> str:
    """Indent every line by N spaces, preserving blank lines."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    try:
        n = int(space_number)
    except Exception:
        n = 0
    if n <= 0:
        return text
    text = _nl(text)
    pad = " " * n
    return pad + text.replace("\n", "\n" + pad)


# ---------- Word combination utility (optional / dictionary-assisted) ----------

def combine_words(text: str) -> str:
    """
    Heuristic fix for words broken by hyphens/line breaks.
    If words.txt missing, returns conservatively cleaned text.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    sentinel = "!^$"
    work = _nl(text).replace("\n", sentinel)
    tokens = re.split(r"[\s,\t]+", work)

    try:
        with open("words.txt", encoding="utf-8") as fh:
            dict_words = set(fh.read().split())
    except Exception:
        minimal = work.replace(sentinel, "\n")
        return re.sub(r"[ \t]+", " ", minimal)

    i = 0
    while i < len(tokens) - 1:
        a = tokens[i]
        b = tokens[i + 1]

        # Repair sentinel inside tokens
        if sentinel in a:
            tokens[i] = a.replace(sentinel, "" if not a.endswith(sentinel) else "\n")
            a = tokens[i]
        if sentinel in b:
            tokens[i + 1] = b.replace(sentinel, "" if not b.endswith(sentinel) else "\n")
            b = tokens[i + 1]

        # Remove mid-token hyphens for invalid tokens
        if "-" in a and not a.endswith("-") and a not in dict_words:
            tokens[i] = a.replace("-", ""); a = tokens[i]
        if "-" in b and not b.endswith("-") and b not in dict_words:
            tokens[i + 1] = b.replace("-", ""); b = tokens[i + 1]

        combo = a + b
        if (a not in dict_words or b not in dict_words) and (combo in dict_words):
            tokens.pop(i)      # remove a
            tokens.pop(i)      # remove b (now at i)
            tokens.insert(i, combo)
            continue

        i += 1

    result = " ".join(tokens).replace(sentinel, "\n")
    result = re.sub(r"[ \t]+", " ", result)
    return result


# ---------- List helpers (bullets) ----------

# Bullet token at the *start of a line*:
#  - symbols: • * -   ▪
#  - 1..3 digit numbers with optional . ) or -
_LINE_BULLET_RE = re.compile(r"(?m)^\s*(?P<bullet>([*•▪-]|\d{1,3}[.)-]?))\s+")

def extract_list_items_with_bullets(text: str):
    """
    Extract (bullets_list, text_list) from multi-line text.
    If no bullets: returns ([], cleaned_lines).
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = _nl(text).strip()

    bullets_list, text_list = [], []
    matches = list(_LINE_BULLET_RE.finditer(text))
    if matches:
        for idx, m in enumerate(matches):
            bullet = m.group("bullet").strip()
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            item = text[start:end].strip()
            if item:
                bullets_list.append(bullet)
                text_list.append(item)
    else:
        text_list = [ln.strip() for ln in text.split("\n") if ln.strip()]

    return bullets_list, text_list


def list_to_html_fragment(items, bullets):
    """Build minimal <ul>/<ol> fragment; switch when ordered/unordered style changes."""
    if not items:
        return "<p></p>"

    def kind(b):
        if not b:
            return ("unordered", "none")
        if re.match(r"^\d{1,3}[.)-]?$", str(b)):
            return ("ordered", "decimal")
        if b == "-":
            return ("unordered", "square")
        if b == "•":
            return ("unordered", "disc")
        return ("unordered", "disc")

    html = []
    t, st = kind(bullets[0] if bullets else None)

    def open_list(tt, sst):
        if tt == "ordered":
            html.append('<ol style="list-style-type: decimal;">')
        else:
            html.append(f'<ul style="list-style-type: {sst};">')

    def close_list(tt):
        html.append("</ol>" if tt == "ordered" else "</ul>")

    open_list(t, st)
    prev_t, prev_st = t, st

    for b, it in zip(bullets or [None] * len(items), items):
        t, st = kind(b)
        if (t != prev_t) or (t == "unordered" and st != prev_st):
            close_list(prev_t)
            open_list(t, st)
            prev_t, prev_st = t, st
        html.append(f"  <li>{it}</li>")

    close_list(prev_t)
    return "\n" + "\n".join(html) + "\n"


def create_rich_format_output(html_fragment: str) -> str:
    """
    Create a Windows CF_HTML payload with correct BYTE offsets (safe for UTF-8/emoji).
    """
    if not isinstance(html_fragment, str):
        html_fragment = "" if html_fragment is None else str(html_fragment)

    html = (
        "<html><body>\n"
        "<!--StartFragment-->" + html_fragment + "<!--EndFragment-->\n"
        "</body></html>"
    )

    header_tmpl = (
        "Version:0.9\r\n"
        "StartHTML:{:08d}\r\n"
        "EndHTML:{:08d}\r\n"
        "StartFragment:{:08d}\r\n"
        "EndFragment:{:08d}\r\n"
    )

    provisional = header_tmpl.format(0, 0, 0, 0).encode("ascii")
    body = html.encode("utf-8")

    start_html = len(provisional)
    end_html = start_html + len(body)

    sf = b"<!--StartFragment-->"
    ef = b"<!--EndFragment-->"
    try:
        start_fragment = start_html + body.index(sf) + len(sf)
        end_fragment   = start_html + body.index(ef)
    except ValueError:
        start_fragment = start_html
        end_fragment = end_html

    header = header_tmpl.format(start_html, end_html, start_fragment, end_fragment)
    return header + html
