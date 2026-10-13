# 02 — v0 scope and decisions

## Decisions
- **Two stages:** v0 = speed that works accurately; v1 = adds biometrics.
- **Recording:** in-app recording only at first; video upload later. The app should detect the
  device's real fps rather than trusting a label.
- **Camera position:** start with one fixed position (side-on, perpendicular to the pitch) and
  make it perfect; generalise to other positions afterwards.
- **Calibration:** taps with a zoomed magnifier and reprojection check; printed marker / ruler;
  gravity cross-check (ball's vertical motion follows 9.8 m/s²); automatic stump detection later.
- **Confidence indicator:** built from frames tracked, trajectory-fit residual, calibration
  error, timing reliability, motion blur; shown as e.g. "142.6 ± 0.8 km/h".
- **Accuracy target:** ±1 km/h.
- **Frame-by-frame viewer** to correct release frame / ball position; to be improved later.
- **Validation:** test footage and a speed reference are available.

## Advice taken on board
- Use per-frame timestamps, not "240 fps": slow-motion clips are often re-timed to a 30 fps
  playback rate.
- ±1 km/h needs sub-frame precision from trajectory fitting plus good calibration; a radar gun
  itself is ~±1–2 km/h, so a bowling machine or timing gates are a better reference.
- Define "perfect" with a number and measure how often we meet it.
