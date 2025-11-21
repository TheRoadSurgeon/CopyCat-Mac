# core/shortcut_manager.py
from typing import Dict, Optional, Callable
import threading
import time
from pynput import keyboard
from utils.platform_utils import default_hotkeys

class ShortcutManager:
    """
    Manages global hotkeys using pynput. Hotkeys map Action enums (or stable keys)
    to combo strings like '<ctrl>+<alt>+t' or '<cmd>+<shift>+t'.

    This version is robust on macOS:
    - Rebinding creates a NEW listener generation and silences any stale callbacks.
    - Stop/start is serialized behind a lock with a tiny delay so the tap detaches.
    """

    def __init__(self, request_queue, hotkeys: Optional[Dict] = None):
        self.request_queue = request_queue
        self.hotkeys: Dict = dict(default_hotkeys)
        if hotkeys:
            self.hotkeys.update(hotkeys)

        self.listener: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.RLock()
        self._active_generation = 0  # increments every time we (re)start the listener

    # ----- Internal helpers -----
    def _on_trigger(self, action):
        self.request_queue.put(action)

    def _on_trigger_if_current(self, action, gen: int):
        # Ignore events from stale listeners
        if gen == self._active_generation:
            self._on_trigger(action)

    def _build_mapping(self, gen: int) -> Dict[str, Callable[[], None]]:
        """
        Build pynput's { '<combo>': callback } mapping.
        Capture both the action and the current generation in the closure.
        """
        mapping: Dict[str, Callable[[], None]] = {}
        for action, combo in self.hotkeys.items():
            if not combo:
                continue
            mapping[combo] = (lambda a=action, g=gen: self._on_trigger_if_current(a, g))
        return mapping

    def _restart_listener(self):
        with self._lock:
            # bump generation so any in-flight callbacks become no-ops
            self._active_generation += 1
            gen = self._active_generation

            # stop old listener if present
            if self.listener is not None:
                try:
                    self.listener.stop()
                except Exception:
                    pass
                self.listener = None
                # tiny delay lets CGEventTap detach cleanly on macOS
                time.sleep(0.08)

            mapping = self._build_mapping(gen)
            if not mapping:
                return  # nothing to listen for

            self.listener = keyboard.GlobalHotKeys(mapping)
            self.listener.start()
            print(f"[ShortcutManager] Rebound {len(mapping)} combo(s) (gen={gen}).")

    # ----- Public API -----
    def set_shortcut(self, action, shortcut: str):
        """Set/replace a single shortcut for an action."""
        with self._lock:
            self.hotkeys[action] = shortcut
        self._restart_listener()

    def remove_shortcut(self, action):
        """Remove a shortcut for an action (no-op if missing)."""
        with self._lock:
            if action in self.hotkeys:
                del self.hotkeys[action]
        self._restart_listener()

    def update_shortcuts(self, new_hotkeys: Dict):
        """
        Merge a dict of {Action-or-key: '<combo>'} into the current mapping,
        then rebuild the listener.
        """
        with self._lock:
            if new_hotkeys:
                self.hotkeys.update(new_hotkeys)
        self._restart_listener()

    def start_hotkey_listener(self):
        """Start (or restart) the global hotkey listener."""
        self._restart_listener()
        print("[ShortcutManager] hotkey_listener is running")

    def stop(self):
        """Stop the listener and clear it."""
        with self._lock:
            if self.listener is not None:
                try:
                    self.listener.stop()
                except Exception:
                    pass
                self.listener = None
            self._active_generation += 1  # invalidate any late callbacks

    # Optional utility for UI/debugging
    def get_hotkeys(self) -> Dict:
        """Return the current {Action-or-key: '<combo>'} mapping."""
        with self._lock:
            return dict(self.hotkeys)
