"""Trajectory fitting and uncertainty for the pre-bounce ball flight.

World frame (metres): X along the pitch toward the batter, Y up.
The pre-bounce flight is fitted with a cubic polynomial in each axis (captures
gravity plus the slowly changing air-drag deceleration) after a RANSAC step that
picks the ball out of the candidate blobs.
"""
from dataclasses import dataclass

import numpy as np
from numpy.polynomial import polynomial as P

from .calibration import homography_from_taps, to_world, apply_alignment_gradient

G = 9.81
K_DRAG_NOMINAL = 0.0063   # 0.5*rho*Cd*A/m for a cricket ball, Cd~0.4 (approximate)


def _pf(c, t, der=0):
    cc = c if der == 0 else P.polyder(c, der)
    return P.polyval(t, cc)


def _fit(t, X, Y, deg):
    A = np.vander(t, deg + 1, increasing=True)
    return np.linalg.lstsq(A, X, rcond=None)[0], np.linalg.lstsq(A, Y, rcond=None)[0]


def _speed(cx, cy, t):
    return np.hypot(_pf(cx, t, 1), _pf(cy, t, 1))


def _one_per_frame(fidx, res, mask):
    """Among masked candidates keep the lowest-residual one per frame."""
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return idx
    order = idx[np.lexsort((res[idx], fidx[idx]))]
    _, first = np.unique(fidx[order], return_index=True)
    return np.sort(order[first])


def ransac_seed(t, X, Y, fidx, rng, iters=4000, tol=0.12, min_span=0.06):
    n = len(t)
    tm = float(np.median(t))
    best_score, best_mask = 0, None
    tt = t - tm
    for _ in range(iters):
        i = rng.choice(n, 3, replace=False)
        if len(set(fidx[i])) < 3:
            continue
        ts = tt[i]
        if np.ptp(ts) < min_span:
            continue
        A = np.vander(ts, 3, increasing=True)
        try:
            cx = np.linalg.solve(A, X[i]); cy = np.linalg.solve(A, Y[i])
        except np.linalg.LinAlgError:
            continue
        if not (12.0 < cx[1] < 50.0):          # plausible forward speed (m/s)
            continue
        if not (-16.0 < 2 * cy[2] < -4.0):      # roughly gravity-like vertical accel
            continue
        res = np.hypot(X - (cx[0] + cx[1] * tt + cx[2] * tt ** 2),
                       Y - (cy[0] + cy[1] * tt + cy[2] * tt ** 2))
        inl = res < tol
        score = len(np.unique(fidx[inl]))
        if score > best_score:
            best_score, best_mask = score, inl
    return best_mask, best_score


@dataclass
class TrackFit:
    sel: np.ndarray          # indices into candidate arrays
    cx: np.ndarray
    cy: np.ndarray
    tref: float
    deg: int
    rms: float


def fit_track(t, X, Y, fidx, deg=3, seed=0, frame_dt=1 / 240):
    rng = np.random.default_rng(seed)
    if len(t) < 12:
        return None
    mask, score = ransac_seed(t, X, Y, fidx, rng)
    if mask is None or score < 10:
        return None
    tref = float(np.median(t[mask]))
    sel = np.where(mask)[0]
    res_all = None
    for it in range(6):
        d = min(deg, 2) if len(sel) < 25 else deg
        cx, cy = _fit(t[sel] - tref, X[sel], Y[sel], d)
        tt = t - tref
        res_all = np.hypot(X - _pf(cx, tt), Y - _pf(cy, tt))
        rms = float(np.sqrt(np.mean(res_all[sel] ** 2)))
        tol = max(0.04, 3.0 * rms)
        lo, hi = t[sel].min() - 6 * frame_dt, t[sel].max() + 6 * frame_dt
        cand = (res_all < tol) & (t >= lo) & (t <= hi)
        new = _one_per_frame(fidx, res_all, cand)
        if len(new) == len(sel) and np.all(new == sel):
            break
        sel = new
        if len(sel) < 10:
            return None
    cx, cy = _fit(t[sel] - tref, X[sel], Y[sel], deg if len(sel) >= 25 else 2)
    res = np.hypot(X[sel] - _pf(cx, t[sel] - tref), Y[sel] - _pf(cy, t[sel] - tref))
    return TrackFit(sel, cx, cy, tref, len(cx) - 1, float(np.sqrt(np.mean(res ** 2))))


def monte_carlo(taps_px, px, py, t, fit, t_release, K=300, tap_sigma_px=1.0, seed=1,
                align_sigma_end=0.015):
    """Propagate tap noise, fit noise and camera-alignment uncertainty into the release
    speed (std, km/h). align_sigma_end = 1-sigma relative scale difference between the two
    ends of the pitch caused by the camera not being exactly square-on (1.5% ~ yaw of ~2 deg
    by eye; a verified setup should get this well under 0.5%)."""
    rng = np.random.default_rng(seed)
    taps_px = np.asarray(taps_px, float)
    n = len(t)
    speeds = []
    for _ in range(K):
        Hk = homography_from_taps(taps_px + rng.normal(0, tap_sigma_px, taps_px.shape))
        Xk, Yk = to_world(Hk, px, py)
        g = rng.normal(0, align_sigma_end) / 20.12
        Xk, Yk = apply_alignment_gradient(Xk, Yk, g)
        b = rng.integers(0, n, n)                       # bootstrap the points
        if len(np.unique(b)) < fit.deg + 3:
            continue
        cx, cy = _fit(t[b] - fit.tref, Xk[b], Yk[b], fit.deg)
        speeds.append(_speed(cx, cy, t_release - fit.tref) * 3.6)
    speeds = np.array(speeds)
    return float(np.std(speeds)), float(np.mean(speeds))
