import sys
import os

# Add src to path so we can import the detector
sys.path.append(os.path.join(os.path.dirname(__file__), '../perception-node/src'))

import cv2
import numpy as np
import subprocess
from detection.fire_smoke_detector import FireSmokeDetector

def draw_chamfered_box(img, x1, y1, x2, y2, text):
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    chamfer = 20
    thickness = 2
    color = (255, 255, 255)
    
    # Ensure chamfer isn't bigger than box
    chamfer = min(chamfer, max((x2 - x1) // 2, 0), max((y2 - y1) // 2, 0))
    if chamfer <= 0: return

    # Draw polygon lines with anti-aliasing
    cv2.line(img, (x1 + chamfer, y1), (x2, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1), (x2, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y2), (x1, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y2), (x1, y1 + chamfer), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1 + chamfer), (x1 + chamfer, y1), color, thickness, cv2.LINE_AA)
    
    # Draw label box at bottom left
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thick = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, font_thick)
    
    lx1 = x1
    ly1 = y2
    lx2 = x1 + tw + 20
    ly2 = y2 + th + 15
    
    cv2.rectangle(img, (lx1, y2), (lx2, ly2), (255, 255, 255), -1)
    cv2.putText(img, text, (lx1 + 10, ly2 - 8), font, font_scale, (0, 0, 0), font_thick, cv2.LINE_AA)

def main():
    input_path = "../../demo-videos/fire-detection.mp4"
    output_path = "../../manufacture-vision-landing/fire-demo.mp4"
    model_path = "../perception-node/models/fire_smoke.onnx"
    
    # Ensure absolute paths
    base_dir = os.path.dirname(__file__)
    input_path = os.path.abspath(os.path.join(base_dir, input_path))
    output_path = os.path.abspath(os.path.join(base_dir, output_path))
    model_path = os.path.abspath(os.path.join(base_dir, model_path))

    print(f"Loading model: {model_path}")
    detector = FireSmokeDetector(model_path, conf_thresh=0.4)
    detector.initialize()

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Failed to open video: {input_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Video info: {width}x{height} @ {fps}fps")

    # Start ffmpeg process for high-quality encoding
    # Using libx264, preset medium, crf 23 (good balance of quality and size)
    ffmpeg_cmd = [
        'ffmpeg',
        '-y', # Overwrite output
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}',
        '-pix_fmt', 'bgr24',
        '-r', str(fps),
        '-i', '-', # Read from stdin
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '18', # Very high quality
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    ema_box = None
    alpha = 0.15  # Smoothing factor (lower is smoother but lags more)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        detections = detector.detect(frame)
        
        best_conf = 0.0
        best_bbox = None
        best_cls = ""
        
        for d in detections:
            if d['confidence'] > best_conf:
                best_conf = d['confidence']
                best_bbox = d['bbox']
                best_cls = d['class_name']
                
        if best_bbox is not None:
            if ema_box is None:
                ema_box = list(best_bbox)
            else:
                ema_box = [alpha * b + (1 - alpha) * e for b, e in zip(best_bbox, ema_box)]
            
            draw_chamfered_box(frame, ema_box[0], ema_box[1], ema_box[2], ema_box[3], best_cls.upper())
        else:
            # If no detection, gradually decay or hold. We'll hold it for a few frames.
            if ema_box is not None:
                draw_chamfered_box(frame, ema_box[0], ema_box[1], ema_box[2], ema_box[3], best_cls.upper() if best_cls else "SMOKE")
        
        process.stdin.write(frame.tobytes())
        
        frame_idx += 1
        if frame_idx % 30 == 0:
            print(f"Processed {frame_idx} frames...")

    process.stdin.close()
    process.wait()
    cap.release()
    print(f"Done! Saved to {output_path}")

if __name__ == "__main__":
    main()
