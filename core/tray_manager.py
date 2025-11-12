# handles logic for tray icon (menu bar for mac and system tray for windows)
from pystray import Icon, Menu, MenuItem
from utils.icon_utils import create_icon_image

def on_quit(icon, item):
    icon.stop()

def start_tray():
    icon = Icon("Clipboard Manager",
                create_icon_image(),
                menu=Menu(MenuItem('Quit', on_quit)))
    icon.run()