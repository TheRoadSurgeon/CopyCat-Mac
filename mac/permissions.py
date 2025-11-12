# mac/permissions.py
# macOS Accessibility & Input Monitoring checks and helpers.
import platform, subprocess

if platform.system() == "Darwin":
    from Cocoa import NSDictionary, NSNumber
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    from Quartz import (
        CGEventTapCreate,
        kCGHIDEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly,
        kCGEventKeyDown,
        CGEventMaskBit,
    )
else:
    # Stubs for non-mac platforms, so imports don't crash.
    NSDictionary = NSNumber = AXIsProcessTrustedWithOptions = kAXTrustedCheckOptionPrompt = None
    CGEventTapCreate = kCGHIDEventTap = kCGHeadInsertEventTap = kCGEventTapOptionListenOnly = None
    kCGEventKeyDown = CGEventMaskBit = None


def ensure_accessibility_trust(prompt: bool = True) -> bool:
    """
    Returns True if the app is trusted for Accessibility (can send keystrokes).
    If prompt=True and not trusted, macOS will show the Accessibility permission dialog.
    """
    if platform.system() != "Darwin":
        return True

    opts = None
    if prompt:
        # { kAXTrustedCheckOptionPrompt: True }
        opts = NSDictionary.dictionaryWithObject_forKey_(
            NSNumber.numberWithBool_(True), kAXTrustedCheckOptionPrompt
        )
    return bool(AXIsProcessTrustedWithOptions(opts))


def has_input_monitoring() -> bool:
    """
    Returns True if we can create a listen-only keyboard event tap,
    which implies the app is allowed under Input Monitoring.
    """
    if platform.system() != "Darwin":
        return True

    try:
        mask = CGEventMaskBit(kCGEventKeyDown)
        tap = CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            None,
            None,
        )
        return bool(tap)
    except Exception:
        return False


def open_accessibility_pane():
    # Opens System Settings to Accessibility privacy pane
    try:
        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
            check=False,
        )
    except Exception:
        pass


def open_input_monitoring_pane():
    # Input Monitoring pane (anchor name varies across macOS versions)
    for anchor in ("Privacy_KeyboardInputMonitoring", "Privacy_ListenEvent"):
        try:
            subprocess.run(
                ["open", f"x-apple.systempreferences:com.apple.preference.security?{anchor}"],
                check=False,
            )
            return
        except Exception:
            continue
