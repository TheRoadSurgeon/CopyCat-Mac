import sys

if sys.platform == "darwin":
    from AppKit import (
        NSStatusBar, NSVariableStatusItemLength,
        NSMenu, NSMenuItem, NSImage
    )
    import objc
else:
    NSStatusBar = NSVariableStatusItemLength = NSMenu = NSMenuItem = NSImage = None
    objc = None


class MacStatusIcon:
    """
    macOS menu bar icon for CopyCat.
    Appears when app runs and disappears when quitting.
    """

    def __init__(self, on_quit, on_settings):
        self.on_quit = on_quit
        self.on_settings = on_settings
        self.status_item = None

        if sys.platform != "darwin" or NSStatusBar is None:
            return

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self.status_item.button()

        # Use custom app icon if exists, else show CC text
        icon = NSImage.alloc().initWithContentsOfFile_("copycat_status.png")
        if icon:
            icon.setSize_((18, 18))
            button.setImage_(icon)
        else:
            button.setTitle_("CC")

        menu = NSMenu.alloc().init()

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings", "settingsAction:", ""
        )
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit CopyCat", "quitAction:", ""
        )

        settings_item.setTarget_(self)
        quit_item.setTarget_(self)

        menu.addItem_(settings_item)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def settingsAction_(self, sender):
        if self.on_settings:
            self.on_settings()

    def quitAction_(self, sender):
        if self.on_quit:
            self.on_quit()

    if objc:
        @objc.python_method
        def remove(self):
            if self.status_item is not None:
                NSStatusBar.systemStatusBar().removeStatusItem_(self.status_item)
                self.status_item = None
    else:
        def remove(self):
            pass
