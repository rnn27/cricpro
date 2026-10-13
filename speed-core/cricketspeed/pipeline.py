"""End-to-end analysis: frames + taps + timestamps -> speed with uncertainty."""
from dataclasses import dataclass, field

import numpy as np

from . import detect, track
from .calibration import (homography_from_taps, to_world, tap_residual_m,
                          stump_height_ratio)
from .sources import VideoSource
from .timebase import Timebase, make_timebase

UNRELIABLE_TIMING_REL = 0.01     # extra 1% (1 sigma) when frame timing is only assumed


@dataclass
class Result:
    ok: bool
    message: str = ""
    release_kmh: float = float("nan")
    sigma_kmh: float = float("nan")
    ci95_kmh: float = float("nan")
    average_kmh: float = float("nan")
    n_frames: int = 0
    rms_m: float = float("nan")
    gravity_ratio: float = float("nan")
    fps: float = float("nan")
    timing_source: str = ""
    confidence: str = "LOW"
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    debug: dict = field(default_factory=dict)

    def headline(self):
        if not self.ok:
            return f"No result: {self.message}"
        return f"{self.release_kmh:.1f} ± {self.ci95_kmh:.1f} km/h  [{self.confidence}]"


def _confidence(n, rms, gratio, tb, sigma95):
    reasons = []
    if n < 40:
        reasons.append(f"only {n} frames tracked (want >= 40)")
    if rms > 0.04:
        reasons.append(f"track residual {rms*100:.1f} cm (want <= 4 cm)")
    if not (0.9 <= gratio <= 1.1):
        reasons.append(f"gravity cross-check off by {abs(gratio-1):.0%}: calibration or tracking suspect")
    if not tb.reliable:
        reasons.append("frame timing not from sensor timestamps")
    if tb.fps < 200:
        reasons.append(f"fps {tb.fps:.0f} < 200: reduced accuracy")
    if sigma95 > 1.0:
        reasons.append(f"95% half-width {sigma95:.1f} km/h exceeds 1 km/h target")
    label = "HIGH" if not reasons else ("MEDIUM" if len(reasons) == 1 else "LOW")
    return label, reasons


def analyze(src, taps_px, tb: Timebase, release_frame=None, tap_sigma_px=1.0, deg=3,
            mc_draws=300, seed=0, align_sigma_end=0.015):
    res = Result(False)
    res.fps, res.timing_source, res.warnings = tb.fps, tb.source, list(tb.warnings)
    H = homography_from_taps(taps_px)
    tap_res = tap_residual_m(H, taps_px)
    hr = stump_height_ratio(taps_px)
    if tap_res > 0.15:
        res.warnings.append(f"taps do not fit a square-on camera (residual {tap_res:.2f} m): retap or realign")
    if abs(np.log(hr)) > 0.15:
        res.warnings.append(f"stump heights differ by {abs(hr-1):.0%} end to end: camera may not be square-on")
    bg = detect.median_background(src)
    cand = detect.candidates(src, bg, H)
    if len(cand.fidx) == 0:
        res.message = "no moving blobs detected"
        return res
    m = min(src.n, len(tb.t))
    ok = cand.fidx < m
    fidx, px, py = cand.fidx[ok], cand.px[ok], cand.py[ok]
    t = tb.t[fidx]
    X, Y = to_world(H, px, py)
    keep = Y >= 0.10
    fidx, px, py, t, X, Y = fidx[keep], px[keep], py[keep], t[keep], X[keep], Y[keep]
    fit = track.fit_track(t, X, Y, fidx, deg=deg, seed=seed, frame_dt=1.0 / tb.fps)
    if fit is None:
        res.message = "could not find a ball trajectory"
        res.debug = dict(px=px, py=py, fidx=fidx)
        return res

    s = fit.sel
    t_first, t_last = t[s].min(), t[s].max()
    if release_frame is not None:
        t_rel = float(tb.t[release_frame])
    else:
        t_rel = float(t_first)
        res.warnings.append("no release frame given: speed is at the first tracked frame, "
                            "not at release (will read a little low)")
    if t_first - t_rel > 0.15:
        res.warnings.append("release is far before the first tracked frame: large extrapolation")

    v_rel = float(track._speed(fit.cx, fit.cy, t_rel - fit.tref) * 3.6)
    tt = np.linspace(t_first, t_last, 200) - fit.tref
    v_avg = float(np.mean(track._speed(fit.cx, fit.cy, tt)) * 3.6)

    sig_mc, _ = track.monte_carlo(np.asarray(taps_px), px[s], py[s], t[s], fit, t_rel,
                                  K=mc_draws, tap_sigma_px=tap_sigma_px, seed=seed + 1,
                                  align_sigma_end=align_sigma_end)
    sig_time = UNRELIABLE_TIMING_REL * v_rel if not tb.reliable else 0.0
    sigma = float(np.hypot(sig_mc, sig_time))
    tm = t[s].mean() - fit.tref
    ay = float(track._pf(fit.cy, tm, 2))
    sp_m = float(track._speed(fit.cx, fit.cy, tm))
    vy_m = float(track._pf(fit.cy, tm, 1))
    ay_expected = -track.G - track.K_DRAG_NOMINAL * sp_m * vy_m   # gravity + nominal air drag
    gratio = ay / ay_expected

    res.ok = True
    res.release_kmh, res.sigma_kmh, res.ci95_kmh = v_rel, sigma, 1.96 * sigma
    res.average_kmh = v_avg
    res.n_frames, res.rms_m, res.gravity_ratio = int(len(s)), fit.rms, float(gratio)
    res.confidence, res.reasons = _confidence(res.n_frames, fit.rms, gratio, tb, res.ci95_kmh)
    res.debug = dict(H=H, fit=fit, sel=s, fidx=fidx, px=px, py=py, t=t, X=X, Y=Y,
                     t_release=t_rel, bg=bg)
    return res


def analyze_video(path, taps_px, capture_fps=None, release_frame=None, **kw):
    src = VideoSource(path)
    tb = make_timebase(src.n, video_path=path, capture_fps=capture_fps)
    return analyze(src, taps_px, tb, release_frame=release_frame, **kw)
