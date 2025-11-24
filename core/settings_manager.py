# core/settings_manager.py
import os
import json
import time
from typing import Dict, Tuple

from utils.platform_utils import default_hotkeys
from core.actions import Action

SETTINGS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "settings.json")
)

# Stable JSON keys for actions
ACTION_TO_KEY = {
    Action.OPEN_PASTE_SELECTOR: "open_paste_selector",
    Action.SHOW_SETTING:        "show_setting",
    Action.FIX_PASTE_TEXT:      "fix_paste_text",
    Action.FIX_PASTE_LIST:      "fix_paste_list",
}
KEY_TO_ACTION = {v: k for k, v in ACTION_TO_KEY.items()}

_ALLOWED_TRANSFORM_KEYS = {
    "combine_paragraphs",
    "join_broken_lines",
    "fix_whitespace",
    "combine_words",
    "indent_mode",     # boolean in-memory
    "indent_size",
    "bulletize_lists",
    "bullet_char",
}

# ---------------------- Helpers: transforms ----------------------

def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _indent_mode_to_bool(val) -> bool:
    """
    Normalize indent_mode to a boolean.
    - If val is already bool, use it.
    - If val is "none"/"" -> False
    - If val is "spaces"/"tab"/any non-empty string -> True
    - If val is something else (e.g., missing), False.
    """
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("", "none", "no", "false", "0"):
            return False
        # support older values: "spaces", "tab", etc.
        return True
    try:
        return bool(val)
    except Exception:
        return False


def _clean_transforms(t: Dict) -> Dict:
    out: Dict = {}
    if isinstance(t, dict):
        for k, v in t.items():
            if k in _ALLOWED_TRANSFORM_KEYS:
                out[k] = v

    # defaults
    out.setdefault("combine_paragraphs", False)
    out.setdefault("join_broken_lines", True)
    out.setdefault("fix_whitespace", True)
    out.setdefault("combine_words", True)
    out.setdefault("indent_mode", False)  # boolean in-memory
    out.setdefault("indent_size", 4)
    out.setdefault("bulletize_lists", False)
    out.setdefault("bullet_char", "•")

    # normalize indent
    out["indent_mode"] = _indent_mode_to_bool(out.get("indent_mode"))
    out["indent_size"] = max(0, _as_int(out.get("indent_size", 4), 4))

    # normalize bullet char: force single char; keep '•' if empty
    ch = str(out.get("bullet_char", "•")) or "•"
    out["bullet_char"] = ch[0]

    return out


# ---------------------- Helpers: hotkeys ----------------------

def _parse_action_from_string(name: str):
    """
    Best-effort parse: "open_paste_selector" (stable key),
    "Action.FIX_PASTE_TEXT", or "FIX_PASTE_TEXT".
    Returns Action or None.
    """
    if not name:
        return None

    act = KEY_TO_ACTION.get(name)
    if act is not None:
        return act

    try:
        key = name.split(".", 1)[1] if name.startswith("Action.") else name
        key = key.strip().upper().replace(" ", "_")
        return Action[key]
    except Exception:
        return None


def _hotkeys_to_json(hk: Dict) -> Dict[str, str]:
    """
    In-memory keys (Action or str) -> JSON string keys.
    """
    out: Dict[str, str] = {}
    if not isinstance(hk, dict):
        return out

    for k, v in hk.items():
        if isinstance(k, Action):
            json_key = ACTION_TO_KEY.get(k, k.name.lower())
        else:
            json_key = str(k)
        out[json_key] = v
    return out


def _hotkeys_from_json(hk_json: Dict[str, str]) -> Dict:
    """
    JSON string keys -> in-memory keys (Action when recognized, else keep str).
    """
    out: Dict = {}
    if not isinstance(hk_json, dict):
        return out

    for k, v in hk_json.items():
        act = _parse_action_from_string(k)
        if act is None:
            out[k] = v
        else:
            out[act] = v
    return out


def _dedupe_hotkeys(mapping: Dict) -> Tuple[Dict, Dict[str, Action]]:
    """
    Ensure no two actions share the same key combo.
    Returns:
      - cleaned mapping (Action/str -> combo) preserving first occurrence
      - a reverse map {combo: Action} for diagnostics if needed
    """
    cleaned: Dict = {}
    seen_combo_to_action: Dict[str, Action] = {}

    for action_or_key, combo in (mapping or {}).items():
        if not combo:
            continue
        combo_norm = str(combo).strip().lower()
        if combo_norm == "":
            continue

        if combo_norm in seen_combo_to_action:
            # duplicate combo -> skip this entry
            continue

        cleaned[action_or_key] = combo_norm
        if isinstance(action_or_key, Action):
            seen_combo_to_action[combo_norm] = action_or_key
        else:
            seen_combo_to_action[combo_norm] = None

    return cleaned, seen_combo_to_action


# ---------------------- SettingsManager ----------------------

class SettingsManager:
    """
    Persists ONLY: transforms + hotkeys (atomic).
    Keeps any other runtime keys in memory only.

    Public fields:
      - settings: Dict with at least keys "transforms" and "hotkeys"
      - shortcut_manager: reference to the live ShortcutManager (for rebinds)
    """
    def __init__(self, request_queue, shortcut_manager):
        self.request_queue = request_queue
        self.shortcut_manager = shortcut_manager
        self.settings = self._defaults()
        self.load_settings()

    def _defaults(self) -> Dict:
        return {
            "transforms": {
                "combine_paragraphs": False,
                "join_broken_lines": False,
                "fix_whitespace": False,
                "combine_words": False,
                "indent_mode": False,   # boolean
                "indent_size": 4,
                "bulletize_lists": False,
                "bullet_char": "•",
            },
            # Copy to avoid accidental external mutation
            "hotkeys": dict(default_hotkeys),
        }

    # ---------- Persistence ----------

    def load_settings(self) -> Dict:
        """Load transforms + hotkeys from disk; ignore anything else. Atomic-friendly."""
        self.settings = self._defaults()

        if not os.path.exists(SETTINGS_PATH):
            return self.settings

        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # If corrupt, back it up and continue with defaults
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                os.replace(SETTINGS_PATH, SETTINGS_PATH + f".corrupt-{ts}.bak")
            except Exception:
                pass
            return self.settings

        # Transforms
        if "transforms" in data:
            self.settings["transforms"] = _clean_transforms(data["transforms"])

        # Hotkeys
        if "hotkeys" in data:
            loaded = _hotkeys_from_json(data["hotkeys"])
            merged = dict(self.settings["hotkeys"])
            merged.update(loaded)
            deduped, _ = _dedupe_hotkeys(merged)
            self.settings["hotkeys"] = deduped

        return self.settings

    def save_settings(self):
        """Atomic save of transforms + hotkeys only."""
        transforms = _clean_transforms(self.settings.get("transforms", {}))
        hotkeys = self.settings.get("hotkeys", {})
        hotkeys, _ = _dedupe_hotkeys(hotkeys)

        payload = {
            "transforms": transforms,
            "hotkeys": _hotkeys_to_json(hotkeys),
        }

        tmp = SETTINGS_PATH + ".tmp"
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SETTINGS_PATH)

        # Keep normalized in memory
        self.settings["transforms"] = transforms
        self.settings["hotkeys"] = hotkeys

    # ---------- Hotkey application ----------

    def rebind_hotkeys(self):
        """
        Apply current in-memory hotkey mapping to the live ShortcutManager.

        This just hands the mapping to ShortcutManager.update_shortcuts(),
        which rebuilds the listener.
        """
        hotkeys = self.settings.get("hotkeys", {}) or {}
        sm = self.shortcut_manager
        if not sm:
            print("[SettingsManager] rebind_hotkeys: no shortcut_manager attached")
            return

        print("[SettingsManager] rebind_hotkeys called")
        print("  hotkeys mapping:", hotkeys)

        try:
            sm.update_shortcuts(hotkeys)
            print("[SettingsManager] rebind_hotkeys: update_shortcuts() completed")
        except Exception as e:
            print("[SettingsManager] rebind_hotkeys error:", e)

