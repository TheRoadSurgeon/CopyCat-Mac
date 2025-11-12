# core/actions.py
# Centralized action enum + tiny utilities.

from __future__ import annotations
from enum import Enum, auto
from typing import Dict, Mapping, Any, Optional


class Action(Enum):
    # UI / paste features
    OPEN_PASTE_SELECTOR = auto()
    FIX_PASTE_TEXT = auto()
    FIX_PASTE_LIST = auto()

    # Settings / misc
    APPLY_SETTINGS = auto()
    SHOW_HISTORY = auto()
    SHOW_SETTING = auto()  # open settings window

    def __str__(self) -> str:
        return self.name


# Human-friendly labels for UI menus, logs, etc.
FRIENDLY_LABELS: Dict[Action, str] = {
    Action.OPEN_PASTE_SELECTOR: "Open paste selector",
    Action.FIX_PASTE_TEXT: "Fix & paste text",
    Action.FIX_PASTE_LIST: "Fix & paste list",
    Action.APPLY_SETTINGS: "Apply settings",
    Action.SHOW_HISTORY: "Show history",
    Action.SHOW_SETTING: "Open settings",
}

# Name <-> enum maps
NAME_TO_ACTION: Dict[str, Action] = {a.name: a for a in Action}


def friendly_name(action: Action) -> str:
    """Return a readable label for an Action."""
    return FRIENDLY_LABELS.get(action, action.name)


def parse_action(name: str) -> Optional[Action]:
    """
    Convert a string to an Action.
    Accepts exact enum names, case-insensitive names with spaces/underscores.
    Returns None if not recognized.
    """
    if not name:
        return None
    # fast path: exact match
    if name in NAME_TO_ACTION:
        return NAME_TO_ACTION[name]
    key = name.strip().upper().replace(" ", "_")
    return NAME_TO_ACTION.get(key)


# ---- Hotkey dict helpers (optional, handy for JSON persistence) ----

def hotkeys_to_names(mapping: Mapping[Any, str]) -> Dict[str, str]:
    """
    Convert {Action: '<combo>'} to {str: '<combo>'} so it's JSON-friendly.
    Non-Action keys are stringified.
    """
    out: Dict[str, str] = {}
    for k, v in mapping.items():
        out[k.name if isinstance(k, Action) else str(k)] = v
    return out


def hotkeys_from_names(mapping: Mapping[str, str]) -> Dict[Action, str]:
    """
    Convert {str: '<combo>'} back to {Action: '<combo>'}.
    Ignores keys that don't map to a known Action.
    """
    out: Dict[Action, str] = {}
    for k, v in mapping.items():
        act = parse_action(k)
        if act is not None:
            out[act] = v
    return out
