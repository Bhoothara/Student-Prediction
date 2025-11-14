# save as make_icons.py and run: python make_icons.py
from PIL import Image

sizes = [(1024, 'icon-1024.png'), (512, 'icon-512.png'), (192, 'icon-192.png')]
import os
os.makedirs('static/icons', exist_ok=True)
for size, name in sizes:
    im = Image.new('RGBA', (size[0], size[0]), (0,124,240,255))  # blue bg
    im.save(os.path.join('static','icons', name))
print("icons created in static/icons")
