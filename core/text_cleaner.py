# This file contains functions used for formatting and transforming text.
# Changes:
# - add_indent now preserves blank lines and indents each line reliably.
# - combine_words now returns the final string (and handles missing words.txt gracefully).

import re

# --- Basic whitespace/paragraph utilities ---

def combine_paragraphs(text: str) -> str:
    """
    Collapse multiple consecutive newlines to a single newline.
    Leaves single newlines (paragraph breaks) intact.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # Normalize CRLF to LF first
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{2,}", "\n", text)


def join_paragraphs(text: str) -> str:
    """
    Remove all newlines so the content becomes a single flowing paragraph.
    Tabs are also normalized to a single space here.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # First, reduce extra blank lines to keep behavior predictable,
    # then replace remaining newlines with spaces.
    text = combine_paragraphs(text)
    text = text.replace("\n", " ")
    # Normalize any runs of whitespace to a single space
    return re.sub(r"[ \t]+", " ", text)


def clean_spaces(text: str) -> str:
    """
    Standardize spaces: collapse multiple spaces to one, collapse consecutive tabs to one.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # Collapse runs of spaces to a single space
    text = re.sub(r" +", " ", text)
    # Collapse runs of tabs to a single tab
    text = re.sub(r"\t+", "\t", text)
    return text


def add_indent(text: str, space_number: int) -> str:
    """
    Add a fixed number of spaces at the start of every line.
    Preserves blank lines and existing line breaks.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    try:
        n = int(space_number)
    except Exception:
        n = 0
    if n <= 0:
        return text
    indentation = " " * n
    # Prefix indentation on the first line and after every newline
    return indentation + text.replace("\n", "\n" + indentation)


# --- Word combination utility (optional / dictionary-assisted) ---

def combine_words(text: str) -> str:
    """
    Combine "broken" words that are hyphenated or split across line breaks.
    Attempts to use a dictionary (words.txt) to validate combinations.
    If words.txt is missing or unreadable, returns a conservative cleaned string.

    NOTE: This function is heuristic; use with care for non-English text.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    sentinel = "!^$"
    work = text.replace("\n", sentinel)
    strings = re.split(r'[\s,\t]+', work)

    # Try to load a dictionary; if not present, do a minimal cleanup and return.
    try:
        with open('words.txt', encoding='utf-8') as fh:
            dict_words = set(fh.read().split())
    except Exception:
        # Minimal cleanup fallback: restore newlines and collapse whitespace.
        minimal = work.replace(sentinel, "\n")
        return re.sub(r"[ \t]+", " ", minimal)

    prev_word = ""
    i = 0
    length = len(strings)

    while i < length - 1:
        prev_word = strings[i]
        word = strings[i + 1]
        combo = prev_word + word

        # Repair words that had sentinel in the middle (linebreak inside a token)
        if (sentinel in prev_word) and (prev_word.find(sentinel) != len(prev_word) - len(sentinel)):
            strings.pop(i)
            prev_word = prev_word.replace(sentinel, "")
            strings.insert(i, prev_word)
        elif sentinel in prev_word:
            strings.pop(i)
            prev_word = prev_word.replace(sentinel, "\n")
            strings.insert(i, prev_word)

        if (sentinel in word) and (word.find(sentinel) != len(word) - len(sentinel)):
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

        # If either side contains a mid-token hyphen and the token isn't valid, try removing the hyphen
        if ("-" in prev_word and not prev_word.endswith("-") and prev_word not in dict_words):
            strings[i] = prev_word.replace("-", "")
            prev_word = strings[i]

        if ("-" in word and not word.endswith("-") and word not in dict_words):
            strings[i + 1] = word.replace("-", "")
            word = strings[i + 1]

        combo = prev_word + word

        # If combo is a valid dictionary word but parts are not, merge them
        if (prev_word not in dict_words or word not in dict_words) and (combo in dict_words):
            # Replace the pair with the combo
            strings.pop(i)       # remove prev_word
            strings.pop(i)       # remove word (now at i after previous pop)
            strings.insert(i, combo)
            # Do not advance i; re-check from this position
            length = len(strings)
            continue

        i += 1
        length = len(strings)

    # Restore newlines and collapse extra whitespace runs
    result = " ".join(strings).replace(sentinel, "\n")
    result = re.sub(r"[ \t]+", " ", result)
    return result


# --- List helpers (bullets) ---
# bullet_pattern = re.compile(
#     r"""
#     (?P<bullet>
#         [*•▪▪-]           # common bullet chars
#         | \d+[.)-]?       # numbered bullets
#     )
#     [ \n\t\r\f\v\u00A0]*    # spaces
#     """,
#     re.VERBOSE,
# )

# def extract_list_items_with_bullets(text):
#     text=text.strip()
#     bullets = []
#     items = []

#     pos = 0
#     for m in bullet_pattern.finditer(text):
#         bullet = m.group('bullet')
#         start = m.end()

#         # Find next bullet to determine span
#         next_m = bullet_pattern.search(text, start)
#         end = next_m.start() if next_m else len(text)

#         item = text[start:end].strip()

#         bullets.append(bullet)
#         items.append(item)

#         pos = end

#     # If nothing matched, treat each line as plain text
#     if len(bullets)<1:
#         print()
#         lines = text.splitlines()
#         bullets = [None] * len(lines)
#         items = lines

#     return bullets, items
# bullet_pattern = re.compile(r"""
#     (                   # Capture bullet symbol
#         [*•▪]         # Bulleted characters
#         | \d{1,3}+(?:[.)])    # Or numbered bullets
#     )
#     [ \t\r\f\v\u00A0]*  # Allow multiple regular & non-breaking spaces/tabs
#     # (?:\n+)?            # Optionally allow newlines after bullet
# """, re.VERBOSE)

bullet_pattern = re.compile(r"""
    (
        [*•▪]                     # bullet chars
        |
        (?<!\d)                     # must NOT be part of a larger number on left
        \d{1,3}                     # 1 to 3 digits only
        (?:[.)-])?                  # optional punctuation
        (?!\d)                      # must NOT be part of a larger number on right
    )
    [ \t\r\f\v\u00A0]*              # whitespace
""", re.VERBOSE)
def extract_list_items_with_bullets(text):
    """
    Extracts list items and their bullets from a single line of text.
    Returns two separate lists: (bullets_list, text_list).
    """
    text=join_paragraphs(text)
    
    # 1. Split the text, preserving the bullets in the results
    parts = bullet_pattern.split(text.strip())
    
    # Remove the first element if it's an empty string (from the start of the split)
    if parts and parts[0] == '':
        parts.pop(0)

    # 2. Separate the bullets and the item text
    bullets_list = []
    text_list = []
    
    # Iterate through the parts in pairs: (bullet, item_text)
    for i in range(0, len(parts), 2):
        if i + 1 < len(parts):
            # The bullet is the odd index part (0, 2, 4, ...)
            bullet = parts[i].strip()
            # The text is the even index part (1, 3, 5, ...)
            item_text = parts[i+1].strip()
            
            bullets_list.append(bullet)
            text_list.append(item_text)
    
    if len(bullets_list) == 0: # may be a text without bullets
        lines=text.splitlines()
        if len(lines)>0:
            bullet_list=[None] * len(lines)
            text_list=lines

    return bullets_list, text_list

def list_to_html_fragment(items, bullets):
    if len(bullets)<1:
        return "<p></p>"
    previous_bullet=bullets[0]

    html_fragment, isNumeric=_get_html_bullet_style(previous_bullet)
    
    for i in range(len(bullets)):
        if previous_bullet!=bullets[i]:
            previous_bullet=bullets[i]
            numbered_pattern=re.compile(r"""\d+[.-]?""", re.VERBOSE)
            match = numbered_pattern.match(bullets[i])
            if not match: 
                # end the previous list
                if isNumeric:
                    html_fragment+="\n</ol>"
                else:
                    html_fragment+="\n</ul>"
                # start new list
                new_list_tag, isNumeric=_get_html_bullet_style(bullets[i])
                html_fragment+=new_list_tag
        html_fragment+=f"\n  <li> {items[i]} </li>"
    # end the list
    if isNumeric:
        html_fragment+="\n</ol>"
    else:
        html_fragment+="\n</ul>"
    return html_fragment

def _get_html_bullet_style(bullet_char):
    isNumeric=False

    if bullet_char=='•':
        bullet_style="circle"
    elif bullet_char=="-":
        bullet_style="square"
    elif bullet_char is None:
        bullet_style="none"
    else: #default bullet point is circle
        bullet_style="circle"
    html_style=f"""<ul style="list-style-type: {bullet_style};">"""

    if bullet_char is not None:
        # for ordered lists
        numbered_pattern=re.compile(r"""\d+[.)-]?""", re.VERBOSE)
        match = numbered_pattern.match(bullet_char)
        if match:
            print("matched decimal")
            isNumeric=True
            bullet_style="decimal"
            html_style=f"""<ol style="list-style-type: {bullet_style}";>"""
    return html_style, isNumeric


def create_rich_format_output(html_fragment):
    # Wrap fragment in the required structure
    html = (
        "<html><body>\n"
        "<!--StartFragment-->" +
        html_fragment +
        "<!--EndFragment-->\n"
        "</body></html>"
    )

    # Placeholder header
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{:08d}\r\n"
        "EndHTML:{:08d}\r\n"
        "StartFragment:{:08d}\r\n"
        "EndFragment:{:08d}\r\n"
    )

    # First, build with zeros to measure header length
    header = header_template.format(0, 0, 0, 0)
    full = header + html

    # Now compute byte offsets
    start_html = len(header)
    end_html = len(full)

    start_fragment = full.index("<!--StartFragment-->") + len("<!--StartFragment-->")
    end_fragment = full.index("<!--EndFragment-->")

    # Rebuild header with correct offsets
    header = header_template.format(
        start_html,
        end_html,
        start_fragment,
        end_fragment
    )

    full = header + html
    return full

# def main():
#     example="1. example\n2. example2\n3. hello"
#     example="""  Remove subtrees for better generalization 
# (decrease variance)
#   Prepruning: Early stopping (e.g. < 5% points)
#   Postpruning: Grow the whole tree then prune 
# subtrees that overfit on the pruning set"""
#     bullets, text =extract_list_items_with_bullets(example)
#     print(bullets)
#     print(text)
#     # print(bullets)
#     html_fragment=list_to_html_fragment(text, bullets)
#     print('\n'+html_fragment)
#     # set_html_clipboard(html_fragment)

# if __name__ == "__main__":
#     main()