# Testing v0.1

There is no phone app yet. v0.1 is the analysis engine plus two helper tools, run on your PC
(Windows PowerShell commands below). Test in three levels.

## Level 1 — smoke test (no footage, ~2 minutes)
    cd speed-core
    py -m pip install -r requirements.txt
    py tests\validate_synthetic.py
Expect a table of synthetic deliveries with small errors (see `speed-core/README.md`).
If this runs, the engine works on your machine.

## Level 2 — real clips with a reference speed
### Recording protocol (matters more than any code)
- Phone on a **tripod**, main (1x) lens, **no zoom, video stabilisation OFF**, 240 fps slow-motion
  (1080p). Lock exposure/focus if the app allows. Bright daylight; ball must contrast with background.
- Camera **square-on to the pitch**, level, roughly at stump height, far enough back to see both sets
  of stumps with some margin. Pause a frame and check: the stumps at both ends should be the **same
  height in pixels** (within ~2%), and the pitch should look horizontal. If one end is bigger, the
  camera is yawed.
- Whole flight visible: release to past the bounce.
- Bowl along the line of the stumps (a bowling machine on the centre line is ideal for the first tests).
- For every delivery write down: file name, **reference speed** (radar / machine), camera distance
  from the pitch centre line (metres, approximate), and how far the ball was from the centre line.
- 10–20 deliveries across a few speeds is plenty for a first look.

### Per clip
1. Make the calibration file (click 4 stump points, mark the release frame):
       py tools\pick_taps.py clip.mp4 --capture-fps 240
   Keys are printed at the top of `tools/pick_taps.py`. This writes `clip.cal.json`.
   (GUI written without a display, so it may have rough edges. Tell me what breaks.)
2. Run one clip:
       py -m cricketspeed clip.mp4 --cal clip.cal.json --overlay clip_overlay.jpg
3. Many clips against the reference: make `clips.csv` with columns `clip,radar_kmh`, then
       py tools\batch_eval.py clips.csv
   This writes `results.csv` and prints mean error, RMS error and how many are within ±1 km/h.

### What the output means
`142.6 ± 1.7 km/h [MEDIUM]` = release speed, 95% half-width, confidence label. The reasons for a
lower label are printed (few frames, gravity check off, fps low, timing not from sensor timestamps...).
Without the in-app recorder there are no sensor timestamps, so every real clip will be flagged
"timing assumed" and carry an extra 1% uncertainty. A file that reports 30 fps is refused unless you
give the real capture fps, to stop a slow-motion clip silently reading many times too slow.

## Level 3 — what to send back
`results.csv`, the camera distances and any notes, and one or two overlay images, especially of the
worst clips. That is the first real accuracy number.

## Expect errors, and know the likely causes
- **Camera not square-on (yaw):** bias roughly equal to the end-to-end scale change.
- **Ball off the calibration plane (parallax):** the calibration plane is the vertical plane through the
  pitch centre line. A ball nearer to the camera than that plane looks larger and reads fast. Rough
  size (analytical estimate, not measured): relative error ~ offset / camera distance, so 0.5 m offset
  at 20 m distance is about 2.5%, i.e. ~3 km/h at 140. Recording the distances lets us check this.
- Radar guns are themselves ~±1–2 km/h.
