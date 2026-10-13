# cricpro

An app that measures the speed of a cricket ball from video and, later, does
biomechanical analysis of fast bowlers.

- **v0.x** — ball speed, in-app recording, side-on fixed camera, target ±1 km/h
- **v1.x** — biomechanics (pose, release/foot-strike events, action classification)

The `docs/journey/` folder is the running log of how and why decisions were made.
See [JOURNEY.md](JOURNEY.md) for the index and the logging convention.

## Layout
    docs/journey/     decision log, one numbered entry per working session
    speed-core/       Python reference implementation of the speed pipeline (v0.1)
    android/          (planned) in-app recorder + UI

## Quick start
    cd speed-core && pip install -r requirements.txt
    python tests/validate_synthetic.py
