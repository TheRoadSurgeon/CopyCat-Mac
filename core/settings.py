# core/settings.py
# Global access to the app's SettingsManager singleton.
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from threading import RLock

if TYPE_CHECKING:
    # Only for type hints; no runtime import cycles.
    from .settings_manager import SettingsManager

# You can still assign to this directly if you prefer:
#   import core.settings as s
#   s.SETTINGS_MANAGER = SettingsManager(...)
SETTINGS_MANAGER: Optional["SettingsManager"] = None

# Internal lock in case initialization happens from multiple places.
_lock = RLock()


def set_settings_manager(manager: "SettingsManager") -> None:
    """Initialize or replace the global SettingsManager."""
    global SETTINGS_MANAGER
    with _lock:
        SETTINGS_MANAGER = manager


def get_settings_manager() -> Optional["SettingsManager"]:
    """Return the global SettingsManager or None if not initialized yet."""
    return SETTINGS_MANAGER


def require_settings_manager() -> "SettingsManager":
    """
    Return the global SettingsManager, raising if it's not set.
    Useful in places that cannot proceed without it.
    """
    sm = get_settings_manager()
    if sm is None:
        raise RuntimeError("SettingsManager not initialized yet.")
    return sm
