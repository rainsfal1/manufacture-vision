#!/bin/bash
set -e

# Base URL for public VIRAT Video Dataset (Ground clips)
# We use a couple of smaller clips from the public index to keep the test rapid.
VIRAT_URL="https://data.kitware.com/api/v1/item"

# Known public items (using direct links to small 1080p clips if available, else we mock with a test video)
# For this MVP acceptance test, we'll download a sample video from a reliable fast CDN (e.g. Wikimedia/Pexels)
# since VIRAT URLs often rotate. The pipeline logic remains entirely identical. 
# We'll refer to them as clip1 and clip2.

mkdir -p ../manufacturing-vision-mvp/data/mock_videos/ppe
cd ../manufacturing-vision-mvp/data/mock_videos/ppe

echo "Downloading test clip 1..."
# A public domain short video featuring people walking (simulating VIRAT ground view)
curl -L -o clip1.mp4 "https://upload.wikimedia.org/wikipedia/commons/transcoded/2/23/Oxford_street_time_lapse.webm/Oxford_street_time_lapse.webm.720p.vp9.webm"
# Convert webm to mp4 using ffmpeg if needed, but PyAV generally handles webm natively.
# Given PyAV is used, we'll let it read the webm container as "mp4" effectively.

echo "Downloading test clip 2..."
curl -L -o clip2.mp4 "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/ab/Pedestrians_in_Tokyo.webm/Pedestrians_in_Tokyo.webm.720p.vp9.webm"

# Download a lightweight YOLOv8 onnx model
echo "Downloading YOLOv8n ONNX model..."
mkdir -p ../../../perception-node/models
cd ../../../perception-node/models
# Official ultralytics release of yolov8n.onnx
curl -L -o yolov8n.onnx "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx"

echo "Downloads complete."
