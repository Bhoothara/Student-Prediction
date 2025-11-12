# save as create_icons.py then run: python create_icons.py
from PIL import Image
import os

src = 'static/icons/source_icon.png'   # put your original square PNG here (any size)
out_dir = 'static/icons'
os.makedirs(out_dir, exist_ok=True)

if not os.path.exists(src):
    raise SystemExit("Put your original square PNG at static/icons/source_icon.png and re-run.")

img = Image.open(src).convert('RGBA')

sizes = [(192, 'icon-192.png'), (512, 'icon-512.png'), (1024, 'icon-1024.png')]
for size, name in sizes:
    im = img.copy()
    im = im.resize((size, size), Image.LANCZOS)
    out = os.path.join(out_dir, name)
    im.save(out, format='PNG')
    print("Saved", out)
