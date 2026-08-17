#!/usr/bin/env bash
# Download the GGUF files (model + mmproj) for one eyes-mcp preset.
#   EYES_PRESET=fast ./scripts/download_models.sh
# China mainland mirror:  HF_ENDPOINT=https://hf-mirror.com ./scripts/download_models.sh
set -euo pipefail

PRESET="${EYES_PRESET:-lfm-450m}"
HF_BASE="${HF_ENDPOINT:-https://huggingface.co}"
MODELS_ROOT="${EYES_MODELS_ROOT:-$HOME/.eyes-mcp/models}"

case "$PRESET" in
  nano)
    REPO="ggml-org/SmolVLM2-256M-Video-Instruct-GGUF"
    FILES=("SmolVLM2-256M-Video-Instruct-Q8_0.gguf" "mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf") ;;
  lfm-450m)
    REPO="LiquidAI/LFM2.5-VL-450M-GGUF"
    FILES=("LFM2.5-VL-450M-Q4_K_M.gguf" "mmproj-LFM2.5-VL-450m-F16.gguf") ;;
  fast)
    REPO="unsloth/Qwen3.5-0.8B-GGUF"
    FILES=("Qwen3.5-0.8B-Q4_K_M.gguf" "mmproj-F16.gguf") ;;
  ocr)
    REPO="ggml-org/GLM-OCR-GGUF"
    FILES=("GLM-OCR-Q8_0.gguf" "mmproj-GLM-OCR-Q8_0.gguf") ;;
  strong)
    REPO="unsloth/Qwen3.5-2B-GGUF"
    FILES=("Qwen3.5-2B-Q4_K_M.gguf" "mmproj-F16.gguf") ;;
  xstrong)
    REPO="unsloth/Qwen3.5-4B-GGUF"
    FILES=("Qwen3.5-4B-Q4_K_M.gguf" "mmproj-F16.gguf") ;;
  # ---- extra presets (not in the chooser menu; see README "more models") ----
  smol500)
    REPO="ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
    FILES=("SmolVLM2-500M-Video-Instruct-Q8_0.gguf" "mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf") ;;
  paddle)
    REPO="PaddlePaddle/PaddleOCR-VL-1.6-GGUF"
    FILES=("PaddleOCR-VL-1.6-GGUF.gguf" "PaddleOCR-VL-1.6-GGUF-mmproj.gguf") ;;
  qwen3-2b)
    REPO="Qwen/Qwen3-VL-2B-Instruct-GGUF"
    FILES=("Qwen3VL-2B-Instruct-Q4_K_M.gguf" "mmproj-Qwen3VL-2B-Instruct-F16.gguf") ;;
  *)
    echo "unknown preset '$PRESET'" >&2
    echo "menu presets : nano lfm-450m fast ocr strong xstrong" >&2
    echo "extra presets: smol500 paddle qwen3-2b" >&2
    exit 2 ;;
esac

DEST="$MODELS_ROOT/$PRESET"
mkdir -p "$DEST"

for f in "${FILES[@]}"; do
  if [ -s "$DEST/$f" ]; then
    echo "✓ exists: $DEST/$f"
    continue
  fi
  echo "↓ downloading: $f"
  # -L follow redirects, -C - resume interrupted downloads
  curl -fL -C - --retry 3 -o "$DEST/$f.part" "$HF_BASE/$REPO/resolve/main/$f"
  mv "$DEST/$f.part" "$DEST/$f"
done

echo "done: preset=$PRESET → $DEST"
