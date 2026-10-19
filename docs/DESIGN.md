# Track viewer: design and implementation notes

This document records what the viewer is for, the decisions made so far and why, how the code fits together, how to test it, and what is known to be wrong or missing. It is written so the work can be resumed without the original conversation. The user-facing description is in [`../README.md`](../README.md).

Status as of October 2026: working prototype, one static page (`index.html`), tested in headless Chrome against four real tracks.

## 1. Purpose

The user races keelboats out of Cape Town and records each race with a Garmin watch. After a race they want to review their own track to learn and improve. In their words: *"I know what my boat should be doing and I want to see what it did."*

So the page answers: where was the boat fast or slow, which way was it going, how did the stretches of the race compare with each other, and what did each turn cost?

### Non-goals for now

These were discussed and deliberately deferred (see section 8):

- Wind, true wind angle, VMG and polar comparison. The watch records no wind.
- Course models: marks, rounding detection, start-line analysis, defined legs.
- Comparing several boats or races.
- Saving anything between sessions, apart from the chosen time zone.
- Heart rate. It is in the GPX but comes from the watch, so it is ignored.

### Constraints the user set

- A static HTML file opened straight from disk, with the GPX chosen from a file picker. No server.
- Internet access is fine, so libraries and map tiles can come from the web.
- Personal, non-commercial use, which allows the free tile services below.

## 2. What the data looks like

Garmin Connect exports GPX 1.1 with a single `<trk>`/`<trkseg>`. Each `<trkpt>` has `lat`, `lon`, `<ele>`, `<time>` and a heart-rate extension.

- **Fix interval:** 1–10 s, median 2–3 s.
- **Position noise:** a few metres, so point-to-point speeds are noisy. The raw 99th percentile on the 2024 track was 9.1 kn against about 7.5 kn after smoothing.
- **Elevation:** varies by about ±6 m at sea. It is GPS noise and is ignored.
- **No heading or wind:** there is no heading, boat speed through the water, depth or wind. All speeds and courses are over the ground (SOG, COG), so they include current and leeway.
- **Gaps:** the watch sometimes stops logging for minutes at a time (see section 6).
- **Track name:** always "Cape Town sail", with type `other`.

## 3. Decisions and the reasons for them

### 3.1 One static page opened from `file://`

- Browsers block `fetch()` of other local files from a `file://` page, so the GPX comes in through `<input type="file">` or drag and drop, read with `File.text()` and parsed with `DOMParser`.
- Chrome also blocks JavaScript modules (`<script type="module">`) on `file://` pages. If the code is split into several files, use plain `<script src>` files, not modules.
- `localStorage` works on `file://` in Chrome and stores the chosen time zone (`trackViewer.tz`).
- Nothing listens on the network. A local server was considered and rejected, partly because the user wanted to open a file and partly because it adds a listening socket.

### 3.2 Libraries

| Library | Version | Used for | Why this one |
|---|---|---|---|
| Leaflet | 1.9.4 | Map, raster tiles, WMS, layer switcher | Small, raster tiles and WMS built in, simple API. |
| uPlot | 1.6.32 | Time-series charts | Fast with 20k+ points, cursor sync and drag-to-zoom built in. |

Both load from jsDelivr with Subresource Integrity (`sha384`) hashes, which work on a `file://` page because jsDelivr sends `Access-Control-Allow-Origin: *`. To upgrade, download the new files, recompute the hashes with `openssl dgst -sha384 -binary FILE | openssl base64 -A`, and update the `integrity` attributes.

Alternatives considered: **OpenLayers** has a built-in GPX parser and good WMS support, but a bigger API. **MapLibre GL** gives smooth vector maps but needs a style file and usually a keyed tile provider.

### 3.3 Background maps

Most of a passage race is far offshore, where a street map is plain blue. What adds information there is depth shading. Near harbours, buoys and lights (seamarks) matter. These findings were checked in October 2026:

| Source | Used? | Finding |
|---|---|---|
| Esri World Ocean Base + Reference | **Default** | Depth shading and labels, no key. Around Cape Town the tiles stop at **zoom 10**. From z11 up the service returns a "Map data not yet available" image, so the page sets `maxNativeZoom: 10, maxZoom: 12`. |
| Esri World Topo | **Above z12** in the Ocean layer | Good harbour detail. Offshore it is plain light blue. |
| GEBCO WMS `GEBCO_LATEST` | Layer | Global shaded-relief bathymetry, about 450 m resolution. `GEBCO_LATEST` was chosen over `GEBCO_LATEST_2` (flat colours) because the relief shows the shelf edge. |
| Esri World Light Gray (+ Reference) | Layer | Plain background that makes the track stand out. Replaces CARTO. |
| Esri World Imagery | Layer | Satellite. Little use offshore. |
| OpenSeaMap seamarks | **Overlay, on by default** | See-through layer of buoys and lights, good detail in Table Bay. Nothing offshore. |
| CARTO basemaps | No | Now return an "API KEY REQUIRED" tile. |
| OpenStreetMap standard tiles | No | The tile policy requires a `Referer` header, which `file://` pages don't send. |
| Navionics (Garmin) web API | No | The free tier forbids drawing your own data on top. Overlays need the paid tier. |
| South African Navy Hydrographic Office charts | No | Paid, in an encrypted chart format browsers can't show. |
| NOAA chart tiles | No | US waters only. |
| Google Maps, MapTiler, Mapbox | No | Need API keys, and Google also a billing account. On `file://` keys can't be restricted to a domain. |
| Offline (Natural Earth coastline, Protomaps PMTiles extract) | No | Possible if offline use is ever needed. |

**Zoom hand-over gotcha:** the map uses whole-number zoom levels only (no `zoomSnap: 0.5`). Leaflet picks a layer's tiles by the *rounded* zoom but hides the layer by the *unrounded* zoom. At z12.5 both the Ocean layer (`maxZoom: 12`) and the Topo layer (`minZoom: 13`) were hidden, which was verified in testing.

### 3.4 OpenSeaMap and JOSM

The user asked whether OpenSeaMap's JOSM link could import a track. It can't:

- JOSM is the desktop OpenStreetMap editor. Its "Remote Control" feature listens on `127.0.0.1:8111`.
- OpenSeaMap's "Map with JOSM Remote" button (`josm_call()` in its `nominatim.js`) sends `load_and_zoom?left=…&right=…&top=…&bottom=…`. That makes JOSM download OpenStreetMap data for the current view so you can edit seamarks.
- Data flows from the OpenStreetMap database into OpenSeaMap's tile renderer, never from JOSM to OpenSeaMap.
- OpenSeaMap's Trip Planner only *exports* routes you draw (GPX, KML, GML, CSV). depth.openseamap.org accepts depth soundings, which the watch doesn't record.
- **OpenCPN** can show a GPX track on OpenSeaMap's downloadable charts, but does no analysis.

### 3.5 Speed and course

- **SOG** at each fix is the straight-line distance between the first and last fixes within a time window centred on it, divided by the time between them. The window is set by **Smoothing** (6/10/20/30/60 s, default 20 s).
- **COG** uses the same window, or 20 s if the window is shorter, because course is noisier than speed at low speed.
- If a window holds only one fix, the neighbouring fixes are used.
- **Distance sailed** is the sum of the raw fix-to-fix distances. On the 2024 track the median raw and smoothed speeds differ by about 0.5% (6.30 vs 6.27 kn), so the noise adds little.

### 3.6 Turns

A turn is detected and measured like this (constants are at the top of the script):

- **Detection:** at each fix, compare the circular-mean COG 20–60 s before with 20–60 s after (`TURN_WIN`). It's a turn if the change is ≥ 50° (`TURN_MIN_DEG`) and the mean SOG before is ≥ 2 kn (`TURN_MIN_KN`). Running sums make each of these means constant-time.
- **One turn, many fixes:** fixes that qualify within 90 s of each other are treated as one turn. The fix with the largest course change marks it.
- **Entry speed:** mean SOG 20–60 s before. **Minimum:** lowest SOG from 20 s before to 40 s after.
- **Recover:** time from the slowest point until SOG is back to 90% of entry speed (`RECOVER_FRAC`), capped at 5 min (`RECOVER_CAP_S`, shown as ">5m").
- **Loss:** the integral of (entry speed − SOG) from 20 s before until recovery or the cap, in metres, floored at 0.
- **What it can't tell:** without wind it cannot tell a tack from a gybe or a mark rounding. Direction is reported as P (to port, course decreasing) or S (to starboard).

### 3.7 From out-and-back to general courses

The first version was built around the user's out-and-back distance race (sail out, turn, come back by a deadline). It had a draggable **mark** (default: first fix), **range from the mark**, a **turn-around** (furthest point from the mark, counted if the track then came back at least 25% closer), **VMC** (speed away from the mark, then toward it after the turn-around) and fixed **Whole / Out / Back** columns.

The user pointed out that most courses have more legs and turns. A general course model was discussed (section 8.2). The user then asked: *"As a reviewer of the track, do I need a leg split defined in the software?"* The answer was no. The reviewer needs to look at any stretch and compare stretches, and dragging on a chart already selects a stretch. So the out-and-back parts were removed and replaced with **pinned selections**:

- Drag across a chart to select a period, then **Pin selection** to keep it as a numbered column. Columns are numbered in time order. Click a pinned column's heading to select it again, or × to unpin.
- **Made good** is the straight line from the start to the end of a period, and **efficiency** is made good ÷ sailed.
- **"One way" rule:** made good, efficiency and mean COG are shown only if the boat mostly sailed one way. That means the speed-weighted resultant of COG unit vectors is at least 0.5 of the total. A beat with tacking angles up to about 120° passes (cos 60° = 0.5). A whole out-and-back race, or a windward/leeward lap, doesn't, so it shows "–".
- Pins are not saved and are cleared when a new file loads. That was a deliberate simplification.
- The old out-and-back numbers can be reproduced by pinning the outbound and return legs (see section 5.3).

### 3.8 Speed colours

- **First version:** a continuous matplotlib "plasma" gradient (purple → orange → yellow), linear in knots from the 2nd to the 98th percentile of moving speeds.
- **Why it changed:** the user said: *"I'm finding it difficult to visually see the slow and fast parts."* Neighbouring speeds got near-identical colours. On the 2 Sep 2026 track the scale ran 1.5–10 kn, so all the racing speeds (5–8 kn) were the same orange.
- **Now:** five discrete classes, each holding about a fifth of the fixes above 1 kn (quintiles), coloured with ColorBrewer RdYlGn: red `#d7191c`, orange `#fdae61`, pale yellow `#ffffbf`, light green `#a6d96a`, green `#1a9641`. Red-is-slow, green-is-fast reads without a legend. The pale middle class marks typical speed. A dark casing keeps the pale colours visible on light maps. The line is 5 px wide.
- **Selection highlight:** now a white glow (was yellow, which would clash with the yellow class).
- **Colour blindness:** with red-green colour blindness the two ends look alike. ColorBrewer RdYlBu is the drop-in alternative, but its blue end is harder to see on water.
- **Classes are relative to the whole track,** so on a course with beats and runs the slower point of sail shows as red even when sailed well (see backlog).

## 4. How the code fits together

Everything is in `index.html`: HTML, CSS, then one script divided into sections by `// ---------- name ----------` comments.

### 4.1 Sections

| Section | Contents |
|---|---|
| constants and helpers | Turn and recovery constants, `distM` (haversine), `bearingDeg`, `angDiff`, `lowerBound`/`upperBound` |
| formatting | Time-zone-aware `Intl.DateTimeFormat` cache (`dtf`), `fmtTime`, `fmtHM`, `fmtDate`, `fmtDur`, `fmtDDM` (degrees and decimal minutes, e.g. `33 51.907'S  018 25.463'E`) |
| GPX parsing and analysis | `parseGpx` (namespace-agnostic, sorts by time, drops repeated timestamps), `buildTrack` (typed arrays and cumulative distance), `analyse` (SOG, COG, turns, colour scale), `legStats` (one period's numbers) |
| state | `settings` (smoothing, time zone), `track`, `an`, `sel`, `pins`, `cur`, `charts`, flags |
| map | Base layers and overlay, panes, renderers, boat marker, info and legend controls, `SPEED_COLORS`/`speedClass`, `drawTrack`, `drawPoints`, `drawSelection`, `updateLegend`, `updateInfo`, `fitMapTo`, map hover |
| charts | `marksPlugin` (dashed lines at turns), `buildCharts`, `setRange`, `onRange`, `syncChartCursors`, resize handling |
| side panel | `renderStats` (periods table), `renderTurns`, `zoomToTurn` |
| cursor and replay | `setCurrent`, `startPlay`/`stopPlay`/`stepPlay`, `recompute`, `loadGpxText` (exposed as `window.loadGpxText` for the console and tests), `openFile` |
| controls | Button, select and slider handlers, time-zone list, drag and drop, global error reporting |

### 4.2 Data flow

1. A file arrives through `openFile` → `loadGpxText` → `parseGpx` → `buildTrack`, which resets `sel`, `pins` and `cur`. Then `recompute()` runs, and finally `fitMapTo` fits the whole track.
2. `recompute()` (also run when smoothing or time zone change) calls `analyse`, then `drawTrack`, `drawPoints`, `updateLegend`, `renderTurns` and `buildCharts`, then `setCurrent`.
3. `buildCharts()` destroys and recreates the two uPlot charts (SOG, COG). It keeps the current selection by time, so a selection survives a change of smoothing or time zone.
4. A zoom on any chart fires the first chart's `setScale` hook, which calls `onRange`. That converts the time range to indices, sets `sel` (`null` means the whole track), updates the slider range and buttons, and calls `drawSelection` and `renderStats`.
5. `setCurrent(i, source)` is the single place that moves the "current fix": boat marker and rotation, info box, chart cursors, slider, and follow-pan during replay. `source` is one of `map`, `chart`, `scrub`, `play`, `turn` or `recompute`, and it decides which of those to skip so updates don't loop.

### 4.3 Map details

- **Panes:** `selection` (z 390, white glow under the track), `track` (z 420, canvas), `points` (z 450, start and end dots, plus turn dots that zoom to the turn when clicked).
- **Track drawing:** a dark casing polyline, then one polyline per run of fixes in the same speed class. That makes 4–6k polylines on the long races and 250–320 on the evening races.
- **Colours:** see 3.8. Class limits are rounded to 0.1 kn so the legend matches the drawing exactly.
- **Hover:** each animation frame searches all fixes in flat-earth coordinates for the nearest one, and uses it if it is within 14 px on screen.

### 4.4 uPlot details (verified against uPlot 1.6.32 source)

- **Cursor sync:** both charts use `cursor.sync = { key: 'track', scales: ['x', null] }`. uPlot relays mousemove, mousedown, mouseup and dblclick to the other chart, so drag-to-zoom and double-click-reset apply to both.
- **Zooms apply later:** `setScale` takes effect on a microtask, so `onRange` runs from the hook, and `onRange` re-places the cursors on the next animation frame.
- **Cursor hook fires on redraws too:** the `setCursor` hook fires after zoom redraws as well as on mouse moves. The app only follows it while the mouse is over the charts (`overChart`). Without that guard, zooming to a turn moved the boat to the wrong fix.
- **Moving the cursor from code:** `u.setCursor({left, top}, false, false)` fires no hook and doesn't relay to the other chart.
- **COG wrap-around:** COG data has `null` where consecutive values differ by more than 180°, so the line breaks at 359°→0°.
- **Chart width:** `#charts` is hidden while empty (`:empty`), so charts are sized from `#left`.

## 5. Testing

### 5.1 Headless check: `test/check.py`

```
test/check.py [--screenshot DIR] [--tz Africa/Johannesburg] [--smooth 20] FILE.gpx...
```

For each file it writes a temporary copy of `index.html`, loads the GPX through a `<script>` tag, and calls `loadGpxText` (a `file://` page can't fetch the GPX itself). It runs headless Chrome and prints the load time, the speed class limits, the Periods table and the Turns table, optionally with a 1600×1000 screenshot. It exits non-zero on JS errors, a status message or a missing screenshot. Each Chrome launch gets its own profile directory: a second Chrome started on a profile that is still in use exits without output.

- **Needs:** Python 3 (standard library only), Chrome or Chromium (or set `CHROME`), and internet access.
- **Checks:** that the page loads and computes, plus the numbers. It doesn't check them against expected values; compare them with section 5.3 by eye.

Interactions were checked with one-off scripts in the same style (calling `setRange`, clicking `#pin`, firing `mousemove` on the map):

- selection and pinning
- duplicate-pin rejection
- re-selecting a pin from its heading, and unpinning
- zoom to a turn
- map hover moving both chart cursors
- replay staying inside the selection
- the zoom hand-over at z12 and z13

### 5.2 Not yet tested

- Real mouse dragging on charts, the file picker, drag and drop, and touch.
- Firefox and Safari.
- Pan and zoom smoothness in a real browser with 5–7k polylines.

### 5.3 Test tracks

The GPX files are personal location history and stay out of git (`.gitignore` has `*.gpx`). The user keeps them in `~/Downloads/`; the last three are in `~/Downloads/GPX-files-for-analysis-frontend/`. Times are SAST (UTC+2) at 20 s smoothing.

| File | When | What | Fixes | Elapsed | Sailed | Avg SOG | Max SOG | Turns |
|---|---|---|---|---|---|---|---|---|
| `activity_17328860833.gpx` | Sat 19 Oct 2024, 08:23–00:04 | Out-and-back distance race west of Table Bay. Turn-around 16:41, 46.75 nm from the first fix. | 17,434 | 15h 41m | 97.77 nm | 6.23 kn | 8.69 kn | 5 |
| `activity_24242231850.gpx` | Wed 2 Sep 2026, 16:53–19:10 | Evening race in Table Bay, several legs. 380 s GPS gap. | 2,705 | 2h 16m | 13.03 nm | 5.73 kn | 12.63 kn | 13 |
| `activity_24660672774.gpx` | Wed 7 Oct 2026, 17:23–19:40 | Evening race in Table Bay, several legs and pre-start circling. 1,810 s GPS gap. | 2,466 | 2h 17m | 11.39 nm | 4.99 kn | 7.89 kn | 11 |
| `activity_24771299457.gpx` | Sat 17 Oct 2026, 09:07–23:48 | Coastal race from Table Bay round Cape Point into False Bay. Ends 22 nm from the start. | 23,616 | 14h 40m | 71.12 nm | 4.84 kn | 7.23 kn | 12 |

- **Reference numbers for the 2024 track:** pinning the outbound leg (08:23–16:41) gives 50.87 nm sailed, 6.13 kn, 46.75 nm made good, 92%, COG 250°. Pinning the return leg (16:41–00:04) gives 46.89 nm, 6.35 kn, 45.97 nm, 98%, 064°.
- **The 12.63 kn peak on 2 Sep 2026 looks real:** the straight-line speed stays at 10.4 kn over 2 minutes (18:29–18:31), so it isn't a single GPS jump.
- **Speed class limits at 20 s smoothing:** 19 Oct 2024: 5.8 / 6.1 / 6.4 / 6.7 kn. 2 Sep 2026: 4.9 / 6.4 / 7.3 / 8.3. 7 Oct 2026: 4.1 / 5.3 / 6.1 / 6.7. 17 Oct 2026: 4.3 / 4.7 / 5.1 / 5.5.
- **Load times:** 0.25 s for 2.5k fixes, 0.9–1.2 s for 17–24k fixes (headless).

## 6. Known issues

Found by running the four tracks above.

1. **GPS gaps are drawn as if sailed.** The page draws a straight line across a gap on the map and chart, and counts the straight line as distance sailed. On 7 Oct 2026 the watch logged nothing from 18:36:08 to 19:06:18 (30 min) and the next fix is 3.3 km away. That makes "sailed" too low and the SOG line flat across the gap. 2 Sep 2026 has a 380 s gap at 17:10:52–17:17:12. *Fix idea:* treat a gap of more than about 60 s as a break. Use `null` in the chart data, split the map polylines, leave it out of sailed distance (or show it separately), and mark gaps on the chart.
2. **Loss and Recover are overstated at mark roundings.** They compare with the entry speed, but after a rounding the boat is on a different point of sail. On 2 Sep 2026 at 17:57:47 (a 180° turn) the entry speed was 8.5 kn and the speed settled at 6.4–6.5 kn, so the table shows ">5m" and 347 m lost. On 17 Oct 2026, 18:03:24 (6.0 → 4.4 kn) and 20:52:46 (6.3 → 3.9 kn) show the same thing. *Fix idea:* recover to 90% of the lower of the entry speed and the steady exit speed (mean SOG 60–180 s after), and measure loss against a line from entry to exit speed.
3. **Non-sailing turns are counted.** Pre-start circling (three starboard turns at 16:58–17:09 on 2 Sep 2026) and drifting at the end of a sail near 2 kn (2 Sep 18:47 and 18:56, 7 Oct 19:38) are all listed. Turns less than about 90 s apart merge into one, so a fast tacking duel would be under-counted.
4. **Mean COG and made good are blank for the whole of a point-to-point race that bends round a cape.** On 17 Oct 2026 the course changes direction too much. This is the "one way" rule working as designed, but it may surprise.
5. **Max SOG depends on smoothing.** Shorter windows let more GPS noise through. On the 2024 track the max is 8.69 kn at 20 s and 10.37 kn at 10 s, while the raw fix-to-fix maximum is 15 kn. Use 20 s or more for honest maxima.
6. **Speed colours look speckled on steady long races at the default 20 s smoothing.** On the 2024 track the class limits are only 0.3 kn apart (5.8 / 6.1 / 6.4 / 6.7 kn), so GPS noise moves fixes between classes every few seconds. At 60 s smoothing the slow and fast stretches stand out as solid runs, and the map needs 2,216 polylines instead of 5,757. The evening races, with a wider spread of speeds, read well at 20 s.

## 7. Backlog

These are in the order that best serves "see what it did". The first two are fixes for section 6.

1. GPS gap handling (issue 1).
2. Turn loss measured against exit speed (issue 2).
3. Speed colours: smooth the colouring separately from the charts (e.g. 60 s for colours, issue 6), and offer colour classes relative to the current selection, so slow and fast stretches within one leg show even when beats are always slower than runs.
4. Tack and gybe angles, made visible (README, "Ideas for later"): a course rose per selection, before/after arrows at each turn, and the tacking angle per period. The user said they *do* care about tack and gybe angles, but parked them for later: *"propose that as future idea; let's keep it simple to start with."*
5. Save pins per track in `localStorage`, keyed by the first fix time and fix count.
6. Click between two turns on a chart to select exactly that stretch, which makes pinning legs quicker.
7. Option to set a minimum speed for turns, or to hide turns before the first long straight leg (issue 3).
8. Larger features, each needing a design discussion first: wind and polars (README, "Ideas for later"), course marks and start-line analysis (8.2), comparing several tracks, and offline use (copy the libraries into the repo, plus an offline tile source).

## 8. Discussions to pick up from

### 8.1 Key user decisions so far

- Heart rate: ignore it (*"it's from a smart watch"*).
- Internet access is fine. Use is personal and non-commercial.
- Colour the line by speed, and design from the point of view of a racing sailor reviewing their own race.
- Wind and polars: not yet (*"I know what my boat should be doing and I want to see what it did"*). They are written up in the README for later.
- Leg splits are not needed. Pinned selections were agreed instead.
- Tack and gybe angles: wanted, but later.
- Speed colours: the first gradient made slow and fast parts hard to see. Replaced with five red-to-green classes (3.8).

### 8.2 General course model (deferred)

If more structure is needed later, this was the proposed shape: a race is a track, plus an optional course (start line, marks in order, finish line), plus optional wind.

- **Splitting into legs:** manually (always works), from marks (closest approach to each mark in order; automatic but needs positions), or from big course changes (only suggestions, because tacks and roundings look alike without wind).
- **Where marks come from:** typed from sailing instructions in degrees and decimal minutes, clicked on the map, imported from a GPX route or waypoint file (OpenSeaMap's Trip Planner, OpenCPN and chart plotters export these), or a saved list of club marks.
- **What "made good" means per leg:** VMC to the next mark on reaches and passage legs, VMG to the wind on beats and runs, or progress along the rhumb line as a stand-in without wind.
- **Start analysis:** from the line ends and gun time, show distance and time behind the line at the gun, and speed at the gun.
- **Wind sources:** typed by the user, estimated from tack headings (the line halfway between port and starboard courses points into the wind), Open-Meteo modelled wind, or instrument logs (usually NMEA).

### 8.3 Open questions

- Which races matter most: evening races in Table Bay (two of the test tracks), coastal races, or offshore distance races?
- Should pins be saved per track?
- Does the boat ever log instrument data (heading, boat speed, wind)? That would change what is possible more than anything else.
