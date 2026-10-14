# 05 — Phone test bench and the how-it-works page

## Asked for
A "how it works" page kept up to date in the repo, and a version of the app usable from a phone to test
and keep developing.

## Decision (a deliberate change of order)
Entry 02 said: in-app recording only at first, upload later. A native Android recorder needs a build
environment that was not available where this was written, so it would have been delivered untested.
Instead, an **interim phone test bench** was built first: the phone records with its own camera app
(240 fps), and its browser talks to a small server on the PC that runs the same engine. This gets real
clips and real accuracy numbers sooner. The native recorder (Camera2 high-speed capture, exact sensor
timestamps) is still the plan and comes next.

## Built
- `testbench/server.py` (Flask): upload, frame extraction, analysis job, overlay image, history, CSV.
- `testbench/static/index.html`: 4-step mobile UI (upload, tap 4 stump points with a zoom square,
  mark release frame, enter reference/distance/offset and run), result card with confidence and overlay.
- `docs/how-it-works.md` (plain English, with a diagram), `docs/git-in-plain-words.md`.

## Checked
Server API end to end on the synthetic clip (upload, frames, analysis, overlay, CSV; result 139.4 vs 140
with the expected "timing assumed" warning), server start-up, client JavaScript syntax.
**Not checked:** the page on a real phone (touch behaviour, file picker, layout), real codecs (HEVC .mov),
Windows firewall behaviour.

## Trade-off to remember
The test bench cannot get sensor timestamps, so timing is assumed and uncertainty is wider. That is
exactly what the native recorder fixes.

## Next
1. Record real clips and run them through the test bench; collect results.csv.
2. Native Android recorder with sidecar timestamps.
3. Marker calibration; parallax term in the uncertainty.
