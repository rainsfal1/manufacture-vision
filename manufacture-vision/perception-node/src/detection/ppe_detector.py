import numpy as np
import cv2
import onnxruntime as ort
from loguru import logger


class PPEDetector:
    """
    Second-stage PPE attribute detector.
    Model: Hansung-Cho/yolov8n-ppe-detection (10 classes, presence + absence).

    Runs on person crops produced by the primary PersonDetector.

    Model class vocabulary:
        0: Hardhat        1: Mask         2: NO-Hardhat    3: NO-Mask
        4: NO-Safety Vest 5: Person       6: Safety Cone   7: Safety Vest
        8: machinery      9: vehicle

    Decision logic per PPE item:
        - Absence class detected  → MISSING  (explicit signal)
        - Presence class detected → WEARING  (explicit signal)
        - Neither detected        → WEARING  (benefit of doubt — model couldn't see clearly)
        - Both detected           → WEARING  (presence wins)
    """

    PRESENCE_CLASS: dict[str, int] = {
        "helmet": 0,   # Hardhat
        "vest":   7,   # Safety Vest
        "mask":   1,   # Mask
    }
    ABSENCE_CLASS: dict[str, int] = {
        "helmet": 2,   # NO-Hardhat
        "vest":   4,   # NO-Safety Vest
        "mask":   3,   # NO-Mask
    }

    def __init__(self, model_path: str, conf_thresh: float = 0.4):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.session: ort.InferenceSession | None = None
        self.input_name: str | None = None
        self.input_shape: list | None = None

    def initialize(self):
        logger.info(f"Loading PPE ONNX model: {self.model_path}")
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
        logger.info(f"PPEDetector loaded — providers: {self.session.get_providers()}")

        h = self.input_shape[2] if isinstance(self.input_shape[2], int) else 640
        w = self.input_shape[3] if isinstance(self.input_shape[3], int) else 640
        dummy = np.zeros((1, 3, h, w), dtype=np.float32)
        self.session.run(None, {self.input_name: dummy})
        logger.info("PPEDetector warmed up")

    def crop_person(self, frame: np.ndarray, bbox: list, pad: int = 15) -> np.ndarray:
        """Extract a padded person crop, clamped to frame bounds."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)
        return frame[y1:y2, x1:x2]

    def _preprocess(self, img_bgr: np.ndarray):
        """Letterbox + normalize to model input size."""
        h, w = img_bgr.shape[:2]
        target_h = self.input_shape[2] if isinstance(self.input_shape[2], int) else 640
        target_w = self.input_shape[3] if isinstance(self.input_shape[3], int) else 640

        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img_bgr, (new_w, new_h))

        pad_w = target_w - new_w
        pad_h = target_h - new_h
        top, bottom = pad_h // 2, pad_h - pad_h // 2
        left, right = pad_w // 2, pad_w - pad_w // 2

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                    cv2.BORDER_CONSTANT, value=(114, 114, 114))
        blob = padded.transpose(2, 0, 1)
        blob = np.expand_dims(blob, axis=0).astype(np.float32) / 255.0
        return blob

    def _postprocess(self, outputs) -> set[int]:
        """Return set of class_ids detected above conf_thresh."""
        preds = outputs[0][0].transpose(1, 0)  # (num_anchors, 4 + num_classes)
        scores = preds[:, 4:]
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)
        mask = confidences > self.conf_thresh
        return set(class_ids[mask].tolist())

    def detect_ppe(self, crop: np.ndarray, required_ppe: list[str]) -> dict[str, bool]:
        """
        Returns {ppe_item: is_wearing} for each item in required_ppe.

        Absence class detection → MISSING (explicit).
        Presence class detection → WEARING (explicit).
        Neither detected → WEARING (benefit of doubt).
        Unknown items default to True.
        """
        if self.session is None:
            self.initialize()

        if crop.size == 0:
            return {item: True for item in required_ppe}

        blob = self._preprocess(crop)
        outputs = self.session.run(None, {self.input_name: blob})
        detected = self._postprocess(outputs)

        result = {}
        for item in required_ppe:
            if item not in self.PRESENCE_CLASS:
                result[item] = True
                continue
            absent  = self.ABSENCE_CLASS[item] in detected
            present = self.PRESENCE_CLASS[item] in detected
            # Absence class is the explicit violation signal; presence wins ties
            result[item] = (not absent) or present
        return result
