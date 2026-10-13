"""Compare cricketspeed with a reference (radar gun / bowling machine) over many clips.

    python tools/batch_eval.py clips.csv

clips.csv columns:  clip,radar_kmh[,cal][,capture_fps]
  clip         video file, relative to the csv
  radar_kmh    reference speed for that delivery
  cal          optional, defaults to <clip>.cal.json (made with tools/pick_taps.py)
  capture_fps  optional override
Writes results.csv next to the input and prints a summary.
"""
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cricketspeed.calibration import load_cal          # noqa: E402
from cricketspeed.pipeline import analyze_video        # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    csv_path = Path(sys.argv[1])
    base = csv_path.parent
    out_rows, diffs = [], []
    for row in csv.DictReader(open(csv_path, newline="")):
        clip = base / row["clip"]
        cal = base / (row.get("cal") or (row["clip"] + ".cal.json").replace(".mp4.cal.json", ".cal.json"))
        if not cal.exists():
            alt = clip.with_suffix(".cal.json")
            cal = alt if alt.exists() else cal
        ref = float(row["radar_kmh"])
        rec = {"clip": row["clip"], "reference_kmh": ref}
        try:
            taps, rel, cfps = load_cal(cal)
            if row.get("capture_fps"):
                cfps = float(row["capture_fps"])
            r = analyze_video(str(clip), taps, capture_fps=cfps, release_frame=rel)
            if r.ok:
                d = r.release_kmh - ref
                diffs.append(d)
                rec.update(estimate_kmh=round(r.release_kmh, 2), ci95_kmh=round(r.ci95_kmh, 2),
                           diff_kmh=round(d, 2), inside_ci=abs(d) <= r.ci95_kmh,
                           confidence=r.confidence, frames=r.n_frames,
                           gravity_ratio=round(r.gravity_ratio, 2),
                           notes="; ".join(r.reasons + r.warnings))
            else:
                rec["notes"] = "FAILED: " + r.message
        except Exception as e:                      # keep going over the other clips
            rec["notes"] = f"ERROR: {e}"
        out_rows.append(rec)
        print(rec)
    keys = ["clip", "reference_kmh", "estimate_kmh", "ci95_kmh", "diff_kmh", "inside_ci",
            "confidence", "frames", "gravity_ratio", "notes"]
    with open(base / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out_rows)
    if diffs:
        n = len(diffs)
        print(f"\n{n} clips   mean diff {sum(diffs)/n:+.2f} km/h   mean |diff| {sum(map(abs, diffs))/n:.2f}   "
              f"RMS {math.sqrt(sum(d*d for d in diffs)/n):.2f}   within ±1: {sum(abs(d) <= 1 for d in diffs)}/{n}")
        print("note: a radar gun is itself ~±1-2 km/h, so differences of that size are not necessarily our error")
    print("wrote", base / "results.csv")


if __name__ == "__main__":
    main()
