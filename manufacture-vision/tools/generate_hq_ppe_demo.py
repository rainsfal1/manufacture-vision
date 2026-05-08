import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../perception-node/src'))

import cv2
import numpy as np
import subprocess
from ultralytics import YOLO
from detection.ppe_detector import PPEDetector

def draw_chamfered_box(img, x1, y1, x2, y2, text, color=(255, 255, 255)):
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    chamfer = 20
    thickness = 2
    
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
    
    cv2.rectangle(img, (lx1, y2), (lx2, ly2), color, -1)
    
    # Text color contrast
    text_color = (0, 0, 0) if color == (255, 255, 255) else (255, 255, 255)
    cv2.putText(img, text, (lx1 + 10, ly2 - 8), font, font_scale, text_color, font_thick, cv2.LINE_AA)

def main():
    input_path = "../../demo-videos/helmet.mp4"
    output_path = "../../manufacture-vision-landing/ppe-demo.mp4"
    ppe_model_path = "../perception-node/models/ppe_detector.onnx"
    
    base_dir = os.path.dirname(__file__)
    input_path = os.path.abspath(os.path.join(base_dir, input_path))
    output_path = os.path.abspath(os.path.join(base_dir, output_path))
    ppe_model_path = os.path.abspath(os.path.join(base_dir, ppe_model_path))

    print("Loading YOLOv8m model...")
    person_model = YOLO("yolov8m.pt")
    
    print("Loading PPEDetector model...")
    ppe_detector = PPEDetector(ppe_model_path, conf_thresh=0.25)
    ppe_detector.initialize()

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Failed to open video: {input_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Video info: {width}x{height} @ {fps}fps")

    ffmpeg_cmd = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}', '-pix_fmt', 'bgr24', '-r', str(fps),
        '-i', '-', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-pix_fmt', 'yuv420p', output_path
    ]
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_idx = 0
    results = person_model.track(source=input_path, stream=True, classes=[0], conf=0.3, tracker="botsort.yaml")

    for result in results:
        frame = result.orig_img
        
        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            track_ids = result.boxes.id.cpu().numpy()
            
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                
                # Crop and detect PPE
                crop = ppe_detector.crop_person(frame, box, pad=10)
                status = ppe_detector.detect_ppe(crop, ["helmet"])
                
                has_helmet = status.get("helmet", True)
                
                if not has_helmet:
                    draw_chamfered_box(frame, x1, y1, x2, y2, f"NO HELMET", color=(0, 0, 255))
                else:
                    draw_chamfered_box(frame, x1, y1, x2, y2, f"HELMET OK", color=(255, 255, 255))

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
