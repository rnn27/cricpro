"""Writes demo.mp4 (+ sidecar timestamps + taps.json + release frame) from a synthetic delivery."""
import sys, json
from pathlib import Path
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent)); sys.path.insert(0, str(_here))
import cv2, numpy as np, synth
out = sys.argv[1] if len(sys.argv) > 1 else "demo"
synth.set_camera_yaw(0.0)
render, n, ts, v_true, rel = synth.make_clip(140, seed=3)
vw = cv2.VideoWriter(out + ".mp4", cv2.VideoWriter_fourcc(*"mp4v"), 30, (1280, 720))   # 30 fps container, like a re-timed slow-mo file
for k in range(n):
    vw.write(cv2.cvtColor(render(k), cv2.COLOR_GRAY2BGR))
vw.release()
json.dump({"timestamps_ns": [int(t * 1e9) + 10**12 for t in ts], "capture_fps": 240}, open(out + ".mp4.timestamps.json", "w"))
taps = synth.true_taps(np.random.default_rng(9), 1.0)
json.dump(dict(zip(["bowler_base", "bowler_top", "batter_base", "batter_top"], taps.round(1).tolist())), open(out + "_taps.json", "w"))
print("true speed", round(v_true, 2), "release frame", rel)
