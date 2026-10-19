# Track viewer

A single HTML page for reviewing a sailing GPX track after a race.

Open `index.html` in a browser straight from disk (`file://` works), then click **Open GPX…** or drop a GPX file on the page.
The page needs internet access for map tiles and for its two libraries, Leaflet 1.9.4 and uPlot 1.6.32. Both load from jsDelivr, pinned with integrity hashes.

## What it shows

- **Map:** the track coloured by speed over ground (SOG) in five classes: red for the slowest fifth of the time moving, through orange, pale yellow and light green, to green for the fastest fifth. Start, end and turns are marked. Base maps: Esri Ocean (default), GEBCO bathymetry, Esri light grey and Esri satellite. The OpenSeaMap seamark layer (buoys, lights) is on by default.
- **Charts:** SOG and course over ground (COG) against time. Hovering the map or a chart moves a boat marker and a readout. Dragging across a chart selects a period. Double-clicking resets it.
- **Periods:** distance sailed, average and max SOG, distance made good, efficiency, mean course and number of turns, for the whole track and the selected period. **Pin selection** keeps a period as an extra column, so you can compare, for example, the outbound and return legs.
- **Turns:** every course change of 50° or more, with entry speed, minimum speed, time to recover and metres lost.
- **Replay:** plays the selected period at 60–3600× real time, with an option to keep the boat in view.

## How the numbers are worked out

- GPS fixes are 1–9 s apart and jitter by a few metres. SOG therefore comes from the straight-line distance across a time window centred on each fix (6–60 s, set by **Smoothing**). COG uses the same window, or 20 s if the window is shorter.
- **Made good** is the straight-line distance from the start to the end of a period. **Efficiency** is made good divided by distance sailed. Made good, efficiency and **mean course** are left blank when the boat sailed in very different directions during the period, such as over a whole out-and-back race. A beat with tacks still counts as one direction.
- A **turn** is a change of at least 50° between the mean course 20–60 s before a fix and 20–60 s after it, entered at 2 kn or more. **Recover** is the time from the slowest point until SOG is back to 90% of entry speed. **Loss** is the distance given up compared with holding entry speed until then.

## Map sources

The tile services are free for personal, non-commercial use with attribution:

- Esri World Ocean Base and Reference. In some regions, Cape Town included, these stop at zoom 10, so above zoom 12 the Ocean base map switches to Esri World Topo.
- GEBCO WMS (`GEBCO_LATEST`, shaded relief).
- Esri World Light Gray Canvas and World Imagery.
- OpenSeaMap seamarks.

## Ideas for later

### Tack and gybe angles

How far the boat turns through each tack or gybe, and how consistent that is, says a lot about how well it is being sailed. Much of this can be shown without wind data:

- **Angle per turn:** the Turns table already shows the course before and after each turn. That is the tacking or gybing angle measured over the ground.
- **Course rose:** a circular histogram of time spent on each course during a selected period. On a beat it shows two lobes, one per tack. The angle between them is the typical tacking angle, and the width of each lobe shows how steadily the boat was steered.
- **Turn arrows on the map:** short arrows at each turn showing the course before and after.
- **Limits:** COG is not heading, because leeway and current move the boat sideways, so angles over the ground differ from angles on the compass. Telling a tack from a gybe needs the wind direction, or a label from the user.

### Wind and polars

The GPX from a watch has no wind, so the page shows what the boat did but not how well it did for the conditions. Adding wind and the boat's polars would change that:

- **Wind without instruments:** Open-Meteo's historical API returns hourly modelled wind for any time and place. It is free for non-commercial use, needs no key, and allows requests from a page opened from disk.
- **Percentage of polar:** combining that wind with the boat's ORC polar (the table in `apparent-wind/optimise_route.py`) gives % of polar along the track. For the 19 Oct 2024 race it gave 91–101% for most of the outbound leg and dips to 82–86% at 09:00–10:00 and 19:00–20:00.
- **Limits:** hours above 100% (101–105% from 22:00) show that model wind is approximate and that GPS speed includes current. The numbers are useful for comparing parts of a race with each other, not as absolute values.
- **Also possible with wind:** labelling turns as tacks or gybes, true wind angle and VMG, splitting legs automatically by point of sail, and comparing the actual race with the `apparent-wind` plan (turn time, distance).
- **Buoy racing:** beats and runs would also need the ORC beat and run targets, because the current polar table only covers 52–150° true wind angle.
