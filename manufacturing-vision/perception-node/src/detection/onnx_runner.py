import onnxruntime as ort
import numpy as np
import cv2
from loguru import logger

class PersonDetector:
    """
    ONNX Runtime wrapper for a YOLOv8 (or generic) object detector.
    Filters outputs strictly for the 'person' class for Step 1.
    """
    def __init__(self, model_path: str, conf_thresh: float = 0.5):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.session = None
        self.input_name = None
        self.input_shape = None

    def initialize(self):
        logger.info(f"Loading ONNX model: {self.model_path}")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        opts.inter_op_num_threads = 2

        # CoreML uses Apple Neural Engine on M1/M2 — fall back to CPU if unavailable
        available = ort.get_available_providers()
        providers = (
            ["CoreMLExecutionProvider", "CPUExecutionProvider"]
            if "CoreMLExecutionProvider" in available
            else ["CPUExecutionProvider"]
        )
        self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        logger.info(f"PersonDetector loaded — providers: {self.session.get_providers()}")

        # Warm-up: trigger ONNX graph + CoreML network compilation now, not on first frame
        h = self.input_shape[2] if isinstance(self.input_shape[2], int) else 640
        w = self.input_shape[3] if isinstance(self.input_shape[3], int) else 640
        dummy = np.zeros((1, 3, h, w), dtype=np.float32)
        self.session.run(None, {self.input_name: dummy})
        logger.info("PersonDetector warmed up")

    def preprocess(self, img_bgr: np.ndarray):
        """
        Resizes and normalizes image for standard YOLO input.
        Assuming 640x640 input shape for modern YOLO models.
        """
        h, w = img_bgr.shape[:2]
        target_size = (self.input_shape[2], self.input_shape[3]) if isinstance(self.input_shape[2], int) else (640, 640)
        
        # Keep aspect ratio padding (letterbox)
        scale = min(target_size[0] / w, target_size[1] / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img_bgr, (new_w, new_h))
        
        pad_w = target_size[0] - new_w
        pad_h = target_size[1] - new_h
        
        top, bottom = pad_h // 2, pad_h - (pad_h // 2)
        left, right = pad_w // 2, pad_w - (pad_w // 2)
        
        padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        
        blob = padded.transpose(2, 0, 1) # HWC to CHW
        blob = np.expand_dims(blob, axis=0).astype(np.float32) / 255.0
        
        return blob, scale, left, top

    def postprocess(self, outputs, scale, pad_left, pad_top, conf_thresh=0.5):
        """
        Post-processes YOLOv8 ONNX output to extract bounding boxes.
        Returns: [bbox, conf, class_id] where bbox = [x1, y1, x2, y2]
        """
        # YOLOv8 output shape is generally (1, num_classes + 4, num_anchors)
        preds = outputs[0][0] # (84, 8400) for COCO

        # Transpose so rows are anchors
        preds = preds.transpose(1, 0) # (8400, 84)

        boxes = preds[:, :4] # cx, cy, w, h
        scores = preds[:, 4:] # Class probabilities

        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # Filter strictly for 'person' class (index 0 in COCO)
        mask = (class_ids == 0) & (confidences > conf_thresh)
        filtered_boxes = boxes[mask]
        filtered_confidences = confidences[mask]

        if len(filtered_boxes) == 0:
            return []

        # Convert cx,cy,w,h → x,y,w,h for NMS
        nms_boxes = np.stack([
            filtered_boxes[:, 0] - filtered_boxes[:, 2] / 2,
            filtered_boxes[:, 1] - filtered_boxes[:, 3] / 2,
            filtered_boxes[:, 2],
            filtered_boxes[:, 3],
        ], axis=1)

        indices = cv2.dnn.NMSBoxes(
            nms_boxes.tolist(),
            filtered_confidences.tolist(),
            conf_thresh,
            0.45,  # IoU threshold
        )

        if len(indices) == 0:
            return []

        results = []
        for i in np.array(indices).flatten():
            cx, cy, w, h = filtered_boxes[i]
            x1 = (cx - w / 2 - pad_left) / scale
            y1 = (cy - h / 2 - pad_top) / scale
            x2 = (cx + w / 2 - pad_left) / scale
            y2 = (cy + h / 2 - pad_top) / scale
            results.append([[x1, y1, x2, y2], float(filtered_confidences[i]), 0])

        return results

    def detect(self, img_bgr: np.ndarray) -> list:
        if not self.session:
            self.initialize()
            
        blob, scale, pad_left, pad_top = self.preprocess(img_bgr)
        outputs = self.session.run(None, {self.input_name: blob})
        
        results = self.postprocess(outputs, scale, pad_left, pad_top, self.conf_thresh)
        
        # Optional NMS could be applied here if the model doesn't embed it.
        return results
