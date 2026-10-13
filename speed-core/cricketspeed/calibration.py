"""Calibration of the vertical plane through the pitch centre line.

Four taps (pixels) define a homography image -> metres in the plane that runs
along the pitch (X = 0 at the bowler's stumps, X = 20.12 m at the batter's
stumps, Y = height above ground).

Tap order: bowler-end stump base, bowler-end stump top,
           batter-end stump base, batter-end stump top.
"""
import numpy as np
import cv2

PITCH_LENGTH_M = 20.12      # stumps to stumps (22 yards)
STUMP_HEIGHT_M = 0.711      # 28 inches

WORLD_PTS = np.array([[0.0, 0.0],
                      [0.0, STUMP_HEIGHT_M],
                      [PITCH_LENGTH_M, 0.0],
                      [PITCH_LENGTH_M, STUMP_HEIGHT_M]], dtype=np.float64)

TAP_KEYS = ["bowler_base", "bowler_top", "batter_base", "batter_top"]


def taps_from_dict(d):
    return np.array([d[k] for k in TAP_KEYS], dtype=np.float64)


def similarity_from_taps(taps_px):
    """Least-squares similarity (scale, rotation, shift) image -> metres.

    Assumes the camera looks perpendicular to the pitch, so the centre-line plane
    is parallel to the image plane. 8 equations / 4 unknowns: tap noise averages
    out over the 20 m baseline. A full 4-point homography is hopelessly
    ill-conditioned here (all points sit in a 20 m x 0.7 m strip).
    """
    taps_px = np.asarray(taps_px, dtype=np.float64).reshape(4, 2)
    u, v = taps_px[:, 0], -taps_px[:, 1]
    A, b = [], []
    for (ui, vi), (Xw, Yw) in zip(zip(u, v), WORLD_PTS):
        A.append([ui, -vi, 1, 0]); b.append(Xw)
        A.append([vi, ui, 0, 1]); b.append(Yw)
    sol = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)[0]
    a, bb, tx, ty = sol
    # world = [[a,-b],[b,a]] @ (u,v) + t ; pixel->(u,v) flips y, fold that into H
    H = np.array([[a, bb, tx], [bb, -a, ty], [0, 0, 1.0]])
    return H


def tap_residual_m(H, taps_px):
    taps_px = np.asarray(taps_px, dtype=np.float64).reshape(4, 2)
    X, Y = to_world(H, taps_px[:, 0], taps_px[:, 1])
    return float(np.sqrt(np.mean((X - WORLD_PTS[:, 0]) ** 2 + (Y - WORLD_PTS[:, 1]) ** 2)))


def stump_height_ratio(taps_px):
    """Apparent stump height, bowler end / batter end. ~1.0 when the camera is square-on."""
    t = np.asarray(taps_px, dtype=np.float64).reshape(4, 2)
    return float(np.hypot(*(t[1] - t[0])) / np.hypot(*(t[3] - t[2])))


def homography_from_taps(taps_px, mode="similarity"):
    taps_px = np.asarray(taps_px, dtype=np.float64).reshape(4, 2)
    if mode == "similarity":
        return similarity_from_taps(taps_px)
    H, _ = cv2.findHomography(taps_px, WORLD_PTS, 0)
    if H is None:
        raise ValueError("Calibration failed: taps are degenerate")
    return H


def apply_alignment_gradient(X, Y, g):
    """Correct for a relative scale gradient g (per metre) along the pitch, keeping both
    stump ends fixed. Models a camera that is not exactly square-on (yaw error)."""
    L = PITCH_LENGTH_M
    return X + 0.5 * g * X * (X - L), Y * (1.0 + g * (X - 0.5 * L))


def to_world(H, px, py):
    pts = np.stack([px, py], axis=1).astype(np.float64).reshape(-1, 1, 2)
    out = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    return out[:, 0], out[:, 1]
