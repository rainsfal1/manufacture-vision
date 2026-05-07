"""
PERS-30: Download keremberke/yolov8n-ppe-detection and export to ONNX.

Usage (run from repo root):
    cd manufacturing-vision-mvp
    python tools/export_ppe_model.py

Output: perception-node/models/ppe_detector.onnx
"""

import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download
from ultralytics import YOLO

REPO_ID = "Tanishjain9/yolov8n-ppe-detection-6classes"
FILENAME = "best.pt"
OUTPUT_PATH = Path(__file__).parent.parent / "perception-node" / "models" / "ppe_detector.onnx"


def main():
    print(f"Downloading {REPO_ID}/{FILENAME} from HuggingFace ...")
    pt_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
    print(f"Downloaded .pt → {pt_path}")

    model = YOLO(pt_path)

    print("Exporting to ONNX (imgsz=640) ...")
    exported = model.export(format="onnx", imgsz=640)

    exported_path = Path(exported)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(exported_path), str(OUTPUT_PATH))

    print(f"Saved → {OUTPUT_PATH}")
    print()
    print("Class vocabulary:")
    for idx, name in model.names.items():
        print(f"  {idx}: {name}")


if __name__ == "__main__":
    main()
