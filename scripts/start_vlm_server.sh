#!/usr/bin/env bash
# Start the llama.cpp VLM server that eyes-mcp's analyze_image talks to.
# Model presets + paths overridable via env (see download_models.sh for the same manifest).
set -euo pipefail

PRESET="${EYES_PRESET:-lfm-450m}"

# ---- preset manifest (keep in sync with scripts/download_models.sh) ----
case "$PRESET" in
  lfm-450m)  # tested default: 450M, ~400MB, fastest startup
    MODEL_DIR="${EYES_MODEL_DIR:-$HOME/.eyes-mcp/models/lfm-450m}"
    MODEL_FILE="${VLM_MODEL_FILE:-LFM2.5-VL-450M-Q4_K_M.gguf}"
    MMPROJ_FILE="${VLM_MMPROJ_FILE:-mmproj-LFM2.5-VL-450m-F16.gguf}"
    CTX="${VLM_CTX:-4096}" ;;
  nano)      # smallest useful VLM, Apache-2.0
    MODEL_DIR="${EYES_MODEL_DIR:-$HOME/.eyes-mcp/models/nano}"
    MODEL_FILE="${VLM_MODEL_FILE:-SmolVLM2-256M-Video-Instruct-Q8_0.gguf}"
    MMPROJ_FILE="${VLM_MMPROJ_FILE:-mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf}"
    CTX="${VLM_CTX:-4096}" ;;
  fast)      # Apache-2.0, supports video, good general vision
    MODEL_DIR="${EYES_MODEL_DIR:-$HOME/.eyes-mcp/models/fast}"
    MODEL_FILE="${VLM_MODEL_FILE:-SmolVLM2-500M-Video-Instruct-Q8_0.gguf}"
    MMPROJ_FILE="${VLM_MMPROJ_FILE:-mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf}"
    CTX="${VLM_CTX:-8192}" ;;
  ocr)       # text-dense scenes champion (Apache-2.0); needs a larger context
    MODEL_DIR="${EYES_MODEL_DIR:-$HOME/.eyes-mcp/models/ocr}"
    MODEL_FILE="${VLM_MODEL_FILE:-PaddleOCR-VL-1.6-GGUF.gguf}"
    MMPROJ_FILE="${VLM_MMPROJ_FILE:-PaddleOCR-VL-1.6-GGUF-mmproj.gguf}"
    CTX="${VLM_CTX:-16384}" ;;
  strong)    # real visual understanding when you have the RAM
    MODEL_DIR="${EYES_MODEL_DIR:-$HOME/.eyes-mcp/models/strong}"
    MODEL_FILE="${VLM_MODEL_FILE:-Qwen3VL-2B-Instruct-Q4_K_M.gguf}"
    MMPROJ_FILE="${VLM_MMPROJ_FILE:-mmproj-Qwen3VL-2B-Instruct-F16.gguf}"
    CTX="${VLM_CTX:-8192}" ;;
  *)
    echo "eyes-mcp: unknown preset '$PRESET' (lfm-450m|nano|fast|ocr|strong)" >&2; exit 2 ;;
esac

HOST="${VLM_HOST:-127.0.0.1}"
# Default 0 = OS-assigned free port, so a manual run never collides with
# services squatting on 8080. The MCP server passes an explicit VLM_PORT it
# pre-picked; llama-server prints the bound port to stdout for manual use.
PORT="${VLM_PORT:-0}"

# llama-server discovery: $LLAMA_SERVER_BIN > PATH > brew
BIN="${LLAMA_SERVER_BIN:-$(command -v llama-server || true)}"
if [ -z "$BIN" ]; then
  if command -v brew >/dev/null 2>&1 && [ -x "$(brew --prefix)/bin/llama-server" ]; then
    BIN="$(brew --prefix)/bin/llama-server"
  else
    echo "eyes-mcp: llama-server not found. Install it first:" >&2
    echo "  macOS:  brew install llama.cpp" >&2
    echo "  Linux:  build from source (https://github.com/ggml-org/llama.cpp)" >&2
    exit 127
  fi
fi

exec "$BIN" \
  -m "$MODEL_DIR/$MODEL_FILE" \
  --mmproj "$MODEL_DIR/$MMPROJ_FILE" \
  --host "$HOST" --port "$PORT" -c "$CTX" \
  --alias local-vlm
