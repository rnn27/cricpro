# cricketspeed v0.1 — ball speed from a fixed side-on high-fps video

Speed-only core (no biomechanics yet). Python reference implementation of the
algorithm that the Android app will run; validated on synthetic deliveries.

## Run
    pip install numpy opencv-python scipy
    python -m cricketspeed clip.mp4 --taps taps.json --release-frame 72
    python tests/validate_synthetic.py        # accuracy check vs known speeds

`taps.json`: {"bowler_base":[x,y], "bowler_top":[x,y], "batter_base":[x,y], "batter_top":[x,y]}
(pixel taps on the base and top of the stumps at each end).

## Recording contract for the in-app recorder (Android)
Next to `clip.mp4` write `clip.mp4.timestamps.json`:
    {"timestamps_ns": [one SENSOR_TIMESTAMP per frame], "capture_fps": 240}
Frame timing comes from these, never from the container or the fps label.
Use Camera2 constrained high-speed capture, fixed focus/exposure/white balance,
shutter <= 1/1000 s, tripod, camera square-on to the pitch.

## Pipeline
1. timestamps (sidecar > assumed capture fps > container; non-sidecar = flagged unreliable)
2. calibration: least-squares similarity from 4 stump taps (square-on camera assumed)
3. background (median) + moving-blob candidates inside the calibrated region
4. RANSAC seed (gravity-plausible, forward speed 12-50 m/s) + cubic fit (gravity + drag)
5. release speed = fitted speed at the release frame; average speed also reported
6. uncertainty: Monte Carlo over tap noise (1 px), fit noise (bootstrap), camera-alignment
   uncertainty (default 1.5% scale difference end to end), timing (+1% if not sensor timestamps)
7. confidence label from frames tracked, residual, gravity cross-check (with drag), fps,
   timing source, and the 95% half-width

## Synthetic validation (known speeds, 1 px tap noise, 240 fps unless noted)
| camera / condition              | mean abs error | reported 95% half-width | true value inside |
|---------------------------------|---------------:|------------------------:|------------------:|
| square-on                       | 0.34 km/h      | 1.7                     | 100%              |
| yaw ~1% scale change end to end | 0.69 km/h      | 1.7                     | 100%              |
| yaw ~4% scale change end to end | 3.75 km/h      | 1.8                     | 0%  (see below)   |
| square-on, 120 fps              | 0.40 km/h      | 1.8                     | 100%              |
| square-on, fps label 0.4% off   | 0.17 km/h      | 3.3                     | 100%              |

## Known limits (what real footage must tell us)
- Calibration is the bottleneck, not tracking. With perfect calibration the tracker error was
  under 0.1 km/h. A full 4-point homography from stump taps is useless (error 11 km/h at
  1 px tap noise): all points lie in a 20 m x 0.7 m strip. Hence the similarity model.
- A camera that is not square-on (yaw) biases speed by roughly the end-to-end scale change
  (4% -> ~3.7 km/h) and CANNOT be detected from the stump taps alone at 1 px tap noise.
  Reaching +-1 km/h needs a verified alignment: printed fiducial markers at both ends
  (planned v0.2), or very precise taps plus the stump-height ratio check.
- Not simulated: lateral parallax (ball off the centre-line plane), lens distortion,
  rolling shutter, video compression artefacts beyond one mp4 test, sky/clutter backgrounds,
  the ball being hidden by the bowler's hand at release.
- Release speed assumes the release frame is marked; the speed estimate is insensitive to
  +-1 frame there, but the ball must be tracked for a few frames after release.
