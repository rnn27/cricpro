import argparse

import cv2

from .calibration import load_cal
from .pipeline import analyze_video


def main():
    ap = argparse.ArgumentParser(prog="cricketspeed")
    ap.add_argument("video")
    ap.add_argument("--cal", "--taps", dest="cal", required=True,
                    help="<clip>.cal.json from tools/pick_taps.py (4 taps, release frame, capture fps)")
    ap.add_argument("--capture-fps", type=float, default=None, help="overrides the value in the cal file")
    ap.add_argument("--release-frame", type=int, default=None, help="overrides the value in the cal file")
    ap.add_argument("--overlay", default=None, help="write an overlay jpg here")
    a = ap.parse_args()
    taps, rel, cfps = load_cal(a.cal)
    rel = a.release_frame if a.release_frame is not None else rel
    cfps = a.capture_fps or cfps
    try:
        r = analyze_video(a.video, taps, capture_fps=cfps, release_frame=rel)
    except ValueError as e:
        raise SystemExit(f"error: {e}")
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
