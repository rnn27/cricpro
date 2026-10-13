"""Synthetic side-on delivery generator with known ground truth.

Renders a ball (drag + gravity + bounce) through a known plane homography with
motion blur, sensor noise, a static background texture and a moving bowler blob.
Not simulated: lateral parallax (ball off the calibrated plane), lens distortion,
rolling shutter, compression. Real footage must be used to measure those.
"""
import numpy as np

W, H_IMG = 1280, 720
def _cam(h31, h32=0.002, s=48.0, roll=0.01):
    c, sn = np.cos(roll), np.sin(roll)
    return np.array([[s * c, s * sn, 140.0], [s * sn, -s * c, 590.0], [h31, h32, 1.0]])


H_W2P = _cam(0.0)
BALL_R_M = 0.036
K_DRAG = 0.0063


def w2p(pts):
    pts = np.atleast_2d(pts)
    h = np.c_[pts, np.ones(len(pts))] @ H_W2P.T
    return h[:, :2] / h[:, 2:3]


def true_taps(rng=None, sigma=0.0):
    from cricketspeed.calibration import WORLD_PTS
    p = w2p(WORLD_PTS)
    if rng is not None and sigma > 0:
        p = p + rng.normal(0, sigma, p.shape)
    return p


def simulate(v_kmh, x0=1.2, y0=2.2, bounce_target=13.5, dt=1e-4, tmax=1.2):
    v0 = v_kmh / 3.6

    def run(theta):
        x, y = x0, y0
        vx, vy = v0 * np.cos(theta), -v0 * np.sin(theta)
        T, XS, YS = [0.0], [x], [y]
        t = 0.0
        bounced = False
        while t < tmax:
            sp = np.hypot(vx, vy)
            ax, ay = -K_DRAG * sp * vx, -9.81 - K_DRAG * sp * vy
            vx += ax * dt; vy += ay * dt
            x += vx * dt; y += vy * dt; t += dt
            if y <= BALL_R_M and vy < 0:
                y = BALL_R_M
                if not bounced:
                    bx = x
                bounced = True
                vy, vx = -0.5 * vy, 0.75 * vx
            T.append(t); XS.append(x); YS.append(y)
            if bounced and t > 0 and x > 19.5:
                break
        return np.array(T), np.array(XS), np.array(YS), (bx if bounced else 99.0)

    lo, hi = 0.005, 0.35
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if run(mid)[3] > bounce_target:
            lo = mid
        else:
            hi = mid
    return run(0.5 * (lo + hi))[:3]


def make_clip(v_kmh, fps=240.0, true_fps=None, seed=0, exposure=1 / 1000, noise=2.5,
              pre=0.30, post=0.80):
    """Returns (render(k), n_frames, true_timestamps_s, true_release_speed_kmh, release_frame)."""
    rng = np.random.default_rng(seed)
    true_fps = true_fps or fps
    T, XS, YS = simulate(v_kmh)
    fine_t = T
    pos = lambda t: (np.interp(t, fine_t, XS), np.interp(t, fine_t, YS))
    n = int((pre + post) * true_fps)
    t_start = -pre + rng.uniform(0, 1 / true_fps)
    ts = t_start + np.arange(n) / true_fps
    rel_frame = int(np.ceil((0 - t_start) * true_fps))

    gen = np.random.default_rng(1234)
    yy, xx = np.mgrid[0:H_IMG, 0:W]
    base = 125 + 25 * np.sin(yy / 90.0) + 10 * np.cos(xx / 140.0)
    base += gen.normal(0, 6, base.shape)
    pool = [gen.normal(0, noise, (H_IMG, W)).astype(np.float32) for _ in range(8)]
    bg_img = base.astype(np.float32)
    # static stump marks at both ends (visible features, part of the background)
    for X in (0.0, 20.12):
        a, b = w2p(np.array([[X, 0.0], [X, 0.711]]))
        for yline in np.linspace(a[1], b[1], 40):
            xline = a[0] + (b[0] - a[0]) * (yline - a[1]) / (b[1] - a[1])
            bg_img[int(yline), int(xline) - 1:int(xline) + 2] = 215
    bg_img = np.clip(bg_img, 0, 255)

    def render(k):
        t = ts[k]
        img = bg_img.copy()
        # bowler blob: runs in until release, keeps moving afterwards
        xb = 1.0 + 6.0 * t if t < 0 else 1.0 + 3.0 * t
        if -1.5 < xb < 6:
            p0 = w2p(np.array([[xb - 0.25, 0.0]]))[0]
            p1 = w2p(np.array([[xb + 0.25, 1.8]]))[0]
            x_a, x_b = int(p0[0]), int(p1[0])
            y_a, y_b = int(p1[1]), int(p0[1])
            img[max(y_a, 0):y_b, max(x_a, 0):x_b] = 45
        if t >= 0:
            cov = np.zeros_like(img)
            for s in np.linspace(0, exposure, 8):
                bx, by = pos(t + s)
                cx, cy = w2p(np.array([[bx, by]]))[0]
                r = BALL_R_M * 48.0 * (1 - 0.0)  # px radius at nominal scale
                x0, x1 = int(cx) - 6, int(cx) + 7
                y0, y1 = int(cy) - 6, int(cy) + 7
                if x0 < 0 or y0 < 0 or x1 > W or y1 > H_IMG:
                    continue
                gy, gx = np.mgrid[y0:y1, x0:x1]
                d = np.hypot(gx + 0.5 - cx, gy + 0.5 - cy)
                cov[y0:y1, x0:x1] += np.clip(r + 0.5 - d, 0, 1) / 8.0
            cov = np.clip(cov, 0, 1)
            img = img * (1 - cov) + 235.0 * cov
        img = img + pool[k % len(pool)]
        return np.clip(img, 0, 255).astype(np.uint8)

    v_true = float(np.hypot((XS[1] - XS[0]), (YS[1] - YS[0])) / (T[1] - T[0]) * 3.6)
    return render, n, ts, v_true, rel_frame


def set_camera_yaw(h31):
    """h31 > 0 makes the scale vary along the pitch (camera yawed away from square-on)."""
    global H_W2P
    H_W2P = _cam(h31)
