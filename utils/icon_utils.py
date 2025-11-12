from PIL import Image, ImageDraw

def create_icon_image():
    img = Image.new('RGB', (64, 64), color="black")
    d = ImageDraw.Draw(img)
    d.rectangle([16, 16, 48, 48], fill="white")
    return img