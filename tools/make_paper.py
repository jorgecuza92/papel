#!/usr/bin/env python3
"""
Build the off-white "paper" player mockups into OUT/.rockbox (wps + images + fonts) and a placeholder cover.

  python3 make_paper.py OP1_ASSETS MENU_MARK FONT_DIR WPS_SRC_DIR OP1_WPS OUT

OP1_ASSETS  folder with the OP_1 images (OP_backdrop.bmp, reel*.bmp, icons, pb*.bmp, mark.bmp)
MENU_MARK   45x27 [o] mark with magenta (transparent) background, black brackets
FONT_DIR    folder with the Heros / Courier .fnt files to ship
WPS_SRC_DIR folder with Paper-*.wps
OP1_WPS     current OP_1.wps (recoloured into OP_1-Paper.wps)

Colours: bitmaps use (247,239,239) for the paper colour. That is what F0ECE8 becomes on the iPod's
RGB565 screen, and Rockbox's bitmap loader rounds where the background colour setting truncates,
so (247,239,239) is the value both paths agree on.
"""
import os, re, shutil, sys
import numpy as np
from PIL import Image, ImageFilter

BG = np.array((247, 239, 239), float)
BLACK = np.array((0, 0, 0), float)
ORANGE = np.array((255, 80, 0), float)
GRAY = np.array((185, 182, 175), float)
TAPE = np.array((150, 146, 140), float)
MAGENTA = (255, 0, 255)


def recolor(im):
    """OP_1 dark-theme bitmap -> paper version. Black -> paper, white -> black, red -> orange,
    blue -> light grey, brown (tape path) -> mid grey; anti-aliased pixels keep their coverage."""
    a = np.asarray(im.convert('RGB')).astype(float)
    out = np.empty_like(a)
    h, w, _ = a.shape
    for y in range(h):
        for x in range(w):
            r, g, b = a[y, x]
            if (r, g, b) == MAGENTA:
                out[y, x] = MAGENTA
                continue
            if max(r, g, b) - min(r, g, b) <= 12:
                k, t = max(r, g, b) / 255, BLACK
            elif r > 2.5 * g and r > 2.5 * b:
                k, t = r / 246, ORANGE
            elif b > r and b > g:
                k, t = b / 170, GRAY
            else:
                k, t = r / 73, TAPE
            k = min(k, 1.0)
            out[y, x] = BG * (1 - k) + t * k
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def recolor_fast(im):
    """Same mapping for big pure-greyscale strips (reels): vectorised."""
    a = np.asarray(im.convert('RGB')).astype(float)
    k = (a.max(axis=2, keepdims=True) / 255)
    out = BG * (1 - k)
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def bar(w, h, colour):
    return Image.new('RGB', (w, h), tuple(int(c) for c in colour))


def cover(path, size=500, seed=7):
    """Neutral placeholder album art (not a real cover): grainy dusk gradient, pale disc, dark ridge."""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, size)[:, None, None]
    top, bot = np.array((38, 52, 74)), np.array((196, 128, 104))
    img = top * (1 - y) + bot * y + np.zeros((size, size, 3))
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.hypot(xx - size * 0.62, yy - size * 0.42)
    img[d < size * 0.13] = (236, 222, 200)
    ridge = size * (0.70 + 0.06 * np.sin(xx / size * 7.0) + 0.03 * np.sin(xx / size * 23.0))
    img[yy > ridge] = (22, 20, 24)
    img += rng.normal(0, 9, img.shape)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    im.save(path, quality=92)


def main():
    op1, menu_mark, font_dir, wps_src, op1_wps, out = sys.argv[1:7]
    R = os.path.join(out, '.rockbox')
    wps_dir, fnt_dir = os.path.join(R, 'wps'), os.path.join(R, 'fonts')
    os.makedirs(fnt_dir, exist_ok=True)
    for f in os.listdir(font_dir):
        if f.endswith('.fnt'):
            shutil.copy(os.path.join(font_dir, f), fnt_dir)

    # four new layouts: mark + progress bar images per skin
    bars = {'Paper-Sheet': (288, 2), 'Paper-Art': (240, 3), 'Paper-Label': (284, 6), 'Paper-Type': (288, 1)}
    for name, (w, h) in bars.items():
        d = os.path.join(wps_dir, name)
        os.makedirs(d, exist_ok=True)
        shutil.copy(menu_mark, os.path.join(d, 'mark.bmp'))
        bar(w, h, BLACK).save(os.path.join(d, 'pbfg.bmp'))
        bar(w, h, GRAY).save(os.path.join(d, 'pbbg.bmp'))
        shutil.copy(os.path.join(wps_src, name + '.wps'), wps_dir)
        bc = os.path.join(wps_src, 'barcode.bmp')
        if name == 'Paper-Type' and os.path.exists(bc):
            shutil.copy(bc, os.path.join(d, 'barcode.bmp'))

    # OP_1 reel player, recoloured
    d = os.path.join(wps_dir, 'OP_1-Paper')
    os.makedirs(d, exist_ok=True)
    for f in sorted(os.listdir(op1)):
        if not f.endswith('.bmp'):
            continue
        im = Image.open(os.path.join(op1, f))
        if f.startswith('reel'):
            res = recolor_fast(im)
        elif f.endswith('_icon.bmp'):                       # white key with black glyph -> black glyph on paper
            a = np.asarray(im.convert('RGB')).astype(float).max(axis=2, keepdims=True) / 255
            res = Image.fromarray(np.clip(BG * a + 0.5, 0, 255).astype(np.uint8))
        elif f == 'pb.bmp':
            res = Image.new('RGB', im.size, (0, 0, 0))      # slider: black
        else:
            res = recolor(im)
        res.save(os.path.join(d, f))
        print('recoloured', f)
    s = open(op1_wps).read()
    s = s.replace('%Vf(FFFFFF)', '%Vf(000000)')
    s = s.replace('%Vb(49392F)%Vf(000000)', '%Vf(000000)')            # artist line
    s = s.replace('%Vf(49392F)', '%Vf(000000)')                         # rule under the bar
    s = s.replace('%Vf(556471)', '%Vf(000000)')                         # battery, hold
    s = s.replace('#__OP_1\n', '#__OP_1 (paper / off-white version)\n', 1)
    assert 'FFFFFF' not in s and '49392F' not in s
    open(os.path.join(wps_dir, 'OP_1-Paper.wps'), 'w').write(s)

    cover(os.path.join(out, 'cover.jpg'))
    print('wrote', out)


if __name__ == '__main__':
    main()
