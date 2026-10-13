"""Ball candidate detection for a fixed camera: background model + blob extraction."""
from dataclasses import dataclass

import cv2
import numpy as np

# Region of interest in the calibrated plane (metres)
ROI_X = (-2.0, 22.5)
ROI_Y = (0.10, 4.5)


@dataclass
class Candidates:
    fidx: np.ndarray
    px: np.ndarray
    py: np.ndarray
    area: np.ndarray


def median_background(src, k=31):
    frames = src.sample(k)
    return np.median(np.stack(frames, axis=0), axis=0).astype(np.uint8)


def candidates(src, bg, H, thresh=28, amin=3, amax=150):
    Hinv = np.linalg.inv(H)
    roi_w = np.array([[ROI_X[0], ROI_Y[0]], [ROI_X[1], ROI_Y[0]],
                      [ROI_X[1], ROI_Y[1]], [ROI_X[0], ROI_Y[1]]], np.float64).reshape(-1, 1, 2)
    poly = cv2.perspectiveTransform(roi_w, Hinv).reshape(-1, 2)
    h_img, w_img = bg.shape
    x0 = int(max(0, np.floor(poly[:, 0].min())))
    x1 = int(min(w_img, np.ceil(poly[:, 0].max())))
    y0 = int(max(0, np.floor(poly[:, 1].min())))
    y1 = int(min(h_img, np.ceil(poly[:, 1].max())))
    roi_mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(roi_mask, np.round(poly - [x0, y0]).astype(np.int32), 1)
    bg_c = bg[y0:y1, x0:x1]

    F, PX, PY, A = [], [], [], []
    for k, frame in enumerate(src.iter_gray()):
        d = cv2.absdiff(frame[y0:y1, x0:x1], bg_c)
        d = d * roi_mask
        mask = (d > thresh).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for j in range(1, n):
            area = stats[j, cv2.CC_STAT_AREA]
            if area < amin or area > amax:
                continue
            bx, by, bw, bh = (stats[j, cv2.CC_STAT_LEFT], stats[j, cv2.CC_STAT_TOP],
                              stats[j, cv2.CC_STAT_WIDTH], stats[j, cv2.CC_STAT_HEIGHT])
            patch = d[by:by + bh, bx:bx + bw].astype(np.float64)
            patch = patch * (labels[by:by + bh, bx:bx + bw] == j)
            s = patch.sum()
            if s <= 0:
                continue
            cx = (patch.sum(axis=0) * np.arange(bw)).sum() / s + bx + x0 + 0.5
            cy = (patch.sum(axis=1) * np.arange(bh)).sum() / s + by + y0 + 0.5
            F.append(k); PX.append(cx); PY.append(cy); A.append(area)
    return Candidates(np.array(F, int), np.array(PX), np.array(PY), np.array(A, float))
