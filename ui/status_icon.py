# ui/status_icon.py
# Cross-platform status icon:
# - macOS: native NSStatusBar / NSMenu via PyObjC
# - Windows/Linux: pystray

import os, sys, platform

def _resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

IS_MAC = platform.system() == "Darwin"

if IS_MAC:
    # ---- macOS native status icon (PyObjC) ----
    from AppKit import (
        NSStatusBar, NSImage, NSMenu, NSMenuItem, NSApplication, NSApp
    )
    from Foundation import NSObject
    import objc

    class _MenuDelegate(NSObject):
        def initWithCallbacks_(self, callbacks):
            self = objc.super(_MenuDelegate, self).init()
            if self is None:
                return None
            self._on_quit, self._on_settings = callbacks
            return self

        def onSettings_(self, _sender):
            try:
                if callable(self._on_settings):
                    self._on_settings()
            except Exception:
                pass

        def onQuit_(self, _sender):
            try:
                if callable(self._on_quit):
                    self._on_quit()
            except Exception:
                pass

    class StatusIcon:
        def __init__(self, on_quit, on_settings):
            self._status_item = None
            self._delegate = None

            if NSApp is None:
                NSApplication.sharedApplication()

            bar = NSStatusBar.systemStatusBar()
            self._status_item = bar.statusItemWithLength_(-1)  # variable length

            # Icon (optional)
            icon_path = _resource_path("copycat_status.png")
            img = NSImage.alloc().initByReferencingFile_(icon_path)
            if img is not None:
                try:
                    img.setTemplate_(True)  # auto invert for dark/light menus
                except Exception:
                    pass
                btn = self._status_item.button()
                if btn:
                    btn.setImage_(img)

            # Menu + delegate
            menu = NSMenu.alloc().init()
            menu.setAutoenablesItems_(False)  # <-- keep items enabled even if target is custom
            self._delegate = _MenuDelegate.alloc().initWithCallbacks_((on_quit, on_settings))

            sel_settings = objc.selector(self._delegate.onSettings_, signature=b"v@:@")
            sel_quit     = objc.selector(self._delegate.onQuit_,     signature=b"v@:@")

            settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Settings…", sel_settings, "")
            settings_item.setTarget_(self._delegate)   # <-- IMPORTANT
            settings_item.setEnabled_(True)

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit CopyCat", sel_quit, "")
            quit_item.setTarget_(self._delegate)       # <-- IMPORTANT
            quit_item.setEnabled_(True)

            menu.addItem_(settings_item)
            menu.addItem_(quit_item)

            self._status_item.setMenu_(menu)

        def remove(self):
            try:
                if self._status_item is not None:
                    NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
                    self._status_item = None
            except Exception:
                pass

else:
    # ---- Windows/Linux via pystray ----
    from PIL import Image
    import pystray

    class StatusIcon:
        def __init__(self, on_quit, on_settings):
            icon_path = _resource_path("copycat_status.png")
            try:
                image = Image.open(icon_path)
            except Exception:
                image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

            menu = pystray.Menu(
                pystray.MenuItem("Settings…", lambda: on_settings() if callable(on_settings) else None),
                pystray.MenuItem("Quit CopyCat", lambda: on_quit() if callable(on_quit) else None),
            )
            self._icon = pystray.Icon("CopyCat", image, "CopyCat", menu)
            self._icon.run_detached()

        def remove(self):
            try:
                if getattr(self, "_icon", None):
                    self._icon.stop()
            except Exception:
                pass
