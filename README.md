# Track viewer

A single HTML page for reviewing a sailing GPX track after a race.

Open `index.html` in a browser straight from disk (`file://` works), then click **Open GPX…** or drop a GPX file on the page.
The page needs internet access for map tiles and for its two libraries, Leaflet 1.9.4 and uPlot 1.6.32. Both load from jsDelivr, pinned with integrity hashes.

## What it shows

- **Map:** the track coloured by speed over ground (SOG), with the start, end, turn-around and turns marked. Base maps: Esri Ocean (default), GEBCO bathymetry, Esri light grey and Esri satellite. The OpenSeaMap seamark layer (buoys, lights) is on by default.
- **Charts:** SOG and VMC, course over ground (COG), and range from the mark, all against time. Hovering the map or a chart moves a boat marker and a readout. Dragging across a chart selects a period. Double-clicking resets it.
- **Legs:** distance sailed, average and max SOG, distance made good, average VMC and efficiency for the whole track, the outbound and return legs, and the selected period.
- **Turns:** every course change of 50° or more, with entry speed, minimum speed, time to recover and metres lost.
- **Replay:** plays the selected period at 60–3600× real time, with an option to keep the boat in view.

## How the numbers are worked out

- GPS fixes are 1–9 s apart and jitter by a few metres. SOG and VMC therefore come from the straight-line distance across a time window centred on each fix (6–60 s, set by **Smoothing**). COG uses the same window, or 20 s if the window is shorter.
- The **mark** defaults to the first track point. You can drag it, pick it on the map, or type it (`33 51.907'S 018 25.463'E` or `-33.865, 18.424`).
- The **turn-around** is the furthest point from the mark, counted only if the track then comes back at least 25% closer. **VMC** is the speed away from the mark until the turn-around and toward it afterwards. **Made good** is the same measure as a distance. **Efficiency** is made good divided by distance sailed.
- A **turn** is a change of at least 50° between the mean course 20–60 s before a fix and 20–60 s after it, entered at 2 kn or more. **Recover** is the time from the slowest point until SOG is back to 90% of entry speed. **Loss** is the distance given up compared with holding entry speed until then.

## Map sources

The tile services are free for personal, non-commercial use with attribution:

- Esri World Ocean Base and Reference. In some regions, Cape Town included, these stop at zoom 10, so above zoom 12 the Ocean base map switches to Esri World Topo.
- GEBCO WMS (`GEBCO_LATEST`, shaded relief).
- Esri World Light Gray Canvas and World Imagery.
- OpenSeaMap seamarks.
