# System tray / menu bar icon management
from pystray import Icon, Menu, MenuItem
from utils.icon_utils import create_icon_image
# === Tray Icon ===
def create_image():
    img = Image.new('RGB', (64, 64), color="black")
    d = ImageDraw.Draw(img)
    d.rectangle([16, 16, 48, 48], fill="white")
    return img

def on_quit(icon, item):
    icon.stop()

def start_tray():
    icon = Icon("Clipboard Manager",
                create_image(),
                menu=Menu(MenuItem('Quit', on_quit)))
    icon.run()