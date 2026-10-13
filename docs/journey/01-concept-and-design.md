# 01 — Concept and design

**Idea:** an app that (1) computes the speed of a ball bowled and (2) does biomechanical
analysis of a fast bowler.

## Input
One high-speed phone video (120–240 fps, fast shutter ~1/1000 s, tripod). Both features come
from the same footage: ball position per frame gives speed; joint positions per frame give
biomechanics.

Frame rate sets accuracy: at 140 km/h the ball moves ~16 cm per frame at 240 fps; a ±1 frame
error over a ~110-frame flight is ~0.9% (~1.3 km/h). 30 fps would give ~8%.

## Speed — what is needed
- Calibration (pixels -> metres) from known pitch geometry: 20.12 m stump to stump, popping
  crease 1.22 m in front of the stumps, stump height 71.1 cm, stump set width 22.86 cm.
- Ball detection and tracking (Kalman / fitted trajectory).
- Speed from the track: simple two-point average, or a trajectory fit (gravity + drag)
  extrapolated back to release, which is closer to what a radar gun reports. Report which one.
- Main error source: perspective, since the ball is off the ground plane.

## Biomechanics — what is needed (v1)
Pose estimator (MediaPipe BlazePose / RTMPose / ViTPose) on every frame; events: back-foot
contact, front-foot contact, release, follow-through. Metrics: run-up speed, stride length,
front-knee angle at FFC and release, trunk lateral flexion, arm position and release height,
event timings, action classification (shoulder-hip counter-rotation matters for injury risk).

Honest limits: single camera is 2D with depth ambiguity (side-on + front/behind improves it);
the 15° elbow-extension law cannot be judged from a phone; ground reaction forces need force
plates. Position as a coaching/screening tool, not clinical.

## Open at the end of this entry
Target user (coaches/academies with a tripod vs casual handheld) and platform.
