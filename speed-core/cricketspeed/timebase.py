"""Per-frame timestamps. Accuracy depends on real frame timing, not the fps label.

Priority:
  1. sidecar  <video>.timestamps.json  {"timestamps_ns": [...], "capture_fps": 240}
     (written by the in-app recorder from the camera sensor timestamps)
  2. --capture-fps override (assumed uniform spacing, flagged unreliable)
  3. container timestamps via ffprobe (flagged unreliable: slow-motion files are
     often re-timed to a 30 fps playback rate)
"""
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Timebase:
    t: np.ndarray                # seconds, one per frame, starting near 0
    source: str
    fps: float
    jitter_frac: float           # std(dt)/median(dt)
    reliable: bool
    warnings: list = field(default_factory=list)


def _ffprobe_times(path):
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "frame=best_effort_timestamp_time", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=120).stdout
        vals = []
        for tok in out.replace(",", " ").split():
            try:
                vals.append(float(tok))
            except ValueError:
                pass
        return np.array(vals) if vals else None
    except Exception:
        return None


def _summarise(t, source, reliable, warnings):
    dt = np.diff(t)
    med = float(np.median(dt))
    return Timebase(t - t[0], source, 1.0 / med, float(np.std(dt) / med), reliable, warnings)


def make_timebase(n_frames, video_path=None, sidecar=None, capture_fps=None):
    warnings = []
    side = sidecar or (video_path + ".timestamps.json" if video_path else None)
    if side and os.path.exists(side):
        d = json.load(open(side))
        t = np.asarray(d["timestamps_ns"], dtype=np.float64) * 1e-9
        if len(t) != n_frames:
            warnings.append(f"timestamp count {len(t)} != frame count {n_frames}; trimming")
            m = min(len(t), n_frames)
            t = t[:m]
        tb = _summarise(t, "sidecar", True, warnings)
        if tb.jitter_frac > 0.05:
            tb.warnings.append(f"frame timing jitter high ({tb.jitter_frac:.1%})")
        return tb
    if capture_fps:
        t = np.arange(n_frames) / float(capture_fps)
        warnings.append("assuming uniform frame spacing at the given capture fps")
        return _summarise(t, "assumed", False, warnings)
    t = _ffprobe_times(video_path) if video_path else None
    if t is not None and len(t) >= n_frames:
        tb = _summarise(t[:n_frames], "container", False, warnings)
        if tb.fps < 100:
            tb.warnings.append(
                f"container fps is {tb.fps:.0f}: slow-motion clips are often re-timed "
                "to playback rate. Pass the real capture fps or record in-app.")
        return tb
    raise ValueError("No usable timestamps: provide a sidecar or --capture-fps")
