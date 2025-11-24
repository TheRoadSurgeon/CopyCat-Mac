import re

# ---------- Newline normalization ----------

_NEWLINES_RE = re.compile(r"\r\n?")  # \r\n or \r -> \n


def _nl(s: str) -> str:
    """Normalize all newlines to \\n and coerce non-str to str."""
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    return _NEWLINES_RE.sub("\n", s)


# ---------- Basic whitespace / paragraph utilities ----------


def clean_spaces(text: str) -> str:
    """
    Collapse runs of spaces/tabs/NBSPs to a single *space* on each line.
    Leaves line breaks intact, but trims extra horizontal whitespace around them.
    """
    text = _nl(text)

    lines = text.split("\n")
    # For each line: collapse horizontal whitespace to one space and trim edges
    lines = [re.sub(r"[ \t\u00A0]+", " ", ln).strip() for ln in lines]

    return "\n".join(lines)


def join_lines(text: str) -> str:
    """
    Join "soft-wrapped" lines but preserve paragraph breaks.

    Any run of 2+ newlines is treated as a paragraph separator; single newlines
    inside a paragraph are turned into spaces.
    """
    text = _nl(text)

    # Split into paragraphs on blank lines (2+ newlines)
    parts = re.split(r"\n{2,}", text)

    cleaned_paragraphs = []
    for part in parts:
        # Split on single newlines inside the paragraph and join with spaces
        lines = part.split("\n")
        # Keep non-empty lines, stripping edges
        joined = " ".join(ln.strip() for ln in lines if ln.strip() != "")
        cleaned_paragraphs.append(joined)

    if not cleaned_paragraphs:
        return ""

    # Re-join paragraphs with a double newline separator
    result = cleaned_paragraphs[0]
    for para in cleaned_paragraphs[1:]:
        result += "\n\n" + para

    return result


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
    Attempts to use a dictionary (words.txt) to validate combinations.

    - If words.txt is missing, returns a conservatively cleaned string.
    - Tries to repair hyphenated words that are split across lines.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    sentinel = "!^$"
    # Normalize newlines and mark them with a sentinel so we can restore them later
    work = _nl(text).replace("\n", sentinel)
    strings = re.split(r"[\s,\t]+", work)

    # Try to load a dictionary; if not present, do a minimal cleanup and return.
    try:
        with open("words.txt", encoding="utf-8") as fh:
            dict_words = set(fh.read().split())
    except Exception:
        # Minimal cleanup fallback: restore newlines and collapse whitespace.
        minimal = work.replace(sentinel, "\n")
        return re.sub(r"[ \t]+", " ", minimal)

    i = 0
    length = len(strings)

    while i < length - 1:
        prev_word = strings[i]
        word = strings[i + 1]

        # Repair words that had sentinel in the middle (linebreak inside a token)
        if (sentinel in prev_word) and (
            prev_word.find(sentinel) != len(prev_word) - len(sentinel)
        ):
            strings.pop(i)
            prev_word = prev_word.replace(sentinel, "")
            strings.insert(i, prev_word)
        elif sentinel in prev_word:
            strings.pop(i)
            prev_word = prev_word.replace(sentinel, "\n")
            strings.insert(i, prev_word)

        if (sentinel in word) and (
            word.find(sentinel) != len(word) - len(sentinel)
        ):
            strings.pop(i + 1)
            word = word.replace(sentinel, "")
            strings.insert(i + 1, word)
        elif sentinel in word:
            strings.pop(i + 1)
            word = word.replace(sentinel, "\n")
            strings.insert(i + 1, word)

        # Recompute because we may have changed entries
        prev_word = strings[i]
        word = strings[i + 1]
        combo = prev_word + word

        # If either side contains a mid-token hyphen and the token isn't valid,
        # try removing the hyphen inside that token.
        if "-" in prev_word and not prev_word.endswith("-") and prev_word not in dict_words:
            strings[i] = prev_word.replace("-", "")
            prev_word = strings[i]

        if "-" in word and not word.endswith("-") and word not in dict_words:
            strings[i + 1] = word.replace("-", "")
            word = strings[i + 1]

        combo = prev_word + word

        # If the combo has a hyphen not at the ends and it's not a valid
        # hyphenated word, try removing the hyphen and see if that is valid.
        if (
            "-" in combo
            and combo[0] != "-"
            and combo[-1] != "-"
            and combo not in dict_words
        ):
            temp = combo.split("-")
            combo_no_hyphen = "".join(temp)
            if combo_no_hyphen in dict_words:
                strings.pop(i)  # remove prev_word
                strings.pop(i)  # remove word (now at i after previous pop)
                strings.insert(i, combo_no_hyphen)
                length = len(strings)
                continue

        # If combo is a valid dictionary word but parts are not, merge them
        if (prev_word not in dict_words or word not in dict_words) and combo in dict_words:
            strings.pop(i)  # remove prev_word
            strings.pop(i)  # remove word (now at i after previous pop)
            strings.insert(i, combo)
            length = len(strings)
            continue

        i += 1
        length = len(strings)

    # Restore newlines and collapse extra whitespace runs
    result = " ".join(strings).replace(sentinel, "\n")
    result = re.sub(r"[ \t]+", " ", result)
    return result


# ---------- List helpers (bullets) ----------

# Bullet token at the *start of a line*:
#  - symbols: • * -   ▪ and other block-like bullet chars
#  - 1..3 digit numbers with optional . ) or -
_LINE_BULLET_RE = re.compile(
    r"(?m)^\s*(?P<bullet>([*•▪-]|\d{1,3}[.)-]?|[\u25A0-\u25FF]))\s+"
)


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
        end_fragment = start_html + body.index(ef)
    except ValueError:
        start_fragment = start_html
        end_fragment = end_html

    header = header_tmpl.format(start_html, end_html, start_fragment, end_fragment)
    return header + html
