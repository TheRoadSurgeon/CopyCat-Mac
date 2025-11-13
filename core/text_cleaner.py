# core/text_cleaner.py
# Formatting and transforming helpers for CopyCat.
# - Preserves newlines when extracting lists (no join_paragraphs here)
# - Fixes missing-variable bug when no bullets are found
# - CF_HTML offsets computed in BYTES (safe for Unicode/emoji)

import re

# --- Basic whitespace/paragraph utilities ---

def combine_paragraphs(text: str) -> str:
    """Collapse multiple consecutive newlines to a single newline."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{2,}", "\n", text)


def join_paragraphs(text: str) -> str:
    """Remove all newlines so the content becomes a single flowing paragraph."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = combine_paragraphs(text)
    text = text.replace("\n", " ")
    return re.sub(r"[ \t]+", " ", text)


def clean_spaces(text: str) -> str:
    """Collapse multiple spaces/tabs to single instances."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\t+", "\t", text)
    return text


def add_indent(text: str, space_number: int) -> str:
    """Indent every line by N spaces, preserving blank lines."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    try:
        n = int(space_number)
    except Exception:
        n = 0
    if n <= 0:
        return text
    indentation = " " * n
    return indentation + text.replace("\n", "\n" + indentation)


# --- Word combination utility (dictionary-assisted, optional) ---

def combine_words(text: str) -> str:
    """
    Combine 'broken' words split by hyphens/line breaks using a dictionary (words.txt) when available.
    Returns a conservative cleaned string if words.txt is missing.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    sentinel = "!^$"
    work = text.replace("\n", sentinel)
    strings = re.split(r'[\s,\t]+', work)

    try:
        with open('words.txt', encoding='utf-8') as fh:
            dict_words = set(fh.read().split())
    except Exception:
        minimal = work.replace(sentinel, "\n")
        return re.sub(r"[ \t]+", " ", minimal)

    i = 0
    length = len(strings)
    while i < length - 1:
        prev_word = strings[i]
        word = strings[i + 1]

        # Repair sentinel inside tokens
        if sentinel in prev_word:
            if not prev_word.endswith(sentinel):
                strings[i] = prev_word.replace(sentinel, "")
            else:
                strings[i] = prev_word.replace(sentinel, "\n")
        prev_word = strings[i]

        if sentinel in word:
            if not word.endswith(sentinel):
                strings[i + 1] = word.replace(sentinel, "")
            else:
                strings[i + 1] = word.replace(sentinel, "\n")
        word = strings[i + 1]

        # Remove mid-token hyphens for invalid tokens
        if "-" in prev_word and not prev_word.endswith("-") and prev_word not in dict_words:
            strings[i] = prev_word.replace("-", "")
            prev_word = strings[i]
        if "-" in word and not word.endswith("-") and word not in dict_words:
            strings[i + 1] = word.replace("-", "")
            word = strings[i + 1]

        combo = prev_word + word
        if (prev_word not in dict_words or word not in dict_words) and (combo in dict_words):
            # Merge the pair
            strings.pop(i)
            strings.pop(i)
            strings.insert(i, combo)
            length = len(strings)
            continue

        i += 1
        length = len(strings)

    result = " ".join(strings).replace(sentinel, "\n")
    result = re.sub(r"[ \t]+", " ", result)
    return result


# --- List helpers (bullets) ---

# Bullet token at the *start of a line*:
#  - common symbols: • * -   ▪
#  - 1..3 digit numbers with optional . ) or -
_LINE_BULLET_RE = re.compile(
    r"(?m)^\s*(?P<bullet>([*•▪-]|\d{1,3}[.)-]?))\s+"
)

def extract_list_items_with_bullets(text: str):
    """
    Extract (bullets_list, text_list) from multi-line text.
    - Preserves newlines (does NOT join paragraphs here).
    - If no explicit bullets found, returns ([], [lines...]) so the caller
      can decide whether to bulletize plain lines.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    bullets_list = []
    text_list = []

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
        # No bullets -> return cleaned non-empty lines; bullets_list stays empty
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        text_list = lines

    return bullets_list, text_list


def list_to_html_fragment(items, bullets):
    """
    Build an HTML <ul>/<ol> fragment from parallel lists of items & bullets.
    Switches lists when ordered/unordered style changes.
    """
    if not bullets or not items:
        # Graceful fallback
        if items:
            # default to unordered 'disc'
            return "<ul>" + "".join(f"\n  <li>{i}</li>" for i in items) + "\n</ul>"
        return "<p></p>"

    def bullet_kind(b):
        # returns ("ordered" | "unordered", style_name_if_unordered)
        if b is None or b == "":
            return ("unordered", "none")
        if re.match(r"^\d{1,3}[.)-]?$", str(b)):
            return ("ordered", "decimal")
        if b == "-":
            return ("unordered", "square")
        if b == "•":
            return ("unordered", "disc")
        # default unordered
        return ("unordered", "disc")

    html = []
    cur_type, cur_style = bullet_kind(bullets[0])

    def open_list(t, st):
        if t == "ordered":
            html.append(f'<ol style="list-style-type: decimal;">')
        else:
            if st == "none":
                html.append(f'<ul style="list-style-type: none;">')
            else:
                html.append(f'<ul style="list-style-type: {st};">')

    def close_list(t):
        html.append("</ol>" if t == "ordered" else "</ul>")

    open_list(cur_type, cur_style)

    for b, it in zip(bullets, items):
        t, st = bullet_kind(b)
        if (t != cur_type) or (t == "unordered" and st != cur_style):
            close_list(cur_type)
            cur_type, cur_style = t, st
            open_list(cur_type, cur_style)
        html.append(f"  <li>{it}</li>")

    close_list(cur_type)
    return "\n" + "\n".join(html) + "\n"


def create_rich_format_output(html_fragment: str) -> str:
    """
    Create a Windows CF_HTML payload with correct byte offsets.
    Caller should encode to UTF-8 before placing on clipboard.
    """
    if not isinstance(html_fragment, str):
        html_fragment = str(html_fragment) if html_fragment is not None else ""

    html = (
        "<html><body>\n"
        "<!--StartFragment-->" + html_fragment + "<!--EndFragment-->\n"
        "</body></html>"
    )

    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{:08d}\r\n"
        "EndHTML:{:08d}\r\n"
        "StartFragment:{:08d}\r\n"
        "EndFragment:{:08d}\r\n"
    )

    # First build a provisional header to measure byte offsets
    provisional_header = header_template.format(0, 0, 0, 0)
    header_bytes = provisional_header.encode("ascii")
    html_bytes = html.encode("utf-8")

    start_html = len(header_bytes)
    end_html = start_html + len(html_bytes)

    sf_marker = b"<!--StartFragment-->"
    ef_marker = b"<!--EndFragment-->"
    try:
        start_fragment = start_html + html_bytes.index(sf_marker) + len(sf_marker)
        end_fragment = start_html + html_bytes.index(ef_marker)
    except ValueError:
        # If markers are missing (shouldn't happen), fall back to whole doc
        start_fragment = start_html
        end_fragment = end_html

    header = header_template.format(start_html, end_html, start_fragment, end_fragment)
    # Return as str; clipboard setter will .encode('utf-8')
    return header + html
