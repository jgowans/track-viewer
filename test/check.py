#!/usr/bin/env python3
"""Load GPX files into index.html in headless Chrome and print what the page computed.

A page opened from file:// can't fetch a local GPX, so each run writes a throwaway copy of
index.html that pulls the GPX in through a <script> tag and calls window.loadGpxText().
The page's own JS does all the work; this script only reports the result.

    test/check.py [--screenshot DIR] [--tz ZONE] [--smooth SECONDS] [--race HH:MM-HH:MM] FILE.gpx...

Needs google-chrome or chromium on PATH (or CHROME=/path/to/chrome) and internet access
for the CDN libraries and map tiles.
"""
import argparse, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Runs after the page's own script. Waits for uPlot's deferred redraws, then dumps state as JSON.
PROBE = """
<script src="gpxdata.js"></script>
<script>
const t0 = performance.now();
settings.smoothS = SMOOTH_S; document.getElementById('smooth').value = String(SMOOTH_S);
loadGpxText(window.GPX_TEXT, 'test');
if (RACE) { [raceStart.value, raceEnd.value] = RACE; setRaceFromBoxes(); }
const loadMs = Math.round(performance.now() - t0);
setTimeout(() => {
  const rows = id => [...document.querySelectorAll(id + ' tr')].map(r => [...r.cells].map(c => c.textContent));
  const out = {
    errors: window.__errs, status: document.getElementById('status').textContent,
    name: document.getElementById('trackName').textContent, loadMs,
  };
  if (track) Object.assign(out, {
    fixes: track.n, speedBreaks: an.breaks, trackLayers: trackLayer.getLayers().length,
    charts: charts.length, stats: rows('#stats'), turns: rows('#turns'),
  });
  const d = document.createElement('pre'); d.id = '__dump'; d.textContent = JSON.stringify(out);
  document.body.append(d);
}, 500);
</script>
"""
CATCH = "<script>window.__errs = []; addEventListener('error', e => __errs.push(e.message));</script>"


def chrome():
    exe = os.environ.get('CHROME') or next(
        (c for c in ('google-chrome', 'chromium', 'chromium-browser') if shutil.which(c)), None)
    if not exe:
        sys.exit('No Chrome found; set CHROME=/path/to/chrome')
    return exe


def run(gpx, tz, smooth, race, shot):
    page = (ROOT / 'index.html').read_text()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / 'gpxdata.js').write_text('window.GPX_TEXT = ' + json.dumps(pathlib.Path(gpx).read_text()) + ';')
        probe = PROBE.replace('SMOOTH_S', str(smooth)).replace('RACE', json.dumps(race.split('-') if race else None))
        (tmp / 'test.html').write_text(page.replace('<head>', '<head>' + CATCH, 1).replace('</body>', probe + '</body>', 1))
        args = [chrome(), '--headless=new', '--disable-gpu', '--window-size=1600,1000', '--virtual-time-budget=20000']
        env = {**os.environ, 'TZ': tz}
        url = (tmp / 'test.html').as_uri()
        # Each launch gets its own profile: a second Chrome on a profile still held by the first exits without output.
        dom = subprocess.run(args + [f'--user-data-dir={tmp / "p1"}', '--dump-dom', url],
                             capture_output=True, text=True, env=env, timeout=120).stdout
        if shot:
            pathlib.Path(shot).unlink(missing_ok=True)
            subprocess.run(args + [f'--user-data-dir={tmp / "p2"}', f'--screenshot={shot}', url],
                           capture_output=True, env=env, timeout=120)
    m = re.search(r'<pre id="__dump">(.*?)</pre>', dom, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {'errors': ['page produced no output']}


def table(rows):
    widths = [max(len(r[i]) for r in rows if i < len(r)) for i in range(max(map(len, rows)))]
    return '\n'.join('  ' + '  '.join(c.rjust(w) if i else c.ljust(w) for i, (c, w) in enumerate(zip(r, widths))) for r in rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gpx', nargs='+')
    ap.add_argument('--tz', default='Africa/Johannesburg', help='browser time zone (default %(default)s)')
    ap.add_argument('--smooth', type=int, default=20, choices=[6, 10, 20, 30, 60], help='smoothing in seconds (default %(default)s)')
    ap.add_argument('--race', metavar='HH:MM-HH:MM', help='only analyse the race window, e.g. 09:00-16:30:00')
    ap.add_argument('--screenshot', metavar='DIR', help='also save DIR/<file>.png at 1600x1000')
    a = ap.parse_args()
    failed = False
    for gpx in a.gpx:
        shot = a.screenshot and str(pathlib.Path(a.screenshot) / (pathlib.Path(gpx).stem + '.png'))
        r = run(gpx, a.tz, a.smooth, a.race, shot)
        failed |= bool(r.get('errors') or r.get('status'))
        print(f"== {gpx}\n  {r.get('name')}: {r.get('fixes')} fixes, loaded in {r.get('loadMs')} ms, "
              f"speed class breaks {r.get('speedBreaks')} kn, {r.get('trackLayers')} track polylines")
        if r.get('errors') or r.get('status'):
            print(f"  ERRORS: {r.get('errors')} status: {r.get('status')!r}")
        for key in ('stats', 'turns'):
            if r.get(key):
                print(table(r[key]))
        if shot:
            ok = pathlib.Path(shot).exists()
            failed |= not ok
            print(f'  screenshot: {shot}' if ok else f'  ERROR: no screenshot written to {shot}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
