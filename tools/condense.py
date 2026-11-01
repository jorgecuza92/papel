"""Make a horizontally condensed copy of a monospaced TTF.
glyph outlines scaled by SX (letters get narrower), advance scaled by AX (cell width);
AX > SX leaves extra space between letters, split evenly on both sides of each glyph."""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
src, dst, SX, AX, NAME = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
FIT_MARGIN = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0   # keep ink this fraction of the advance away from each cell edge (extra squeeze for wide glyphs only)
f = TTFont(src)
gs = f.getGlyphSet(); glyf = f['glyf']; hmtx = f['hmtx']
new = {}
for g in f.getGlyphOrder():
    adv, lsb = hmtx[g]
    nadv = round(adv * AX)
    dx = (nadv - adv * SX) / 2.0
    pen = TTGlyphPen(gs)
    gs[g].draw(TransformPen(pen, (SX, 0, 0, 1, dx, 0)))
    gl = pen.glyph(); gl.recalcBounds(glyf)
    if FIT_MARGIN and getattr(gl, 'numberOfContours', 0) and hasattr(gl, 'xMin'):
        lo, hi = FIT_MARGIN * nadv, nadv * (1 - FIT_MARGIN)
        if gl.xMin < lo or gl.xMax > hi:
            k = (hi - lo) / float(gl.xMax - gl.xMin); cx = (gl.xMin + gl.xMax) / 2.0
            pen = TTGlyphPen(gs)
            gs[g].draw(TransformPen(pen, (SX * k, 0, 0, 1, nadv / 2.0 + (dx - cx) * k + (cx - nadv / 2.0) * 0, 0)))
            gl = pen.glyph(); gl.recalcBounds(glyf)
            # re-centre the narrowed glyph in its cell
            shift = nadv / 2.0 - (gl.xMin + gl.xMax) / 2.0
            pen = TTGlyphPen(gs)
            gs[g].draw(TransformPen(pen, (SX * k, 0, 0, 1, nadv / 2.0 + (dx - cx) * k + shift, 0)))
            gl = pen.glyph(); gl.recalcBounds(glyf)
    new[g] = (gl, nadv)
for g, (gl, nadv) in new.items():
    glyf[g] = gl
    gl.recalcBounds(glyf)
    hmtx[g] = (nadv, getattr(gl, 'xMin', 0) or 0)
for t in ('fpgm', 'prep', 'cvt ', 'hdmx', 'LTSH', 'VDMX', 'kern', 'GPOS', 'DSIG'):
    if t in f: del f[t]
f['hhea'].advanceWidthMax = max(a for a, _ in hmtx.metrics.values())
if 'OS/2' in f: f['OS/2'].xAvgCharWidth = round(f['OS/2'].xAvgCharWidth * AX)
for rec in f['name'].names:
    if rec.nameID in (1, 3, 4, 6, 16):
        rec.string = NAME if rec.nameID != 6 else NAME.replace(' ', '')
f.save(dst)
print('wrote', dst)
