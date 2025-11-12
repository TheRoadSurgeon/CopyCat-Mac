from typing import Dict, Optional
from pynput import keyboard
from utils.platform_utils import default_hotkeys


class ShortcutManager:
    """
    Manages global hotkeys using pynput. Hotkeys map Action enums to combo strings
    like '<ctrl>+<alt>+t' or '<cmd>+<shift>+t'. When a combo fires, we push the
    corresponding Action into the shared request queue.
    """

    def __init__(self, request_queue, hotkeys: Optional[Dict] = None):
        self.request_queue = request_queue
        self.hotkeys: Dict = dict(default_hotkeys)
        if hotkeys:
            self.hotkeys.update(hotkeys)
        self.listener: Optional[keyboard.GlobalHotKeys] = None

    # ----- Internal helpers -----
    def _on_trigger(self, action):
        self.request_queue.put(action)

    def _build_mapping(self) -> Dict[str, callable]:
        """
        Build pynput's { '<combo>': callback } mapping.
        Capture the action value at definition-time to avoid late binding issues.
        """
        mapping: Dict[str, callable] = {}
        for action, combo in self.hotkeys.items():
            if not combo:
                continue
            mapping[combo] = (lambda a=action: self._on_trigger(a))
        return mapping

    def _restart_listener(self):
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

        mapping = self._build_mapping()
        if not mapping:
            return  # nothing to listen for

        self.listener = keyboard.GlobalHotKeys(mapping)
        self.listener.start()

    # ----- Public API -----
    def set_shortcut(self, action, shortcut: str):
        """
        Set/replace a single shortcut for an action.
        Example: set_shortcut(Action.FIX_PASTE_TEXT, '<ctrl>+<alt>+t')
        """
        self.hotkeys[action] = shortcut
        self._restart_listener()

    def remove_shortcut(self, action):
        """Remove a shortcut for an action (no-op if missing)."""
        if action in self.hotkeys:
            del self.hotkeys[action]
            self._restart_listener()

    def update_shortcuts(self, new_hotkeys: Dict):
        """
        Merge a dict of {Action: '<combo>'} into the current mapping.
        Example usage (your main.py): update_shortcuts(settings_manager.settings['hotkeys'])
        """
        if new_hotkeys:
            self.hotkeys.update(new_hotkeys)
        self._restart_listener()

    def start_hotkey_listener(self):
        """Start (or restart) the global hotkey listener."""
        self._restart_listener()
        print("hotkey_listener is running")

    def stop(self):
        """Stop the listener and clear it."""
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    # Optional utility for UI/debugging
    def get_hotkeys(self) -> Dict:
        """Return the current {Action: '<combo>'} mapping."""
        return dict(self.hotkeys)
