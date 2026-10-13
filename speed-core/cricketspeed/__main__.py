import argparse
import json

import cv2
import numpy as np

from .calibration import taps_from_dict
from .pipeline import analyze_video


def main():
    ap = argparse.ArgumentParser(prog="cricketspeed")
    ap.add_argument("video")
    ap.add_argument("--taps", required=True, help="json with bowler_base/bowler_top/batter_base/batter_top [x,y]")
    ap.add_argument("--capture-fps", type=float, default=None)
    ap.add_argument("--release-frame", type=int, default=None)
    ap.add_argument("--overlay", default=None, help="write an overlay jpg here")
    a = ap.parse_args()
    taps = taps_from_dict(json.load(open(a.taps)))
    r = analyze_video(a.video, taps, capture_fps=a.capture_fps, release_frame=a.release_frame)
    print(r.headline())
    if r.ok:
        print(f"average speed over tracked flight: {r.average_kmh:.1f} km/h")
        print(f"frames tracked: {r.n_frames}   residual rms: {r.rms_m*100:.1f} cm   "
              f"gravity ratio: {r.gravity_ratio:.2f}   fps: {r.fps:.1f} ({r.timing_source})")
    for x in r.reasons:
        print("  confidence note:", x)
    for w in r.warnings:
        print("  warning:", w)
    if a.overlay and r.ok:
        img = cv2.cvtColor(r.debug["bg"], cv2.COLOR_GRAY2BGR)
        for i in r.debug["sel"]:
            cv2.circle(img, (int(r.debug["px"][i]), int(r.debug["py"][i])), 4, (0, 255, 0), 1)
        cv2.imwrite(a.overlay, img)


if __name__ == "__main__":
    main()
