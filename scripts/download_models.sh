#!/usr/bin/env bash
# Downloads the two ONNX models the vision pipeline needs at runtime.
# Never commit these (see .gitignore) — this script is how every
# environment (dev machine or Jetson) gets them.
#
#   vision/models/yunet.onnx      - face detection (OpenCV Zoo YuNet)
#   vision/models/w600k_mbf.onnx  - face recognition embeddings (InsightFace)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$ROOT_DIR/vision/models"
mkdir -p "$MODELS_DIR"

YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_DEST="$MODELS_DIR/yunet.onnx"

if [ -f "$YUNET_DEST" ]; then
  echo "yunet.onnx already present, skipping"
else
  echo "downloading YuNet detector from opencv_zoo..."
  curl -fL --retry 3 -o "$YUNET_DEST" "$YUNET_URL"
  echo "-> $YUNET_DEST"
fi

RECOGNITION_DEST="$MODELS_DIR/w600k_mbf.onnx"
if [ -f "$RECOGNITION_DEST" ]; then
  echo "w600k_mbf.onnx already present, skipping"
else
  echo "fetching InsightFace recognition model pack (buffalo_sc, falling back to buffalo_l)..."
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  PACK=""
  for candidate in buffalo_sc buffalo_s buffalo_l; do
    url="https://github.com/deepinsight/insightface/releases/download/v0.7/${candidate}.zip"
    if curl -fsIL "$url" >/dev/null 2>&1; then
      PACK="$candidate"
      PACK_URL="$url"
      break
    fi
  done

  if [ -z "$PACK" ]; then
    echo "ERROR: could not find any InsightFace model pack (buffalo_sc/buffalo_s/buffalo_l)" >&2
    echo "at the expected GitHub releases URLs. Download one manually and place its" >&2
    echo "w600k_*.onnx recognition file at: $RECOGNITION_DEST" >&2
    exit 1
  fi

  echo "using pack: $PACK ($PACK_URL)"
  curl -fL --retry 3 -o "$TMP_DIR/pack.zip" "$PACK_URL"
  unzip -q "$TMP_DIR/pack.zip" -d "$TMP_DIR/pack"

  RECOGNITION_SRC="$(find "$TMP_DIR/pack" -iname 'w600k_*.onnx' | head -n1)"
  if [ -z "$RECOGNITION_SRC" ]; then
    echo "ERROR: pack '$PACK' didn't contain a w600k_*.onnx recognition model" >&2
    exit 1
  fi

  cp "$RECOGNITION_SRC" "$RECOGNITION_DEST"
  echo "-> $RECOGNITION_DEST (from $PACK: $(basename "$RECOGNITION_SRC"))"
  if [ "$PACK" != "buffalo_sc" ]; then
    echo "NOTE: buffalo_sc wasn't available, used '$PACK' instead — heavier model," >&2
    echo "fine for dev-machine testing but revisit for the Jetson Nano deployment." >&2
  fi
fi

echo "done."
