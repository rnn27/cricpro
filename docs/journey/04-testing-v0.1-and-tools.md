# 04 — Testing v0.1, tools added

## Context
Push to GitHub done (`rnn27/cricpro`, tag `v0.1.0`). Question: how to test v0.1. There is no app
yet, so testing means running the Python engine on recorded clips.

## Added
- `tools/pick_taps.py`: click the 4 stump taps (with a magnifier), step frames, mark the release
  frame, writes `<clip>.cal.json`. GUI not run in the authoring environment (no display).
- `tools/batch_eval.py`: runs many clips against a reference speed, writes `results.csv`, prints
  mean/RMS error and the share within ±1 km/h.
- CLI now takes the `.cal.json` (taps, release frame, capture fps).
- Safety guard: a file whose container says < 100 fps is refused unless the real capture fps is
  given (a re-timed slow-motion clip would otherwise read many times too slow).
- `docs/testing-v0.1.md`: recording protocol and test steps.

## Checked headlessly
CLI with a cal file, batch evaluation on the synthetic clip (-0.6 km/h vs 140), and the fps guard.

## Finding to carry forward
Parallax from the ball being off the calibrated centre-line plane is likely a larger error than we
had weighted: relative error ~ offset / camera distance (analytical estimate). Not yet in the
uncertainty model. Candidates for v0.2: record camera distance and add an offset prior to the
uncertainty; calibrate with markers in the ball's plane; or a second camera.

## Open
First real accuracy numbers; Android recorder; marker calibration.
