import numpy as np
import cv2
import onnxruntime as ort
from loguru import logger


CLASS_NAMES = {0: "fire", 1: "smoke"}


class FireSmokeDetector:
    """
    Raw ONNX Runtime wrapper for fire/smoke detection (YOLOv8 ONNX export).
    Uses the same thread-capped session pattern as PersonDetector so it does
    not contend with sibling containers for CPU cores.

    Assumed model output: (1, num_classes+4, num_anchors) — standard YOLOv8
    ONNX export with 2 classes: 0=fire, 1=smoke.
    """

    def __init__(self, model_path: str, conf_thresh: float = 0.4):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.session: ort.InferenceSession | None = None
        self.input_name: str | None = None
        self.input_shape: list | None = None

    def initialize(self):
        logger.info(f"Loading Fire/Smoke ONNX model: {self.model_path}")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        opts.inter_op_num_threads = 2

        available = ort.get_available_providers()
        providers = (
            ["CoreMLExecutionProvider", "CPUExecutionProvider"]
            if "CoreMLExecutionProvider" in available
            else ["CPUExecutionProvider"]
        )
        self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        logger.info(f"FireSmokeDetector loaded — providers: {self.session.get_providers()}")

        h = self.input_shape[2] if isinstance(self.input_shape[2], int) else 640
        w = self.input_shape[3] if isinstance(self.input_shape[3], int) else 640
        dummy = np.zeros((1, 3, h, w), dtype=np.float32)
        self.session.run(None, {self.input_name: dummy})
        logger.info("FireSmokeDetector warmed up")

    def _preprocess(self, img_bgr: np.ndarray):
        h, w = img_bgr.shape[:2]
        target_size = (
            (self.input_shape[2], self.input_shape[3])
            if isinstance(self.input_shape[2], int)
            else (640, 640)
        )

        scale = min(target_size[0] / w, target_size[1] / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img_bgr, (new_w, new_h))

        pad_w = target_size[0] - new_w
        pad_h = target_size[1] - new_h
        top, bottom = pad_h // 2, pad_h - pad_h // 2
        left, right = pad_w // 2, pad_w - pad_w // 2

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        blob = padded.transpose(2, 0, 1)
        blob = np.expand_dims(blob, axis=0).astype(np.float32) / 255.0
        return blob, scale, left, top

    def _postprocess(self, outputs, scale, pad_left, pad_top) -> list:
        # Model outputs (1, 300, 6): NMS-filtered rows of [x1, y1, x2, y2, confidence, class_id]
        detections = outputs[0][0]  # (300, 6)

        confidences = detections[:, 4]
        class_ids = detections[:, 5].astype(int)

        mask = (confidences > self.conf_thresh) & (class_ids <= 1)
        detections = detections[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        results = []
        for i, det in enumerate(detections):
            x1 = (det[0] - pad_left) / scale
            y1 = (det[1] - pad_top) / scale
            x2 = (det[2] - pad_left) / scale
            y2 = (det[3] - pad_top) / scale

            cls_id = int(class_ids[i])
            results.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidences[i]) * 100.0,
                "class_name": CLASS_NAMES.get(cls_id, "unknown"),
            })

        return results

    def detect(self, img_bgr: np.ndarray) -> list:
        if self.session is None:
            self.initialize()

        blob, scale, pad_left, pad_top = self._preprocess(img_bgr)
        outputs = self.session.run(None, {self.input_name: blob})
        return self._postprocess(outputs, scale, pad_left, pad_top)
