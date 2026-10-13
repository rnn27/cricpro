"""Interactive helper: click the 4 stump taps and mark the release frame.

    python tools/pick_taps.py clip.mp4 --capture-fps 240

Keys:  a / d  = previous / next frame      j / l = back / forward 10 frames
       left click = place the next tap     u = undo last tap
       r = mark THIS frame as the release frame (last frame with the ball in the hand)
       k = save  <clip>.cal.json and quit  q = quit without saving
A magnifier in the top-right shows the area around the cursor; click on the exact pixel.
Tap order: 1 bowler-end stump BASE, 2 bowler-end stump TOP, 3 batter-end stump BASE, 4 batter-end stump TOP.
(Untested GUI: written without a display. Report anything odd.)
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

NAMES = ["bowler_base", "bowler_top", "batter_base", "batter_top"]
PROMPTS = ["1/4 click the BASE of the stumps at the BOWLER's end",
           "2/4 click the TOP of the stumps at the BOWLER's end",
           "3/4 click the BASE of the stumps at the BATTER's end",
           "4/4 click the TOP of the stumps at the BATTER's end"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--capture-fps", type=float, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(a.video).with_suffix(".cal.json")
    cap = cv2.VideoCapture(a.video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n < 2:
        raise SystemExit("cannot read video")
    st = {"frame": 0, "taps": [], "release": None, "mouse": (0, 0)}
    win = "cricpro: taps"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    def on_track(v):
        st["frame"] = v

    cv2.createTrackbar("frame", win, 0, n - 1, on_track)

    def on_mouse(event, x, y, flags, param):
        st["mouse"] = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN and len(st["taps"]) < 4:
            st["taps"].append([x + 0.5, y + 0.5])      # pixel centre convention

    cv2.setMouseCallback(win, on_mouse)

    def read(i):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = cap.read()
        return f if ok else None

    def goto(i):
        st["frame"] = int(np.clip(i, 0, n - 1))
        cv2.setTrackbarPos("frame", win, st["frame"])

    while True:
        f = read(st["frame"])
        if f is None:
            goto(st["frame"] - 1)
            continue
        img = f.copy()
        for i, (x, y) in enumerate(st["taps"]):
            cv2.drawMarker(img, (int(x), int(y)), (0, 255, 255), cv2.MARKER_CROSS, 14, 1)
            cv2.putText(img, str(i + 1), (int(x) + 6, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        msg = PROMPTS[len(st["taps"])] if len(st["taps"]) < 4 else "taps done: scrub to release, press r, then k to save"
        rel = f"release frame: {st['release']}" if st["release"] is not None else "release frame: not set (press r)"
        cv2.putText(img, f"frame {st['frame']}/{n-1}   {rel}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(img, msg, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        mx, my = st["mouse"]
        r = 15
        pad = cv2.copyMakeBorder(f, r, r, r, r, cv2.BORDER_CONSTANT)
        crop = pad[my:my + 2 * r + 1, mx:mx + 2 * r + 1]
        if crop.size:
            zoom = cv2.resize(crop, (248, 248), interpolation=cv2.INTER_NEAREST)
            c = 124
            cv2.line(zoom, (c, 0), (c, 247), (0, 0, 255), 1)
            cv2.line(zoom, (0, c), (247, c), (0, 0, 255), 1)
            h, w = img.shape[:2]
            img[8:256, w - 256:w - 8] = zoom
        cv2.imshow(win, img)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("q"):
            print("quit without saving")
            break
        if k == ord("d"):
            goto(st["frame"] + 1)
        elif k == ord("a"):
            goto(st["frame"] - 1)
        elif k == ord("l"):
            goto(st["frame"] + 10)
        elif k == ord("j"):
            goto(st["frame"] - 10)
        elif k == ord("u") and st["taps"]:
            st["taps"].pop()
        elif k == ord("r"):
            st["release"] = st["frame"]
        elif k == ord("k"):
            if len(st["taps"]) < 4:
                print("need 4 taps first")
                continue
            d = {name: [round(x, 1), round(y, 1)] for name, (x, y) in zip(NAMES, st["taps"])}
            d["release_frame"] = st["release"]
            d["capture_fps"] = a.capture_fps
            d["video"] = Path(a.video).name
            json.dump(d, open(out, "w"), indent=2)
            print("saved", out)
            if st["release"] is None:
                print("note: no release frame set; speed will be taken at the first tracked frame")
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
