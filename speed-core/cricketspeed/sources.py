"""Frame sources. Everything the pipeline needs: n, iter_gray(), sample(k)."""
import cv2
import numpy as np


class VideoSource:
    def __init__(self, path):
        self.path = path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise IOError(f"cannot open {path}")
        self.n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.shape = (int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
        cap.release()

    def iter_gray(self):
        cap = cv2.VideoCapture(self.path)
        while True:
            ok, f = cap.read()
            if not ok:
                break
            yield cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if f.ndim == 3 else f
        cap.release()

    def sample(self, k):
        step = max(1, self.n // k)
        return [f for i, f in enumerate(self.iter_gray()) if i % step == 0][:k]


class CallableSource:
    """Frames rendered on demand (used by the synthetic test harness)."""
    def __init__(self, n, render, shape):
        self.n, self.render, self.shape = n, render, shape

    def iter_gray(self):
        for k in range(self.n):
            yield self.render(k)

    def sample(self, k):
        step = max(1, self.n // k)
        return [self.render(i) for i in range(0, self.n, step)][:k]
