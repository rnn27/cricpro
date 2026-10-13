"""Accuracy check on synthetic deliveries with known speed. Run: python tests/validate_synthetic.py"""
import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent)); sys.path.insert(0, str(_here))
import numpy as np
import synth
from cricketspeed.pipeline import analyze
from cricketspeed.sources import CallableSource
from cricketspeed.timebase import Timebase


def run(v, h31, seed, fps=240.0, assumed_fps=None, label=""):
    synth.set_camera_yaw(h31)
    render, n, ts, v_true, rel = synth.make_clip(v, fps=fps, seed=seed)
    taps = synth.true_taps(np.random.default_rng(100 + seed), 1.0)       # 1 px tap noise
    src = CallableSource(n, render, (720, 1280))
    if assumed_fps:
        t = np.arange(n) / assumed_fps; rel_ok = True; src_tb = Timebase(t, "assumed", assumed_fps, 0.0, False, [])
    else:
        dt = np.diff(ts)
        src_tb = Timebase(ts - ts[0], "sidecar", 1 / np.median(dt), float(np.std(dt) / np.median(dt)), True, [])
    r = analyze(src, taps, src_tb, release_frame=rel)
    return v_true, r


cases = []
for h31, name in [(0.0, "square-on"), (0.0005, "yaw ~1% end-to-end"), (0.002, "yaw ~4% end-to-end")]:
    for v in (100, 130, 150):
        for seed in (1, 2):
            cases.append((name, v, h31, seed, 240.0, None))
cases += [("square-on, 120 fps", 140, 0.0, 1, 120.0, None), ("square-on, 120 fps", 140, 0.0, 2, 120.0, None),
          ("square-on, fps label 0.4% wrong", 140, 0.0, 1, 240.0 * 0.996, 240.0), ("square-on, fps label 0.4% wrong", 140, 0.0, 2, 240.0 * 0.996, 240.0)]

rows = {}
for name, v, h31, seed, fps, assumed in cases:
    v_true, r = run(v, h31, seed, fps=fps, assumed_fps=assumed)
    if not r.ok:
        print(f"{name:34s} {v:4d} km/h  FAILED: {r.message}"); continue
    err = r.release_kmh - v_true
    rows.setdefault(name, []).append((err, r.ci95_kmh, abs(err) <= r.ci95_kmh, r.confidence))
    print(f"{name:34s} {v:4d} km/h  est {r.release_kmh:6.1f} ± {r.ci95_kmh:4.1f}  true {v_true:6.1f}  err {err:+5.2f}  "
          f"in-CI {abs(err) <= r.ci95_kmh!s:5s} {r.confidence}")
print("\nsummary (mean |err|, mean reported 95% half-width, share of runs whose true value was inside it)")
for name, lst in rows.items():
    e = np.array([x[0] for x in lst]); c = np.array([x[1] for x in lst]); k = np.mean([x[2] for x in lst])
    print(f"  {name:34s} |err| {np.mean(np.abs(e)):4.2f}   ±{np.mean(c):4.2f}   covered {k:.0%}   n={len(lst)}")
