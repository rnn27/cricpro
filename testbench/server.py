"""cricpro test bench: use your phone's browser to run the speed engine on real clips.

The phone records with its normal camera app (240 fps slow-motion), then opens this page
(served from your PC over Wi-Fi), uploads the clip, taps the stumps, marks the release frame
and gets the speed. Everything is processed on your PC; nothing leaves your network.

    py server.py
"""
import csv
import io
import json
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "speed-core"))
from cricketspeed import track                                       # noqa: E402
from cricketspeed.calibration import TAP_KEYS, taps_from_dict         # noqa: E402
from cricketspeed.pipeline import analyze_video                       # noqa: E402

DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
MAX_FRAMES = 4000

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 ** 3
_lock = threading.Lock()


# ---------- session storage (one folder per clip, state in session.json) ----------
def sdir(sid):
    if not sid.isalnum():
        abort(404)
    d = DATA / sid
    if not d.is_dir():
        abort(404)
    return d


def load(sid):
    return json.loads((sdir(sid) / "session.json").read_text())


def save(sid, **upd):
    with _lock:
        p = DATA / sid / "session.json"
        s = json.loads(p.read_text())
        s.update(upd)
        p.write_text(json.dumps(s, indent=1))
        return s


def clip_path(sid):
    return next(p for p in sdir(sid).iterdir() if p.stem == "clip")


# ---------- background jobs ----------
def extract_frames(sid):
    try:
        cap = cv2.VideoCapture(str(clip_path(sid)))
        if not cap.isOpened():
            raise IOError("could not open the video (unsupported codec?)")
        container_fps = float(cap.get(cv2.CAP_PROP_FPS))
        est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fdir = DATA / sid / "frames"
        fdir.mkdir(exist_ok=True)
        i = 0
        w = h = 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            if i >= MAX_FRAMES:
                raise ValueError(f"clip has more than {MAX_FRAMES} frames; trim it to the delivery")
            h, w = f.shape[:2]
            cv2.imwrite(str(fdir / f"{i:06d}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 85])
            i += 1
            if i % 25 == 0:
                save(sid, progress=i / max(est, 1))
        cap.release()
        if i < 20:
            raise ValueError("the video has too few frames")
        save(sid, state="ready", n_frames=i, width=w, height=h, container_fps=container_fps, progress=1.0)
    except Exception as e:                                        # report to the page
        save(sid, state="error", message=str(e))


def _overlay(sid, r, taps):
    dbg = r.debug
    img = cv2.cvtColor(dbg["bg"], cv2.COLOR_GRAY2BGR)
    H, fit = dbg["H"], dbg["fit"]
    for (x, y) in taps:
        cv2.drawMarker(img, (int(x), int(y)), (0, 255, 255), cv2.MARKER_CROSS, 18, 2)
    t = dbg["t"]
    ts = np.linspace(t[dbg["sel"]].min(), t[dbg["sel"]].max(), 200) - fit.tref
    wx, wy = track._pf(fit.cx, ts), track._pf(fit.cy, ts)
    px = cv2.perspectiveTransform(np.stack([wx, wy], 1).reshape(-1, 1, 2), np.linalg.inv(H)).reshape(-1, 2)
    cv2.polylines(img, [np.round(px).astype(np.int32).reshape(-1, 1, 2)], False, (0, 0, 255), 1, cv2.LINE_AA)
    for i in dbg["sel"]:
        cv2.circle(img, (int(dbg["px"][i]), int(dbg["py"][i])), 5, (0, 255, 0), 1)
    cv2.imwrite(str(DATA / sid / "overlay.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])


def run_analysis(sid, payload):
    try:
        taps = taps_from_dict(payload["taps"])
        cfps = float(payload["capture_fps"])
        rel = payload.get("release_frame")
        rel = int(rel) if rel is not None else None
        r = analyze_video(str(clip_path(sid)), taps, capture_fps=cfps, release_frame=rel)
        if r.ok:
            _overlay(sid, r, taps)
            res = dict(ok=True, release_kmh=r.release_kmh, sigma_kmh=r.sigma_kmh, ci95_kmh=r.ci95_kmh,
                       average_kmh=r.average_kmh, confidence=r.confidence, reasons=r.reasons,
                       warnings=r.warnings, n_frames=r.n_frames, rms_cm=r.rms_m * 100,
                       gravity_ratio=r.gravity_ratio, fps=r.fps, timing_source=r.timing_source)
        else:
            res = dict(ok=False, message=r.message, warnings=r.warnings)
        save(sid, analysis="done", result=res)
    except Exception as e:
        save(sid, analysis="done", result=dict(ok=False, message=str(e), warnings=[]))


# ---------- routes ----------
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/upload")
def upload():
    f = request.files.get("video")
    if not f:
        return jsonify(error="no file"), 400
    sid = uuid.uuid4().hex[:10]
    d = DATA / sid
    d.mkdir()
    ext = (Path(f.filename or "clip.mp4").suffix or ".mp4").lower()
    f.save(d / f"clip{ext}")
    (d / "session.json").write_text(json.dumps(dict(
        id=sid, created=time.strftime("%Y-%m-%d %H:%M:%S"), filename=f.filename, state="extracting",
        progress=0.0, capture_fps=float(request.form.get("capture_fps") or 240))))
    threading.Thread(target=extract_frames, args=(sid,), daemon=True).start()
    return jsonify(id=sid)


@app.get("/api/session/<sid>")
def session(sid):
    return jsonify(load(sid))


@app.get("/api/session/<sid>/frame/<int:n>")
def frame(sid, n):
    p = sdir(sid) / "frames" / f"{n:06d}.jpg"
    if not p.exists():
        abort(404)
    return send_file(p, mimetype="image/jpeg", max_age=3600)


@app.post("/api/session/<sid>/analyze")
def analyze(sid):
    s = load(sid)
    if s.get("state") != "ready":
        return jsonify(error="clip not ready"), 400
    p = request.get_json(force=True)
    if not all(k in p.get("taps", {}) for k in TAP_KEYS):
        return jsonify(error="need 4 taps"), 400
    meta = {k: p.get(k) for k in ("reference_kmh", "camera_distance_m", "lateral_offset_m", "notes")}
    save(sid, analysis="running", result=None, taps=p["taps"], release_frame=p.get("release_frame"),
         capture_fps=float(p["capture_fps"]), meta=meta)
    threading.Thread(target=run_analysis, args=(sid, p), daemon=True).start()
    return jsonify(ok=True)


@app.get("/api/session/<sid>/overlay.jpg")
def overlay(sid):
    p = sdir(sid) / "overlay.jpg"
    if not p.exists():
        abort(404)
    return send_file(p, mimetype="image/jpeg", max_age=0)


@app.get("/api/sessions")
def sessions():
    out = []
    for d in sorted(DATA.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if (d / "session.json").exists():
            out.append(json.loads((d / "session.json").read_text()))
    return jsonify(out)


@app.get("/api/results.csv")
def results_csv():
    buf = io.StringIO()
    cols = ["id", "created", "filename", "capture_fps", "release_frame", "reference_kmh", "estimate_kmh",
            "ci95_kmh", "diff_kmh", "confidence", "n_frames", "camera_distance_m", "lateral_offset_m",
            "notes", "warnings"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for s in json.loads(sessions().get_data()):
        res, meta = s.get("result") or {}, s.get("meta") or {}
        ref = meta.get("reference_kmh")
        est = res.get("release_kmh")
        try:
            diff = round(float(est) - float(ref), 2) if (est is not None and ref not in (None, "")) else ""
        except ValueError:
            diff = ""
        w.writerow(dict(id=s["id"], created=s.get("created"), filename=s.get("filename"),
                        capture_fps=s.get("capture_fps"), release_frame=s.get("release_frame"),
                        reference_kmh=ref, estimate_kmh=round(est, 2) if est is not None else "",
                        ci95_kmh=round(res["ci95_kmh"], 2) if res.get("ci95_kmh") is not None else "",
                        diff_kmh=diff, confidence=res.get("confidence", ""), n_frames=res.get("n_frames", ""),
                        camera_distance_m=meta.get("camera_distance_m"), lateral_offset_m=meta.get("lateral_offset_m"),
                        notes=meta.get("notes"), warnings="; ".join((res.get("reasons") or []) + (res.get("warnings") or []))))
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=cricpro_results.csv"})


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    port = 8000
    print(f"\ncricpro test bench running.\n  On this PC:   http://localhost:{port}\n"
          f"  On your phone (same Wi-Fi): http://{lan_ip()}:{port}\n"
          "  Windows may ask to allow Python through the firewall: allow it on PRIVATE networks.\n"
          "  Stop with Ctrl+C. Only run this on a Wi-Fi you trust: there is no password.\n")
    app.run(host="0.0.0.0", port=port, threaded=True)
