#!/usr/bin/env python3
"""
Assemble the public papel-rockbox repo from the working files in ~/claude/ipod-rockbox.

    python3 package_papel_rockbox.py OUT_DIR

Public names: papel.wps (player), papel-menu.sbs (menus), papel-sheet/art/label.wps (alternate players),
Courier-Prime-Papel .fnt, english-papel.lng, themes/papel*.cfg. Writes theme/ (full, needs the papél
firmware) and theme-stock/ (standard Rockbox 4.0: no wrap/year/case features).
"""
import os, re, shutil, sys, zipfile

W = os.path.expanduser('~/claude/ipod-rockbox')
OUT = os.path.abspath(sys.argv[1])
PP = f'{W}/paper-players/.rockbox'
CFL = '/tmp/cfl'                         # unpacked courier-fit-light.zip (menu skin + Courier fonts)

PLAYERS = {'Paper-Type': 'papel', 'Paper-Sheet': 'papel-sheet', 'Paper-Art': 'papel-art', 'Paper-Label': 'papel-label'}
FONT_RENAME = lambda s: s.replace('Courier-Prime-Abloh', 'Courier-Prime-Papel')


def clean_header(text, header):
    """drop the leading #__ comment block and put our own header in front"""
    lines = text.split('\n')
    i = 0
    while i < len(lines) and (lines[i].startswith('#__') or lines[i].strip() == '#'):
        i += 1
    return header.rstrip('\n') + '\n' + '\n'.join(lines[i:])


def stockify_player(text):
    """standard Rockbox 4.0 has no %ss wrap/year flags: album on one scrolling line, year = first 4 chars"""
    text = re.sub(r'#__album, line 1\n(%V\([^\n]*\n)%al%ss\(0,-,%id,wrap1\)\n', r'#__album (scrolls when long)\n\1%al%s%id\n', text)
    text = re.sub(r'#__album, line 2[^\n]*\n%V\([^\n]*\n%al%s%ss\(0,-,%id,wrap2\)%\?ss\(0,-,%id,wrap2\)<%Vd\(f2\)\|%Vd\(f1\)>\n',
                  '#__shows the year line\n%V(0,0,1,1,-)\n%Vd(f1)\n', text)
    text = text.replace('%ss(0,-,%iy,year)', '%ss(0,4,%iy)')
    assert 'wrap' not in text and ',year)' not in text, 'stockify failed'
    return text


def build_theme(dst, stock):
    R = f'{dst}/.rockbox'
    for d in ('wps', 'fonts', 'langs', 'themes'):
        os.makedirs(f'{R}/{d}', exist_ok=True)
    needed_fonts = set()
    # players
    for src, name in PLAYERS.items():
        t = FONT_RENAME(open(f'{PP}/wps/{src}.wps').read())
        hdr = {'papel': '#__papél player: big type. barcode + [o]TM on the header row, lowercase title, "ARTIST" / album / C. year.',
               'papel-sheet': '#__papél player, alternate: spec sheet with hairline rows.',
               'papel-art': '#__papél player, alternate: album art with the title running across it.',
               'papel-label': '#__papél player, alternate: industrial label grid.'}[name]
        hdr += '\n#__c/o Jorge Cuza, CC BY 4.0. github.com/jorgecuza92/papel\n#__320x240 (iPod Video)'
        hdr += '\n#__standard Rockbox 4.0 edition' if stock else '\n#__needs the papél firmware for lowercase/caps, album wrap and C. year'
        t = clean_header(t, hdr)
        if stock and name == 'papel':
            t = stockify_player(t)
        open(f'{R}/wps/{name}.wps', 'w').write(t)
        shutil.copytree(f'{PP}/wps/{src}', f'{R}/wps/{name}', dirs_exist_ok=True)
        needed_fonts |= set(re.findall(r'%Fl\(\d+,([^)]+)\)', t))
    # menu
    m = FONT_RENAME(open(f'{CFL}/wps/Courier-Prime-Paper.sbs').read())
    m = clean_header(m, '#__papél menu: one [item] per screen, lowercase, corner ticks, [o]TM top right.\n'
                        '#__c/o Jorge Cuza, CC BY 4.0. github.com/jorgecuza92/papel\n#__320x240 (iPod Video)')
    open(f'{R}/wps/papel-menu.sbs', 'w').write(m)
    shutil.copytree(f'{CFL}/wps/Courier-Prime-Paper', f'{R}/wps/papel-menu', dirs_exist_ok=True)
    needed_fonts |= set(re.findall(r'%Fl\(\d+,([^)]+)\)', m))
    needed_fonts.add('14-Courier-Prime-Papel.fnt')      # the UI font
    # fonts
    pool = {}
    for d in (f'{PP}/fonts', f'{CFL}/fonts'):
        for f in os.listdir(d):
            pool[FONT_RENAME(f)] = f'{d}/{f}'
    for f in sorted(needed_fonts):
        shutil.copy(pool[f], f'{R}/fonts/{f}')
    # language + database menu
    shutil.copy(f'{W}/lang/english-lowercase.lng', f'{R}/langs/english-papel.lng')
    shutil.copy(f'{W}/lang/tagnavi_user.config', f'{R}/tagnavi_user.config')
    # theme cfgs
    base = ('# papél: off-white menus, big-type player. c/o Jorge Cuza, CC BY 4.0\n'
            'wps: /.rockbox/wps/{wps}.wps\nsbs: /.rockbox/wps/papel-menu.sbs\n'
            'font: /.rockbox/fonts/14-Courier-Prime-Papel.fnt\nlang: /.rockbox/langs/english-papel.lng\n'
            'backdrop: -\nforeground color: 000000\nbackground color: F0ECE8\nstatusbar: off\nscrollbar: off\n'
            'show icons: off\nui viewport: -\nselector type: bar (inverse)\n')
    for name in PLAYERS.values():
        open(f'{R}/themes/{name}.cfg', 'w').write(base.format(wps=name))
    return sorted(needed_fonts)


def main():
    if os.path.exists(OUT):
        for p in ('theme', 'theme-stock'):
            shutil.rmtree(f'{OUT}/{p}', ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    fonts = build_theme(f'{OUT}/theme', stock=False)
    build_theme(f'{OUT}/theme-stock', stock=True)
    print('fonts:', ', '.join(fonts))


if __name__ == '__main__':
    main()
