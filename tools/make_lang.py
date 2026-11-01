#!/usr/bin/env python3
"""
Make a re-cased copy of Rockbox's english.lang (all-caps or lowercase UI text), then compile it with genlang.

  python3 make_lang.py --case upper --title IPOD --short --tagnavi tagnavi_user.config --build rb40/build --out english-caps.lng

--build is a configured Rockbox build dir (its genlang-features must match the firmware the .lng is for:
use rb40/build for the iPod, rb40/build-sim for the simulator). Copy the .lng to /.rockbox/langs/ and pick
it in Settings > General Settings > Language (or `lang: /.rockbox/langs/<name>.lng` in config.cfg).
--short abbreviates menu text TE style (SYSTEM -> SYS); --tagnavi writes the database menu with the same
abbreviations, copy it to /.rockbox/tagnavi_user.config.
"""
import argparse, glob, os, re, subprocess, tempfile

UNDERSCORE = False  # --underscore: spaces in abbreviated menu text become _
FMT = re.compile(r'(%[-+ #0-9.]*[a-zA-Z]|\$[a-zA-Z]|\\[nt])')     # printf / list-format codes stay as they are
SKIP = re.compile(r'FORMAT|VOICED|KEYBOARD|_DATE_|_TIME_|UNIT_|LANGUAGE_NAME')
MENU_SRC = ['apps/menus/*.c', 'apps/root_menu.c', 'apps/settings_list.c', 'apps/onplay.c', 'apps/tree.c',
            'apps/playlist_viewer.c', 'apps/tagtree.c']
# whole strings first, then single words
SHORT = {
    'NOW PLAYING': 'NOW', 'RESUME PLAYBACK': 'RES', 'FILES': 'FIL', 'FM RADIO': 'FM', 'FM RADIO MENU': 'FM MENU',
    'RECENT BOOKMARKS': 'BKM', 'ROCKBOX INFO': 'INFO', 'DEBUG (KEEP OUT!)': 'DEBUG', 'LEGAL NOTICES': 'LEGAL',
    'RUNNING TIME': 'RUNTIME', 'TIME & DATE': 'TIME', 'SET TIME/DATE': 'SET TIME', 'SHOW TRACK INFO': 'INFO',
    'VIEW ALBUM ART': 'ART', 'WHILE PLAYING SCREEN': 'WPS', "WHAT'S PLAYING SCREEN": 'WPS',
    'REMOTE WHILE PLAYING SCREEN': 'RMT WPS', 'ADD TO PLAYLIST...': 'ADD TO PLST', 'OPEN WITH...': 'OPEN WITH',
    'PLAYING NEXT...': 'PLAY NEXT', 'QUEUE...': 'QUEUE', 'SET AS...': 'SET AS', 'FAST-FORWARD/REWIND': 'FF/RW',
    'STARTUP/SHUTDOWN': 'POWER', 'STATUS-/SCROLLBAR': 'BARS', 'MAIN MENU': 'MENU', '<ALL TRACKS>': '<ALL>',
    # database (tagnavi_user.config)
    'FIRST LETTER': 'A-Z', 'BY FIRST LETTER...': 'A-Z', 'SEARCH BY...': 'SEARCH', 'SHUFFLE SONGS': 'SHUF',
    'USER RATING': 'RATING', 'RECENTLY ADDED': 'NEW', 'PLAYBACK HISTORY': 'HIST', 'CUSTOM MENU': 'CUSTOM',
    'SAME AS CURRENTLY PLAYED TRACK': 'SAME', 'MOST PLAYED (PLAYS|SCORE)': 'TOP', 'RECENTLY PLAYED TRACKS': 'RECENT',
    'NEVER PLAYED TRACKS': 'UNPLAYED', 'FAVOURITE ARTISTS': 'FAV ARTIST', 'FAVOURITE ALBUMS': 'FAV ALB',
    'RECENT FAVOURITES': 'RECENT FAV', 'NEW FAVOURITES': 'NEW FAV', 'FORGOTTEN FAVOURITES': 'OLD FAV',
    'TITLE (WITH TRACK DURATION)': 'TITLE + TIME', 'ALBUMS BETWEEN YEARS': 'ALB YRS', 'ARTISTS BETWEEN YEARS': 'ARTIST YRS',
    'ALBUMS BY YEAR': 'ALB YR', 'ALBUM ARTIST': 'ALB ARTIST', 'ALBUM ARTISTS': 'ALB ARTISTS',
}
WORDS = {
    'SETTINGS': 'SET', 'SETTING': 'SET', 'SYSTEM': 'SYS', 'DATABASE': 'DB', 'PLAYLISTS': 'PLS', 'PLAYLIST': 'PLST',
    'PLUGINS': 'PLG', 'PLUGIN': 'PLUG', 'SHORTCUTS': 'SHT', 'BOOKMARKS': 'BKMK', 'BOOKMARK': 'BKMK',
    'BOOKMARKING': 'BKMK', 'RECORDING': 'REC', 'PLAYBACK': 'PLAY', 'PLAYING': 'PLAY', 'DISPLAY': 'DISP',
    'GENERAL': 'GEN', 'SOUND': 'SND', 'DIRECTORY': 'DIR', 'DIRECTORIES': 'DIRS', 'CURRENT': 'CUR',
    'BROWSER': 'BRWS', 'BROWSE': 'BRWS', 'EQUALIZER': 'EQ', 'ADVANCED': 'ADV', 'CONTROLS': 'CTRL',
    'CONTROL': 'CTRL', 'COLOURS': 'CLRS', 'COLOUR': 'CLR', 'BACKGROUND': 'BG', 'FOREGROUND': 'FG',
    'SECONDARY': 'SEC', 'PRIMARY': 'PRI', 'BACKLIGHT': 'BKLT', 'CROSSFADE': 'XFADE', 'CROSSFEED': 'XFEED',
    'SHUFFLED': 'SHUF', 'SHUFFLE': 'SHUF', 'SHUFFLING': 'SHUF', 'REPEAT': 'RPT', 'LANGUAGE': 'LANG',
    'BATTERY': 'BATT', 'REMOTE': 'RMT', 'MAXIMUM': 'MAX', 'MINIMUM': 'MIN', 'AUTOMATIC': 'AUTO', 'MANUAL': 'MAN',
    'PRESETS': 'PRST', 'PRESET': 'PRST', 'NOTIFICATIONS': 'NOTIF', 'CREDITS': 'CRED', 'FREQUENCY': 'FREQ',
    'SCROLLING': 'SCRL', 'SCROLL': 'SCRL', 'MODIFICATIONS': 'MODS', 'SELECT': 'SEL', 'PREVIOUS': 'PREV',
    'SCREEN': 'SCRN', 'TRACKS': 'TRKS', 'TRACK': 'TRK', 'DELETE': 'DEL',
    'PROPERTIES': 'PROPS', 'APPLICATIONS': 'APPS', 'MULTIMEDIA': 'MEDIA', 'MANAGE': 'MNG', 'EXEMPTIONS': 'EXMPT',
    'EXEMPT': 'EXMPT', 'CALIBRATION': 'CAL', 'CALIBRATE': 'CAL', 'HEADPHONE': 'HP', 'KEYCLICK': 'CLICK',
    'COMPRESSOR': 'COMP', 'REPLAYGAIN': 'RGAIN', 'PICTUREFLOW': 'PFLOW', 'TOUCHSCREEN': 'TOUCH', 'ENCODER': 'ENC',
    'PERFORMANCE': 'PERF', 'CHANNELS': 'CH', 'TRIGGER': 'TRIG', 'NUMBERS': 'NUM', 'NUMERIC': 'NUM',
    'GRAPHICAL': 'GFX', 'GRAPHIC': 'GFX', 'SURROUND': 'SURR', 'ENHANCEMENT': 'ENH', 'INTERVAL': 'INT',
    'HISTOGRAM': 'HIST', 'VIEWER': 'VIEW', 'CATALOGUE': 'CAT', 'VOLUME': 'VOL', 'CLOCK': 'CLK', 'HOUR': 'HR',
    'ALARM': 'ALRM', 'CREATE': 'NEW', 'RECURSIVELY': 'RECURSE', 'ALPHABETICAL': 'A-Z', 'DESCENDING': 'DESC',
    'ASCENDING': 'ASC',  'FILENAME': 'FILE', 'COMMENT': 'CMNT',
    'INITIALIZE': 'INIT', 'PRESENTATION': 'LAYOUT', 'SEPARATOR': 'SEP', 'SELECTOR': 'SEL', 'GRADIENT': 'GRAD',
    'INVERSE': 'INV', 'EMBEDDED': 'EMBED', 'EXTERNAL': 'EXT', 'REMINDERS': 'RMND',
    'UNMAPPED': 'UNMAP', 'MODIFIED': 'MOD', 'BACKDROP': 'BKDP',
}


def menu_ids(root):
    ids = set()
    for pat in MENU_SRC:
        for path in glob.glob(os.path.join(root, pat)):
            ids |= set(re.findall(r'ID2P\((LANG_[A-Z0-9_]+)\)', open(path, encoding='utf-8', errors='replace').read()))
    return ids


def shorten(text):
    """Abbreviate an upper-case string; messages and prompts are left alone."""
    if text in SHORT:
        return SHORT[text].replace(' ', '_') if UNDERSCORE else SHORT[text]
    if '?' in text or '!' in text:
        return text
    text = re.sub(r'[A-Z]+', lambda m: WORDS.get(m.group(), m.group()), text)
    return text.replace(' ', '_') if UNDERSCORE else text


def recase(text, case, short=False):
    if short and not FMT.search(text):
        text = shorten(text.upper())
    parts = FMT.split(text)
    f = str.upper if case == 'upper' else str.lower
    return ''.join(p if FMT.fullmatch(p) else f(p) for p in parts)


def tagnavi(root, case, out):
    """Copy of tagnavi.config with the menu labels and titles re-cased and abbreviated."""
    lines = []
    for line in open(os.path.join(root, 'apps/tagnavi.config'), encoding='utf-8'):
        m = re.match(r'^(%menu_start "[^"]+" |%byfirstletter "[^"]+" )?"([^"]+)"(.*)$', line)
        if m and (m.group(1) or re.match(r'\s*(->|==>|~>)', m.group(3))):
            line = f'{m.group(1) or ""}"{recase(m.group(2), case, True)}"{m.group(3)}\n'
        lines.append(line)
    open(out, 'w', encoding='utf-8').write(''.join(lines))
    print('wrote', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', choices=['upper', 'lower'], required=True)
    ap.add_argument('--title', help='replacement for the "Rockbox" main menu title (genlang strips quote characters)')
    ap.add_argument('--short', action='store_true', help='TE-style abbreviations for menu text')
    ap.add_argument('--underscore', action='store_true', help='with --short: snd_set instead of snd set')
    ap.add_argument('--tagnavi', help='also write an abbreviated database menu (tagnavi_user.config) here')
    ap.add_argument('--build', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    global UNDERSCORE
    UNDERSCORE = a.underscore

    root = os.path.dirname(os.path.abspath(a.build.rstrip('/')))
    english = os.path.join(root, 'apps/lang/english.lang')
    short = menu_ids(root) if a.short else set()
    if a.tagnavi:
        tagnavi(root, a.case, a.tagnavi)
    out, phrase_id, in_dest = [], '', False
    for line in open(english, encoding='utf-8'):
        s = line.strip()
        if s.startswith('id:'):
            phrase_id = s[3:].strip()
        elif s == '<dest>':
            in_dest = True
        elif s == '</dest>':
            in_dest = False
        elif in_dest and not SKIP.search(phrase_id):
            m = re.match(r'(\s*[^:]+:\s*)"(.*)"\s*$', line)
            if m and m.group(2) not in ('', 'none'):
                text = recase(m.group(2), a.case, phrase_id in short)
                if phrase_id == 'LANG_ROCKBOX_TITLE' and a.title:
                    text = a.title
                line = f'{m.group(1)}"{text}"\n'
        out.append(line)

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'custom.lang')
        open(src, 'w', encoding='utf-8').write(''.join(out))
        mk = open(os.path.join(a.build, 'Makefile')).read()
        model = re.search(r'^export MODELNAME=(\S+)', mk, re.M).group(1)
        tid = re.search(r'^export TARGET_ID=(\S+)', mk, re.M).group(1)
        feats = open(os.path.join(a.build, 'apps/genlang-features')).read().strip()
        subprocess.run(['perl', os.path.join(root, 'tools/genlang'), f'-e={english}', f'-t={model}:{feats}',
                        f'-i={tid}', f'-b={os.path.abspath(a.out)}', src], check=True, cwd=tmp)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
