import sys, time
from pathlib import Path
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent)); sys.path.insert(0, str(_here))
import numpy as np
from synth import make_clip, true_taps
from cricketspeed.pipeline import analyze
from cricketspeed.sources import CallableSource
from cricketspeed.timebase import Timebase

v = float(sys.argv[1]) if len(sys.argv) > 1 else 140
render, n, ts, v_true, rel = make_clip(v, seed=1)
rng = np.random.default_rng(5)
taps = true_taps(rng, float(sys.argv[2]) if len(sys.argv) > 2 else 1.0)
src = CallableSource(n, render, (720, 1280))
dt = np.diff(ts)
tb = Timebase(ts - ts[0], "sidecar", 1/np.median(dt), float(np.std(dt)/np.median(dt)), True, [])
t0 = time.time()
r = analyze(src, taps, tb, release_frame=rel)
print("elapsed", round(time.time()-t0, 1), "s")
print(r.headline(), "| true", round(v_true, 2), "| err", round(r.release_kmh - v_true, 2))
print(r.n_frames, r.rms_m, r.gravity_ratio, r.reasons, r.warnings, r.message)
