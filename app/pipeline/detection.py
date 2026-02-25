import numpy as np
import cv2
import torch
import functools
from ultralytics import YOLO
import os

# PyTorch 2.6+ compatibility bypass
torch.load = functools.partial(torch.load, weights_only=False)

_model_cache = None
YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "best(2).pt")


def get_yolo_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = YOLO(os.path.abspath(YOLO_MODEL_PATH))
    return _model_cache


def detect_fractures(img: np.ndarray):
    """
    Run YOLO on the image. Returns:
      - Xray_breaks: dict  {'ulna break': {'center': (cx, cy), 'size': (w, h)}, ...}
      - ulna_crop: numpy crop or None
      - radius_crop: numpy crop or None
    Coordinates are in centered space (origin = image center, Y-up).
    """
    model = get_yolo_model()
    results = model(img)
    boxes = results[0].boxes.xyxy.cpu().numpy()

    h, w = img.shape[:2]
    cx_img = w // 2
    cy_img = h // 2

    Xray_breaks = {}
    ulna_crop = None
    radius_crop = None

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        fw, fh = x2 - x1, y2 - y1
        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2
        centered_pt = (int(x_center - cx_img), int(cy_img - y_center))

        pad = 15
        x1p, y1p = max(0, x1 - pad), max(0, y1 - pad)
        x2p, y2p = min(w, x2 + pad), min(h, y2 + pad)
        crop = img[y1p:y2p, x1p:x2p]

        if x_center < cx_img and "radius break" not in Xray_breaks:
            Xray_breaks["radius break"] = {"center": centered_pt, "size": (fw, fh)}
            radius_crop = crop
        elif x_center >= cx_img and "ulna break" not in Xray_breaks:
            Xray_breaks["ulna break"] = {"center": centered_pt, "size": (fw, fh)}
            ulna_crop = crop

    return Xray_breaks, ulna_crop, radius_crop
